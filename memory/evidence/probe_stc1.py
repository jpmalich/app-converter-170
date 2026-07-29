import asyncio, base64, json, os, re, sys, time
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
import fitz
from routes.hover_elevation_read import _find_view_pages, CARDINAL_VIEWS
from routes.hover_vision import MODEL_NAME, _json_from_reply

PDF = '/app/backend/uploads/hover_pdfs/18ac182047fe4def9b2de2063277fa89.pdf'
REGION = 'STC-1'
EXPECTED_COUNT = 5  # Hover's printed FACADES table — DETERMINISTIC TEXT, outranks vision

BBOX_PROMPT = """You are looking at one straight-on elevation drawing from a Hover measurement report.
Facade regions are labeled with tags like WR-1, BR-3, STC-1.
Question: is the region label "%s" printed on THIS drawing?
Return ONE JSON object only:
{"visible": true/false, "bbox_px": {"x0":..,"y0":..,"x1":..,"y1":..} or null, "notes": "<short>"}
bbox_px must be the pixel bounding box of the ENTIRE %s region's boundary (the outlined wall area the label belongs to), not just the label text. Use this image's pixel coordinates. If unsure of the exact boundary, give your best enclosing box and say so in notes. Do NOT guess visible:true if the label is not printed."""

CROP_PROMPT = """You are looking at a CROP of one Hover elevation drawing, cropped around the facade region labeled %s.
Hover's printed facade table says region %s contains EXACTLY %d openings across the whole house (this crop may show only some of them if the region wraps a corner).
Question: which opening IDs are drawn INSIDE the %s boundary in THIS crop?
The report's REAL opening IDs are exactly these (anything else does not exist): %s
Return ONE JSON object only:
{"opening_ids_inside": ["D-1", ...], "uncertain_ids": ["..."], "notes": "<short>"}
RULES: transcribe printed ID tags only; if you cannot confidently read an ID inside the boundary, put it in uncertain_ids with your best guess — NEVER invent an ID to reach a count. If zero openings are inside this crop, return empty lists and say so."""


async def ask(system, text, png_bytes, sid):
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ['EMERGENT_LLM_KEY'], session_id=sid,
                   system_message=system).with_model("anthropic", MODEL_NAME)
    msg = UserMessage(text=text, file_contents=[ImageContent(
        image_base64=base64.b64encode(png_bytes).decode('ascii'))])
    reply = await chat.send_message(msg)
    return _json_from_reply(reply or '')


async def main():
    t0 = time.time()
    raw = open(PDF, 'rb').read()
    pages = [p for p in _find_view_pages(raw) if p['label'] in CARDINAL_VIEWS]
    print('cardinal pages:', [(p['page_num'], p['label']) for p in pages], flush=True)
    # real ID universe from the PDF's own text
    doc = fitz.open(stream=raw, filetype='pdf')
    full = '\n'.join(doc.load_page(i).get_text('text') for i in range(doc.page_count))
    real = sorted(set(i for i in re.findall(r'\b[A-Z]{1,4}\d?-\d+\b', full)
                      if re.match(r'^(W|D|SGD)-', i)))
    calls = 0
    found_ids, uncertain, hits = [], [], []
    for p in pages:
        calls += 1
        b = await ask(BBOX_PROMPT % (REGION, REGION),
                      f"This is the {p['label']} view.", p['png_bytes'],
                      f'probe-bbox-{p["label"]}')
        print(f"[bbox] {p['label']}: {json.dumps(b)[:220]}", flush=True)
        if not b.get('visible') or not b.get('bbox_px'):
            continue
        bb = b['bbox_px']
        # crop with 10% margin using PIL
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(p['png_bytes']))
        W, H = img.size
        mx = (bb['x1'] - bb['x0']) * 0.10
        my = (bb['y1'] - bb['y0']) * 0.10
        box = (max(0, bb['x0'] - mx), max(0, bb['y0'] - my),
               min(W, bb['x1'] + mx), min(H, bb['y1'] + my))
        crop = img.crop(box)
        buf = io.BytesIO(); crop.save(buf, 'PNG')
        calls += 1
        c = await ask(CROP_PROMPT % (REGION, REGION, EXPECTED_COUNT, REGION, ', '.join(real)),
                      f"Crop from the {p['label']} view.", buf.getvalue(),
                      f'probe-crop-{p["label"]}')
        print(f"[crop] {p['label']}: {json.dumps(c)[:300]}", flush=True)
        hits.append(p['label'])
        found_ids += [i for i in (c.get('opening_ids_inside') or []) if i in real]
        uncertain += [i for i in (c.get('uncertain_ids') or [])]
        invented = [i for i in (c.get('opening_ids_inside') or []) if i not in real]
        if invented:
            print(f"  INVENTED on {p['label']}: {invented}", flush=True)
    found = sorted(set(found_ids))
    print('\n=== PROBE RESULT ===', flush=True)
    print('pages where %s located: %s' % (REGION, hits))
    print('opening IDs inside %s (union): %s' % (REGION, found))
    print('uncertain:', sorted(set(uncertain)))
    print('table says %d — crop found %d — %s' % (
        EXPECTED_COUNT, len(found),
        'AGREES' if len(found) == EXPECTED_COUNT else 'DISAGREES — TABLE WINS'))
    print('vision calls: %d | wall time: %.0fs' % (calls, time.time() - t0))

asyncio.run(main())
