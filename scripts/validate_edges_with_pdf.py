"""Validate knowledge-space edges against COINS PDF clusters.

Outputs a per-edge report indicating whether the progression follows expected difficulty levels.
"""
import json
import re
from pathlib import Path

PDF_PATH = Path("learning_space_generator/data/COINS-alle-Cluster-CH.pdf")
LATTICE_PATH = Path("output/matheGesamt_test3/knowledge_space_lattice_k40.json")


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(pdf_path))
        texts = []
        for p in reader.pages:
            try:
                texts.append(p.extract_text() or "")
            except Exception:
                texts.append("")
        return "\n".join(texts)
    except Exception as e:
        print(f"Warning: PyPDF2 not available or failed ({e}). Trying fallback to raw bytes search.")
        try:
            # fallback: return bytes as latin-1 decoded string (not ideal)
            data = pdf_path.read_bytes()
            return data.decode('latin-1', errors='ignore')
        except Exception as e2:
            print(f"Fallback reading failed: {e2}")
            return ""


def parse_area_codes_from_text(text: str):
    # Find all unique occurrences of mXY where X in [1-3] and Y in [0-9]{1,2}
    # We'll restrict to m11..m34 pattern
    codes = set(re.findall(r"m[1-3][0-9]", text))
    # Keep only likely cluster codes m11..m34
    codes = {c for c in codes if 11 <= int(c[1:]) <= 34}
    return sorted(codes)


def parse_item_code(item: str):
    # item format: s1m12b021neu or similar
    m = re.search(r"m(\d{2})", item)
    if not m:
        return None
    code = f"m{m.group(1)}"
    return code


def load_lattice(lattice_path: Path):
    with open(lattice_path) as f:
        return json.load(f)


def analyze_edges(lattice, pdf_codes):
    edges = []
    for src, succs in lattice.items():
        if src == "{}":
            continue
        src_items = [it.strip() for it in src.strip('{}').split(',') if it.strip()]
        src_areas = {parse_item_code(it) for it in src_items}
        src_areas.discard(None)
        for succ in succs:
            succ_items = [it.strip() for it in succ.strip('{}').split(',') if it.strip()]
            succ_areas = {parse_item_code(it) for it in succ_items}
            succ_areas.discard(None)
            if not src_areas or not succ_areas:
                edges.append((src, succ, src_areas, succ_areas, 'unknown'))
                continue
            # For reporting, create pairs (src_area -> succ_area) for all combos
            for sa in sorted(src_areas):
                for ta in sorted(succ_areas):
                    edges.append((sa, ta, src, succ, None))
    
    report = []
    suspicious = []
    for e in edges:
        if e[4] is None:
            sa, ta, src_state, succ_state = e[0], e[1], e[2], e[3]
            # levels
            try:
                slevel = int(sa[1])
                tlevel = int(ta[1])
            except Exception:
                slevel = None
                tlevel = None
            note = ''
            ok = True
            # Basic check: source should not be higher level than target (slevel > tlevel suspicious)
            if slevel is not None and tlevel is not None:
                if slevel > tlevel:
                    note = f'Unexpected: {sa} (level {slevel}) -> {ta} (level {tlevel})'
                    ok = False
                elif slevel == 1 and tlevel == 3:
                    note = f'Skips level: {sa} (basic) -> {ta} (advanced)'
                    ok = False
            # Check PDF presence
            if sa not in pdf_codes or ta not in pdf_codes:
                note = (note + ' PDF-missing-code').strip()
                ok = False
            report.append({'source_area': sa, 'target_area': ta, 'source_state': src_state, 'target_state': succ_state, 'ok': ok, 'note': note})
            if not ok:
                suspicious.append(report[-1])
    return report, suspicious


def main():
    print('Reading lattice...')
    lattice = load_lattice(LATTICE_PATH)
    print('Extracting PDF text...')
    text = extract_pdf_text(PDF_PATH)
    pdf_codes = parse_area_codes_from_text(text)
    print(f'Found cluster codes in PDF (sample): {pdf_codes[:20]}')

    report, suspicious = analyze_edges(lattice, pdf_codes)
    print('\nEdge report:')
    for r in report:
        mark = 'OK' if r['ok'] else 'SUS'
        print(f" - {r['source_area']} -> {r['target_area']}  [{mark}] {r['note']}")

    print(f"\nTotal edges checked: {len(report)}; suspicious: {len(suspicious)}")
    if suspicious:
        print('\nSuspicious edges:')
        for s in suspicious:
            print(f" - {s['source_area']} -> {s['target_area']}: {s['note']}")
    else:
        print('\nNo suspicious edges found.')

if __name__ == '__main__':
    main()
