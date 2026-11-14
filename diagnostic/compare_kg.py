"""Compare the v1 knowledge graph (prerequisite_edges.xlsx, used by the app) with v2.

    python -m diagnostic.compare_kg      # writes reports/kg_v2_vs_v1.{md,json}

Every measure is computed the same way for both graphs from the chapter 1-5 clean text.
"""
import json
import re
import sys
from collections import defaultdict
from diagnostic import engine as e, kg_v2
from diagnostic.evaluate_rag import OUT


def sections(language='en'):
    """[(chapter, 'n.m Title', text)] for every numbered section of chapters 1-5."""
    out = []
    for ch in kg_v2.CHAPTER_FILES:
        current, buf = None, []
        for p in kg_v2.body_pages(ch, 'en'):
            for line in p['text'].split('\n'):
                m = re.match(rf'^{ch}\.(\d+) [A-Z].*', line.strip())
                if m:
                    if current:
                        out.append((ch, current, ' '.join(buf)))
                    current, buf = line.strip(), []
                else:
                    buf.append(line)
        if current:
            out.append((ch, current, ' '.join(buf)))
    return out


def strongly_connected(nodes, edges):
    """Tarjan; returns the set of nodes that lie on a directed cycle."""
    graph = defaultdict(list)
    for a, b in edges:
        graph[a].append(b)
    index, low, stack, on, result, counter = {}, {}, [], set(), set(), [0]

    def visit(v):
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); on.add(v)
        for w in graph[v]:
            if w not in index:
                visit(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in graph[v]:
                result.update(comp)
    sys.setrecursionlimit(10000)
    for v in nodes:
        if v not in index:
            visit(v)
    return result


def measure(name, nodes, edges):
    """nodes: [{'id','en','hi','chapter'(int or 0)}]; edges: [(a, b, has_evidence)]."""
    secs = sections()
    taught = [n for n in nodes if n['chapter']]
    en_ok = [n for n in taught if kg_v2.name_found(n['en'], 'en', [n['chapter']])]
    hi_ok = [n for n in taught if kg_v2.name_found(n['hi'], 'hi', [n['chapter']])]
    names = defaultdict(list)
    for n in nodes:
        names[n['en'].lower()].append(n['id'])
    cyc = strongly_connected([n['id'] for n in nodes], [(a, b) for a, b, _ in edges])
    by_ch = defaultdict(int)
    for n in taught:
        by_ch[n['chapter']] += 1
    covered = [s for s in secs if any(n['chapter'] == s[0] and re.search(kg_v2._en_pattern(re.sub(r'\s*\(.*?\)', '', n['en'])), s[2], re.I)
                                      for n in taught)]
    return {'graph': name, 'concepts': len(nodes), 'concepts_per_chapter': {f'CH{c:02d}': by_ch.get(c, 0) for c in kg_v2.CHAPTER_FILES},
            'chapters_covered': sum(1 for c in kg_v2.CHAPTER_FILES if by_ch.get(c)),
            'sections_total': len(secs), 'sections_with_a_named_concept': len(covered),
            'en_name_in_chapter_text': len(en_ok) / len(taught), 'hi_name_in_chapter_text': len(hi_ok) / len(taught),
            'en_names_not_in_text': sorted(n['en'] for n in taught if n not in en_ok),
            'hi_names_not_in_text': sorted(f"{n['en']} / {n['hi']}" for n in taught if n not in hi_ok),
            'duplicate_names': {k: v for k, v in names.items() if len(v) > 1},
            'edges': len(edges), 'nodes_on_cycles': len(cyc), 'edges_on_cycles': sum(a in cyc and b in cyc for a, b, _ in edges),
            'edges_with_text_reference': sum(bool(x) for _, _, x in edges) / len(edges)}


def v1():
    rows = e.load_graph_rows()
    nodes = {}
    for r in rows:
        for side in ('source', 'target'):
            nodes[r[side + '_id']] = {'id': r[side + '_id'], 'en': r[side + '_en'], 'hi': r[side + '_hi'],
                                      'chapter': int(r[side + '_chapter'][2:])}
    edges = [(r['source_id'], r['target_id'], bool(r.get('supporting_passage_ids'))) for r in rows]
    return list(nodes.values()), edges


def v2():
    nodes = [{'id': c[0], 'en': c[4], 'hi': c[5], 'chapter': c[1]} for c in kg_v2.CONCEPTS]
    edges = [(a, b, bool(re.search(r'\b[1-5]\.\d+\b|Table|"', why))) for a, b, why in kg_v2.EDGES]
    return nodes, edges


def run():
    result = {'v1': measure('v1 (prerequisite_edges.xlsx)', *v1()), 'v2': measure(kg_v2.VERSION, *v2())}
    (OUT / 'kg_v2_vs_v1.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    a, b = result['v1'], result['v2']
    pct = lambda x: f'{100 * x:.0f}%'
    rows = [('Concepts (all)', a['concepts'], b['concepts']),
            ('Chapters with concepts (of 5)', a['chapters_covered'], b['chapters_covered']),
            *[(f'  concepts in {k}', a['concepts_per_chapter'][k], b['concepts_per_chapter'][k]) for k in a['concepts_per_chapter']],
            (f"Sections (of {a['sections_total']}) where a concept name occurs", a['sections_with_a_named_concept'], b['sections_with_a_named_concept']),
            ('English name occurs in its chapter text', pct(a['en_name_in_chapter_text']), pct(b['en_name_in_chapter_text'])),
            ('Hindi name occurs in its Hindi chapter text', pct(a['hi_name_in_chapter_text']), pct(b['hi_name_in_chapter_text'])),
            ('Duplicate concept names', len(a['duplicate_names']), len(b['duplicate_names'])),
            ('Prerequisite edges', a['edges'], b['edges']),
            ('Nodes on a prerequisite cycle', a['nodes_on_cycles'], b['nodes_on_cycles']),
            ('Edges inside a cycle', a['edges_on_cycles'], b['edges_on_cycles']),
            ('Edges citing a textbook location', pct(a['edges_with_text_reference']), pct(b['edges_with_text_reference']))]
    L = ['# Knowledge graph v2 vs v1', '', 'Same measures, same chapter 1-5 clean text, for both graphs. '
         '"Name occurs" is a strict check of the concept label itself (prior-knowledge roots excluded).', '',
         '| Measure | v1 | v2 |', '| --- | ---: | ---: |', *[f'| {m} | {x} | {y} |' for m, x, y in rows], '',
         '## v1 names not found in the text', '', '- English: ' + ', '.join(a['en_names_not_in_text']),
         '- Hindi: ' + ', '.join(a['hi_names_not_in_text']), '', '## v2 names not found in the text', '',
         '- English: ' + ', '.join(b['en_names_not_in_text']), '- Hindi: ' + ', '.join(b['hi_names_not_in_text']), '',
         'v2 misses are descriptive labels whose textbook term is an anchor (e.g. "vertex of an angle" → "vertex"), '
         'and लंब रेखाएँ, which the Hindi extraction prints as "लब रेखाएँ".', '',
         '## Duplicates in v1', '', *[f'- {k}: {", ".join(v)}' for k, v in a['duplicate_names'].items()], '',
         '## Limits', '', '- v2 is AI-authored from the text; prerequisite edges await human review, like v1.',
         '- Finding a name in the text shows grounding, not that the prerequisite direction is pedagogically right.',
         '- The app still loads v1; switching it to v2 is a separate decision (IDs used by the bank are kept in v2).']
    (OUT / 'kg_v2_vs_v1.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    r = run()
    print(json.dumps({k: {x: y for x, y in v.items() if not isinstance(y, (list, dict))} for k, v in r.items()}, ensure_ascii=False, indent=1))
