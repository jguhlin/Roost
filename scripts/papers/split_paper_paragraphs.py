#!/usr/bin/env python3
"""Split paper/paper.typ into numbered paragraphs for the number-audit Ralph loop.

Outputs:
  paper/paragraphs.json       [{id, section, subsection, kind, text, has_numbers}]
  paper/paragraph_audit.md    checklist table (the loop fills in verdicts)

Rules:
  - Paragraphs split on blank lines; typst directives (#figure/#show/#set/#let
    and pure-annotation lines) are skipped.
  - Everything under a '= Methods' (or '= Data availability') heading is SKIPPED
    except figure captions, which are always kept (kind=caption).
  - Figure captions = text inside #figure(...) blocks outside methods, plus any
    <label> tagged captions.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PAPER = ROOT / "paper" / "main.typ"
OUT_JSON = ROOT / "paper" / "paragraphs.json"
OUT_MD = ROOT / "paper" / "paragraph_audit.md"

lines = PAPER.read_text(encoding="utf-8").splitlines()

SKIP_HEADINGS = {"methods", "data availability", "acknowledgements", "references",
                 "funding", "conflict of interest", "author contributions"}
START_HEADING = "abstract"
section, subsection = "", ""
in_methods = False
paragraphs = []
buf, buf_section, buf_sub, buf_kind = [], "", "", "text"
i = 0
figure_depth = 0
in_caption = False

def flush():
    global buf, buf_section, buf_sub, buf_kind
    text = "\n".join(buf).strip()
    buf = []
    if not text:
        return
    has_numbers = bool(re.search(r"\d", re.sub(r"@[\w.\\]+", "", text)))
    paragraphs.append({
        "id": len(paragraphs) + 1,
        "section": buf_section, "subsection": buf_sub,
        "kind": buf_kind, "text": text,
        "has_numbers": has_numbers,
    })

started = False
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if not started:
        if stripped.startswith("= ") and stripped.lstrip("= ").strip().lower() == START_HEADING:
            started = True
        i += 1
        continue

    # figure environment tracking (typst: #figure( ... ) with caption( ... ))
    if stripped.startswith("#figure("):
        # caption = the caption("...") argument; collect the whole figure block
        depth, j = 1, i
        block = []
        while j + 1 < len(lines) and depth > 0:
            j += 1
            block.append(lines[j])
            depth += lines[j].count("(") - lines[j].count(")")
        btext = "\n".join(block)
        m = re.search(r'caption:\s*\[(.*?)\]\)?\s*(?:<[\w.-]+>)?', btext, re.S)
        if m:
            cap = re.sub(r"\s+", " ", m.group(1).strip())
            paragraphs.append({
                "id": len(paragraphs) + 1, "section": section or "Figures",
                "subsection": subsection, "kind": "caption",
                "text": cap, "has_numbers": True,
            })
        i = j + 1
        continue

    if stripped.startswith("== ") and not in_methods:
        flush(); subsection = stripped.lstrip("= ").strip(); i += 1; continue
    if stripped.startswith("= ") and not stripped.startswith("== "):
        flush()
        section = stripped.lstrip("= ").strip()
        in_methods = section.lower() in SKIP_HEADINGS
        subsection = ""
        i += 1; continue

    if in_methods:
        if buf:
            text = "\n".join(buf).strip()
            if re.search(r"\d", text):
                paragraphs.append({"id": len(paragraphs) + 1, "section": section,
                                   "subsection": subsection, "kind": "methods-skip",
                                   "text": text[:300], "has_numbers": True})
            buf = []
        i += 1
        continue

    if (not stripped or stripped.startswith(("//", "#show", "#set ", "#let ", "#import",
            "#align", "#title", "#block", "#super", "*Contact:*"))
            and not stripped.startswith("#figure")):
        if not stripped:
            flush()
        i += 1; continue

    if paragraphs and buf == []:
        buf_section, buf_sub, buf_kind = section, subsection, "text"
    buf.append(line)
    i += 1
flush()

# tag placeholders: skip paragraphs that are just the template header
paragraphs = [p for p in paragraphs if p["text"] and not p["text"].startswith("Joseph Guhlin#super")]

OUT_JSON.write_text(json.dumps(paragraphs, indent=1), encoding="utf-8")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("# Paper paragraph audit — paper/paper.typ\n\n")
    f.write("Loop: check every paragraph with numbers against repo artifacts. "
            "Verdicts per claim: ✅ confirmed · ❌ stale (→ correct) · ⚠️ unverifiable · "
            "🔁 internal inconsistency. Methods sections skipped; captions included.\n\n")
    f.write("| # | Section | Kind | Numbers | First words | Verdict |\n|---|---|---|---|---|---|\n")
    for p in paragraphs:
        first = re.sub(r"\s+", " ", p["text"])[:70]
        f.write(f"| {p['id']} | {p['section'] or '·'}{' / ' + p['subsection'] if p['subsection'] else ''} "
                f"| {p['kind']} | {'yes' if p['has_numbers'] else '—'} | {first}… | |\n")
    f.write("\n## Findings\n\n(findings appended per paragraph below)\n")

print(f"paragraphs: {len(paragraphs)} "
      f"(checkable: {sum(1 for p in paragraphs if p['has_numbers'])}, "
      f"captions: {sum(1 for p in paragraphs if p['kind'] == 'caption')})")
for p in paragraphs:
    mark = "N" if p["has_numbers"] else " "
    print(f"  [{mark}] {p['id']:3} {p['section'][:24]:26} {p['kind']:8} {re.sub(r'[^ -~]','', re.sub(chr(10),' ',p['text']))[:80]}")
