// SEND-144 (Howard ruled 2026-08-28) — CANDIDATE EDGES ON A BODY ZONE.
// The bottom edge is where starter would run, the verticals are where the
// corners would be, the top is the eave/frieze line. They are DASHED LINES
// WITH A WORD and nothing else: no length, no LF, no key written. Starter,
// corners, soffit and fascia stay named refusals until the mark-type send —
// these lines are so Howard can see what to pull, not a second quantity
// engine.
import React from "react";

const EDGE = "#F59E0B";

export const CandidateEdges = ({ marks, nMark }) => (
  <>
    {marks
      .filter((m) => m.kind === "siding_zone" && (m.points || []).length === 4)
      .map((m) => {
        const p = nMark(m).map((q) => ({ x: q.x * 100, y: q.y * 100 }));
        const [tl, tr, br, bl] = p;
        const lines = [
          { key: "starter", word: "starter candidate", a: bl, b: br },
          { key: "corner-left", word: "corner candidate", a: tl, b: bl },
          { key: "corner-right", word: "corner candidate", a: tr, b: br },
          { key: "eave", word: "eave / frieze candidate", a: tl, b: tr },
        ];
        return (
          <g key={`cand-${m.id}`} data-testid={`photo-takeoff-candidate-edges-${m.id}`}>
            {lines.map((l) => (
              <g key={l.key}>
                <line x1={l.a.x} y1={l.a.y} x2={l.b.x} y2={l.b.y}
                  stroke={EDGE} strokeWidth="0.55" strokeDasharray="1.6 1.2"
                  data-testid={`photo-takeoff-candidate-${l.key}-${m.id}`} />
                <text
                  x={(l.a.x + l.b.x) / 2} y={(l.a.y + l.b.y) / 2 - 0.6}
                  fill={EDGE} fontSize="1.6" fontWeight="700"
                  textAnchor="middle" style={{ paintOrder: "stroke" }}
                  stroke="#27272A" strokeWidth="0.35">
                  {l.word}
                </text>
              </g>
            ))}
          </g>
        );
      })}
  </>
);

export default CandidateEdges;
