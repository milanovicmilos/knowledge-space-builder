"""Extract full item descriptions from COINS PDF for each item in lattice and evaluate all edges.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

PDF_PATH = Path("learning_space_generator/data/COINS-alle-Cluster-CH.pdf")
LATTICE_PATH = Path("output/matheGesamt_test3/knowledge_space_lattice_k40.json")

# Heuristic keywords indicating higher complexity
ADV_KEYWORDS = [
    'prove', 'justify', 'derive', 'explain', 'show that', 'prove that', 'demonstrate',
    'apply', 'calculate', 'determine', 'solve', 'evaluate', 'simplify', 'transform',
    'construct', 'prove', 'argument', 'explain why'
]
BASIC_KEYWORDS = [
    'identify', 'recognise', 'recognize', 'name', 'match', 'choose', 'select', 'compute simple',
    'calculate', 'find', 'read', 'circle', 'tick', 'true', 'false'
]


def extract_pdf_pages_text(pdf_path: Path):
    from PyPDF2 import PdfReader
    reader = PdfReader(str(pdf_path))
    pages = [p.extract_text() or "" for p in reader.pages]
    return pages


def collect_item_strings(lattice):
    items = set()
    for state, succs in lattice.items():
        if state and state != "{}":
            for it in state.strip('{}').split(','):
                s = it.strip()
                if s:
                    items.add(s)
        for succ in succs:
            if succ and succ != "{}":
                for it in succ.strip('{}').split(','):
                    s = it.strip()
                    if s:
                        items.add(s)
    return sorted(items)


def find_snippet_for_item(pages, item):
    # Search exact item string across pages; return page index and snippet
    for i, text in enumerate(pages):
        if item in text:
            idx = text.index(item)
            start = max(0, idx - 200)
            end = min(len(text), idx + len(item) + 200)
            snippet = text[start:end].replace('\n', ' ')
            return i+1, snippet
    # fallback: search by item short code mXX
    m = re.search(r'm\d{2}', item)
    if m:
        code = m.group(0)
        for i, text in enumerate(pages):
            if code in text:
                idx = text.index(code)
                start = max(0, idx - 200)
                end = min(len(text), idx + len(code) + 200)
                snippet = text[start:end].replace('\n', ' ')
                return i+1, snippet
    return None, None


def complexity_score(snippet: str):
    if not snippet:
        return 0.0
    s = snippet.lower()
    adv = sum(1 for k in ADV_KEYWORDS if k in s)
    basic = sum(1 for k in BASIC_KEYWORDS if k in s)
    # simple score: (adv - basic) normalized
    return (adv - basic)


def main():
    lattice = json.loads(LATTICE_PATH.read_text())
    pages = extract_pdf_pages_text(PDF_PATH)
    items = collect_item_strings(lattice)

    # Map item -> (page, snippet, score)
    item_info = {}
    for it in items:
        page, snippet = find_snippet_for_item(pages, it)
        score = complexity_score(snippet)
        item_info[it] = {'page': page, 'snippet': snippet, 'score': score}

    # Evaluate every edge
    edge_reports = []
    for src, succs in lattice.items():
        if src == '{}':
            # handle successors from empty state: map succ items
            for succ in succs:
                # treat succ as state
                succ_items = [x.strip() for x in succ.strip('{}').split(',') if x.strip()]
                for s_item in succ_items:
                    # edge: empty -> s_item
                    info_t = item_info.get(s_item)
                    edge_reports.append({
                        'source_state': '{}',
                        'target_state': succ,
                        'source_items': [],
                        'target_items': succ_items,
                        'target_snippets': [ (s_item, item_info.get(s_item)) ],
                        'judgement': 'info-only'
                    })
            continue
        src_items = [x.strip() for x in src.strip('{}').split(',') if x.strip()]
        for succ in succs:
            succ_items = [x.strip() for x in succ.strip('{}').split(',') if x.strip()]
            # compute average complexity score for src and succ
            src_scores = [item_info.get(it, {}).get('score', 0) for it in src_items]
            succ_scores = [item_info.get(it, {}).get('score', 0) for it in succ_items]
            avg_src = sum(src_scores)/len(src_scores) if src_scores else 0
            avg_succ = sum(succ_scores)/len(succ_scores) if succ_scores else 0
            # judgement: OK if avg_succ >= avg_src (allow small negative differences)
            judgement = 'OK' if avg_succ + 0.1 >= avg_src else 'SUS' 
            edge_reports.append({
                'source_state': src,
                'target_state': succ,
                'source_items': src_items,
                'target_items': succ_items,
                'avg_src_score': avg_src,
                'avg_succ_score': avg_succ,
                'judgement': judgement
            })

    # Print detailed report for user (all edges)
    print(f"Total edges evaluated: {len(edge_reports)}")
    sus = [e for e in edge_reports if e.get('judgement') == 'SUS']
    print(f"Suspicious edges by heuristic: {len(sus)}\n")

    for idx, e in enumerate(edge_reports, 1):
        print('\n' + '='*60)
        print(f"Edge {idx}: {e['source_state']}  ->  {e['target_state']}")
        print(f"Judgement: {e.get('judgement')}")
        # print source items/snippets
        if e.get('source_items'):
            print(" Source items:")
            for it in e['source_items']:
                info = item_info.get(it, {})
                print(f"   - {it} (page {info.get('page')}) snippet: {(info.get('snippet') or '')[:180]}")
        else:
            print(" Source: <empty state>")
        # print target items/snippets
        print(" Target items:")
        for it in e.get('target_items', []):
            info = item_info.get(it, {})
            print(f"   - {it} (page {info.get('page')}) snippet: {(info.get('snippet') or '')[:180]}")
        # print scores if available
        if 'avg_src_score' in e:
            print(f" Avg src score: {e.get('avg_src_score')}  Avg target score: {e.get('avg_succ_score')}")

    print('\nDone.')

if __name__ == '__main__':
    main()
