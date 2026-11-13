"""Generate a bilingual diagnostic review pack with shaped Devanagari text."""
import html
import json
from pathlib import Path
import fitz
from diagnostic import engine as e

OUT = e.ROOT / 'output' / 'pdf' / 'Concept_Atlas_Diagnostic_Review.pdf'
CSS = '''
body {font-family: sans-serif; font-size:10pt; color:#334a42; line-height:1.45;}
h1 {font-size:27pt; line-height:1.18; color:#234b3c; margin:0 0 14pt;}
h2 {font-size:20pt; color:#234b3c; margin:0 0 9pt;}
h3 {font-size:11pt; color:#315e4a; margin:0 0 5pt;}
p {margin:5pt 0 9pt;} .kicker {font-size:8pt; letter-spacing:1.4pt; color:#729580; margin:0 0 13pt;}
.intro {font-size:12pt; color:#82988a; margin-bottom:20pt;}
.item {padding:13pt 0; border-top:1pt solid #dfebe2; page-break-inside:avoid;}
.hi {font-family:sans-serif; color:#647d6c; font-size:10.5pt; margin:7pt 0;}
.meta {font-size:8.5pt; color:#829486; margin:5pt 0;}
.answer {font-size:9pt; color:#395e46; margin:6pt 0;}
.note {padding:12pt; background:#f0f6f0; border:1pt solid #dfeade; margin:15pt 0;}
li {margin:7pt 0;} .rule {padding:10pt 0;border-bottom:1pt solid #e0e9e0;}
table {width:100%; border-collapse:collapse; font-size:10pt;} td,th {padding:10pt; border-bottom:1pt solid #dfe9e1;text-align:left;} th {background:#f1f6f1;}
'''
ESC = lambda text: html.escape(str(text))


def create():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bank = e.load_bank()
    doc = fitz.open()

    def add(content, label):
        page = doc.new_page(width=595.28, height=841.89)
        spare, scale = page.insert_htmlbox(fitz.Rect(45, 54, 550, 778), content, css=CSS, scale_low=1)
        if spare < 0 or scale != 1:
            raise RuntimeError(f'Content does not fit: {label}')
        page.draw_line((45, 798), (550, 798), color=(.86,.91,.87), width=.6)
        page.insert_text((45, 815), 'CONCEPT ATLAS  |  DIAGNOSTIC REVIEW COPY', fontsize=7, color=(.48,.57,.51))
        page.insert_text((510, 815), f'{len(doc):02}', fontsize=8, color=(.48,.57,.51))

    add('''<p class="kicker">CONCEPT ATLAS / CLASS 6 MATHEMATICS</p>
    <h1>Bilingual diagnostic<br>question bank</h1><p class="intro">English and Hindi questions, answer keys and diagnostic decision rules.</p>
    <div class="note"><b>30 questions. 10 assessed concepts. At most 3 questions per interaction.</b><p>Prepared for developer and final content review. The learner app keeps this material outside its navigation.</p></div>
    <h2>How the learner check works</h2><ol><li><b>Choose what to learn.</b> Ask a maths question in English or Hindi, or select a supported topic. Unclear mappings require clarification.</li><li><b>Gather a little evidence.</b> Answer one question at a time. The next item uses response evidence and proposed prerequisites.</li><li><b>See the results.</b> Review supported understanding, possible difficulty and insufficient evidence. Untested prerequisites stay unassessed.</li></ol>
    <h3>Concepts in this bank</h3><p>Number pattern; odd number; even number; square number; line segment; angle; right angle; acute angle; place value; digit sum.</p>
    <h3>Review status</h3><p>First AI content/key review completed. Final human review, independent pilot expectations, pedagogical graph validation and textbook alignment are pending.</p>
    <p class="meta">Original development questions, not quoted from NCERT. Passage IDs originate from the provisional knowledge graph. The source textbook passages are not included and have not been verified.</p>
    <p class="meta">Prepared 1 November 2026. Bank and rule version: diagnostic-v1.</p>''', 'cover')

    grouped = {}
    for q in bank:
        grouped.setdefault(q['concept_id'], []).append(q)
    for concept, items in grouped.items():
        first = items[0]
        content = f'<p class="kicker">QUESTION BANK / {ESC(concept)}</p><h2>{ESC(first["concept_en"].title())}</h2><p class="hi">{ESC(first["concept_hi"])}</p>'
        for q in items:
            scoring = 'MCQ: exact correct option letter, case insensitive = 1; another A-D letter = 0; other text = unscorable.' if q['type'] == 'mcq' else 'Numerical: equal numeric value = 1; another number = 0; other text = unscorable. Devanagari digits accepted.'
            content += f'''<div class="item"><h3>{ESC(q['id'])} | {'Multiple choice' if q['type']=='mcq' else 'Short numerical'}</h3><p>{ESC(q['en'])}</p><p class="hi">{ESC(q['hi'])}</p><p class="answer"><b>Correct answer:</b> {ESC(q['answer'])}</p><p class="meta"><b>Scoring:</b> {ESC(scoring)}</p><p class="meta"><b>An incorrect response may indicate:</b> {ESC(q['possible_difficulty'])}</p></div>'''
        ids = sorted({ref['passage_ids'] for q in items for ref in q['source_references'] if ref['passage_ids']})
        content += '<p class="meta"><b>Graph reference examples (unverified):</b> '+ESC('; '.join(ids[:2]) or 'No passage identifiers provided.')+'</p>'
        content += '<p class="meta">Final reviewer: ____________________  Date: __________  Decision: approve / revise / reject</p>'
        add(content, concept)

    add('''<p class="kicker">METHOD / DIAGNOSTIC-V1</p><h2>Selection and decision rules</h2><p class="intro">Transparent development rules. Human review remains pending.</p>
    <h3>Which question is selected next?</h3><ol><li>Eligible concepts are the target and its direct incoming prerequisites that have bank items. Self-loops are excluded.</li><li>Check saved same-version response history; use at most the latest two observations per concept. Their items are excluded from reuse.</li><li>First follow up a concept with exactly one valid observation. Otherwise prioritize direct prerequisites before the target, descending graph confidence, then concept ID.</li><li>Choose the lowest unused item ID in that order. Continue unresolved concepts where items and budget remain.</li><li>Stop after at most three new questions, when no unresolved eligible item remains, or when the learner chooses to finish. Invalid or “not sure” responses consume a question but provide no knowledge evidence.</li></ol>
    <h3>How is evidence interpreted?</h3><div class="rule"><b>Evidence supports understanding</b><p>At least two correct valid responses and no incorrect valid response for that assessed concept.</p></div><div class="rule"><b>Possible prerequisite difficulty</b><p>At least two incorrect valid responses and no correct valid response. This remains a tentative finding.</p></div><div class="rule"><b>Insufficient evidence</b><p>Mixed answers, one valid answer, or no valid answers. A single incorrect response cannot trigger a difficulty label.</p></div>
    <div class="note">A concept with no question asked in the current interaction stays <b>unassessed</b>, even if saved history exists. No difficulty is propagated to untested prerequisites.</div>
    <p class="meta">Reports include asked items, responses, scores, answer keys, historical evidence used, diagnostic statuses and available reference identifiers. These cutoffs are not psychometrically validated.</p>''', 'rules')
    summary = json.loads((e.ROOT/'reports'/'pilot_summary.json').read_text())
    rows = ''.join(f'<tr><td>{ESC(method)}</td><td>{v["mapping_correct"]}/20</td><td>{v["correct_diagnoses"]}</td><td>{v["false_diagnoses"]}</td><td>{v["unresolved_concepts"]}</td><td>{v["questions_asked"]}</td></tr>' for method,v in summary['results'].items())
    add('''<p class="kicker">REVIEW / PRELIMINARY TESTING</p><h2>Pilot notes and review checklist</h2><p class="intro">20 synthetic cases, each run under both methods with the same bank and maximum three-question budget.</p>
    <table><tr><th>Method</th><th>Mapping matches</th><th>Correct labels</th><th>False labels</th><th>Unresolved concepts</th><th>Questions</th></tr>'''+rows+'''</table><p class="meta">False-label counts exclude unresolved concepts and mapping failures. Synthetic results are not a learner study or evidence of general diagnostic validity.</p>
    <h3>Observed limitations</h3><ul><li>A Hindi right-angle question also mentioned degrees, causing clarification rather than the expected unique map.</li><li>A Hindi fraction-addition question matched generic addition, despite fractions being out of scope.</li><li>Odd/even concept names occur in two chapters and require clarification.</li><li>Three questions leave many prerequisites untested. Mixed and ambiguous responses remain insufficient.</li></ul>
    <h3>Final review checklist</h3><ul><li>Check both language versions for equivalence and age-appropriate vocabulary.</li><li>Recalculate each key and confirm one clear intended answer.</li><li>Review whether errors support the tentative difficulty statements.</li><li>Review selection and diagnostic decision rules independently.</li><li>Verify textbook passage identifiers and prerequisite relationships.</li><li>Review expected pilot mappings and diagnoses independently before treating them as a gold standard.</li></ul>
    <p class="meta">Some endpoint and right-angle items overlap in what they test; repeated correct answers do not establish full concept mastery. Number-pattern items assume the conventional simple continuation.</p>
    <div class="note"><b>Human approval remains pending.</b><p>Record corrections and sign-off in reports/review_checklist.csv. Keep the existing pilot as an error record; use a fresh independent case set after tuning.</p></div>''','pilot and review')
    doc.set_metadata({'title':'Concept Atlas - Bilingual Diagnostic Review', 'author':'Concept Atlas', 'subject':'30 bilingual diagnostic questions and provisional decision rules'})
    doc.save(OUT, garbage=4, deflate=True)
    print(f'{OUT} ({len(doc)} pages)')
    return OUT


if __name__ == '__main__':
    create()
