import asyncio, base64, io, json, os, re, sys, time
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
import fitz
from PIL import Image
from routes.hover_elevation_read import _find_view_pages
from routes.hover_vision import MODEL_NAME, _json_from_reply

PDF = '/app/backend/uploads/hover_pdfs/18ac182047fe4def9b2de2063277fa89.pdf'

BOUNDARY_PROMPT = """You are looking at the FRONT straight-on elevation drawing from a Hover measurement report.
Facade regions are outlined and labeled with tags like WR-1, BR-3, STC-1. The label sits inside or beside its outlined region.
TASK: find the region labeled STC-1 and return the pixel bounding box of its ENTIRE OUTLINED WALL AREA — trace the region's full boundary outline (the colored/hatched area the STC-1 label belongs to), not the label text's vicinity. If the outlined area is discontinuous (multiple patches), return one box enclosing ALL patches.
Return ONE JSON object only:
{"visible": true/false, "bbox_px": {"x0":..,"y0":..,"x1":..,"y1":..} or null,
 "boundary_fully_traced": true/false, "notes": "<short — say if the outline is ambiguous>"}"""

CROP_PROMPT = """You are looking at a CROP of the FRONT elevation drawing, cropped to the full outlined boundary of facade region STC-1.
Hover's printed facade table counts 5 openings in STC-1 across the whole house; this FRONT crop shows the region's front portion only, so fewer than 5 here is a legitimate answer.
QUESTION: which opening IDs are drawn INSIDE the STC-1 outlined boundary in THIS crop?
The report's real opening IDs are exactly these (anything else does not exist): %s
Return ONE JSON object only:
{"opening_ids_inside": [...], "uncertain_ids": [...],
 "boundary_visible": true/false,
 "openings_visible_but_outside": [{"id": "...", "inside_region_labeled": "<label or unknown>"}],
 "notes": "<short>"}
RULES: transcribe printed ID tags only. NEVER invent an ID to reach a count — an honest "I can only see N" is the required behavior. For doors/windows visible in the crop but OUTSIDE the STC-1 outline, list them under openings_visible_but_outside with the region label they appear to sit inside."""


async def ask(system, text, png_bytes, sid):
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ['EMERGENT_LLM_KEY'], session_id=sid,
                   system_message=system).with_model("anthropic", MODEL_NAME)
    msg = UserMessage(text=text, file_contents=[ImageContent(
        image_base64=base64.b64encode(png_bytes).decode('ascii'))])
    return _json_from_reply(await chat.send_message(msg) or '')


async def main():
    t0 = time.time()
    raw = open(PDF, 'rb').read()
    front = next(p for p in _find_view_pages(raw) if p['label'] == 'FRONT')
    doc = fitz.open(stream=raw, filetype='pdf')
    full = '\n'.join(doc.load_page(i).get_text('text') for i in range(doc.page_count))
    real = sorted(set(i for i in re.findall(r'\b[A-Z]{1,4}\d?-\d+\b', full)
                      if re.match(r'^(W|D|SGD)-', i)))
    calls = 1
    b = await ask(BOUNDARY_PROMPT, 'Trace the full STC-1 outline on this FRONT view.',
                  front['png_bytes'], 'probe2-boundary-front')
    print('[boundary]', json.dumps(b)[:350], flush=True)
    if not b.get('visible') or not b.get('bbox_px'):
        print('STC-1 not locatable — stop'); return
    bb = b['bbox_px']
    img = Image.open(io.BytesIO(front['png_bytes']))
    W, H = img.size
    mx = max((bb['x1'] - bb['x0']) * 0.15, 40)
    my = max((bb['y1'] - bb['y0']) * 0.15, 40)
    box = (max(0, bb['x0'] - mx), max(0, bb['y0'] - my),
           min(W, bb['x1'] + mx), min(H, bb['y1'] + my))
    print('page px %dx%d | boundary box %s | crop box %s' % (W, H, bb, [round(v) for v in box]), flush=True)
    crop = img.crop(box)
    buf = io.BytesIO(); crop.save(buf, 'PNG')
    calls += 1
    c = await ask(CROP_PROMPT % ', '.join(real), 'Crop of STC-1 full boundary, FRONT view.',
                  buf.getvalue(), 'probe2-crop-front')
    print('[crop]', json.dumps(c)[:600], flush=True)
    inside = [i for i in (c.get('opening_ids_inside') or []) if i in real]
    invented = [i for i in (c.get('opening_ids_inside') or []) if i not in real]
    print('\n=== FRONT BOUNDARY PROBE RESULT ===')
    print('inside STC-1:', inside, '| uncertain:', c.get('uncertain_ids'), '| invented:', invented)
    print('outside:', c.get('openings_visible_but_outside'))
    print('calls: %d | wall: %.0fs' % (calls, time.time() - t0))

asyncio.run(main())
