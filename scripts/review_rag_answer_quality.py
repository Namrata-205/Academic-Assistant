"""Aggregate explicit AI review annotations, not an independent human benchmark.

The semantic labels below were assigned after reading each saved answer and its
actual cited excerpt. Code verifies provenance/arithmetic and aggregates labels;
it does not pretend to infer semantic correctness with string matching.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/phase2_evaluation_v2'
REVIEWED_INPUT_HASHES = {
 'workflow_traces.json':'d7986d8817f8545b5116d89ef2c1d3938463072c042e18a962552267f1936e87',
 'complete_chat_cycles.json':'577b785fe695e639176ceb2eb2133ed4fba3361074f42908eebcc2e58aac595e',
 'diagnosed_answer_quality_cases.json':'3c05f7123f78a6d8126192391d70ea0d943447cabd58ccf404d192d6a3306883',
}
# Each tuple: paragraph index, separately reviewed claim, fully supported EN/HI,
# rationale for the citation-support decisions. Original examples may be derived
# from an explicitly stated cited rule plus checked arithmetic; exact numerical
# copying is not required. Partial support does not pass the full-support rubric.
CLAIMS = {
 'MATH6_C0106': [
  (0,'A complete graph joins each distinct pair of points with one edge.',False,False,
   'EN cited excerpt only asks to count lines; HI only lists complete graphs as shape sequences. Neither gives the defining pairwise-edge rule.'),
  (1,'Four points joined pairwise once have six edges.',False,False,
   'The result is mathematically correct, but the cited excerpts do not give the construction rule or enough textual evidence to derive the edge count. Diagrams not supplied in retrieved text were not inferred.')],
 'MATH6_C0111': [
  (0,'The stated vertex/ray/protractor-mark/second-ray procedure constructs the required angle.',False,False,
   'The excerpts introduce a 30-degree construction, vertex and reference arm, but omit the actual protractor alignment/marking steps. Full procedural support is missing.'),
  (1,'The described activity is drawing an angle of a given measure.',True,True,
   'Both excerpts explicitly describe drawing a 30-degree angle using a protractor, supporting the activity identification.')],
 'MATH6_C0113': [
  (0,'Mental calculation can simplify arithmetic using number relationships.',True,False,
   'EN explicitly says mental calculation is simpler and demonstrates numerical decompositions. HI excerpt contains only largest/smallest-number sum constraints, not a mental strategy.'),
  (0,'Adding nine can be performed by adding ten and subtracting one.',False,False,
   'Neither cited excerpt states the compensation strategy. Mathematical truth alone does not establish citation entailment.'),
  (1,'The worked calculation 52 + 9 equals 61.',False,False,
   'Arithmetic is correct, but the cited excerpts do not state the compensation rule used to ground this worked example.')],
 'MATH6_C0117': [
  (0,'Frequency means the number of occurrences of a data value/category.',False,False,
   'EN has a number-of-times letter-count exercise but no explicit identification of that count as frequency; HI assigns example frequencies without explaining occurrence counting. Both are partial context under this strict rubric.'),
  (1,'The supplied eight-value list contains three occurrences of five.',False,False,
   'Count is independently correct. The cited text lacks the defining counting rule for the claim; matching the topic alone is insufficient.')],
 'MATH6_C0130': [
  (0,'A prime is a whole number greater than one having exactly two positive factors, one and itself.',False,False,
   'Both cited excerpts ask prime-number exercises and list 13 and 31 as primes; neither supplies the factor-based definition.'),
  (1,'The positive factors of sixteen are 1, 2, 4, 8 and 16.',False,False,
   'Factor list is correct but is not established by the cited exercises, which do not supply a factor test.'),
  (1,'Sixteen is not prime.',False,False,
   'The claim follows from the answer definition and checked factors, but the necessary definition/test is absent from the actual citation.')],
 'MATH6_C0158': [
  (0,'Rectangle area is length multiplied by breadth.',True,False,
   'EN directly states rectangle area is length times width. HI excerpt asks about equal-area rectangles and a diagonal without stating the multiplication formula.'),
  (1,'An 8 cm by 3 cm rectangle has area 24 square cm.',True,False,
   'EN states the governing area rule and square-unit convention; multiplication independently verifies the original example. HI citation omits the governing area rule.')],
 'MATH6_C0180': [
  (0,'Equivalent fractions with a common denominator are used to add fractions.',True,False,
   'EN explicitly describes equivalent fractions and a common multiple of denominators. HI excerpt poses a half-plus-quarter food problem without supplying this method.'),
  (0,'After conversion to a common denominator, add numerators and keep that denominator.',False,False,
   'EN excerpt ends at the start of step 2; the numerator-addition step is missing. HI excerpt also omits the rule.'),
  (1,'One fifth plus one eighth is thirteen fortieths.',False,False,
   'Fraction arithmetic is independently correct, but the retrieved cited excerpts do not provide the complete addition rule for grounding the example.')],
 'MATH6_C0191': [
  (0,'The fixed reference point is the centre of the circle.',True,True,
   'Both cited excerpts explicitly identify point P as the circle centre.'),
  (0,'The distance from the centre to any point on the circle is its radius.',True,True,
   'Both excerpts directly define radius as this distance.'),
  (1,'A circle with diameter ten cm has radius five cm.',False,False,
   'Correct geometry, but neither attached excerpt states the diameter-equals-twice-radius relationship.')],
 'MATH6_C0203': [
  (0,'Rotational symmetry means a non-full turn can make a figure coincide with itself.',True,False,
   'EN explicitly connects a 90-degree rotation, unchanged appearance and rotational symmetry. HI selected excerpt discusses radial arms and symmetry angles but omits the unchanged-appearance criterion.'),
  (1,'A regular octagon has rotational order eight.',False,False,
   'Correct, but the cited windmill/radial-arm examples do not state a regular-polygon order rule or show this octagon.')],
 'MATH6_C0216': [
  (0,'Subtracting an integer is equivalent to adding its additive inverse.',False,False,
   'EN discusses integer ordering, not subtraction. HI introduces a subtraction task with a negative operand but does not give the inverse rule or solution.'),
  (1,'Subtracting negative three means adding positive three.',False,False,
   'Neither cited excerpt supplies the sign-change rule.'),
  (1,'Five minus negative three equals eight.',False,False,
   'Correct arithmetic, but the governing subtraction-of-a-negative rule is absent from the attached excerpts.')]
}

DIAGNOSED_RELEVANCE = {
 'DEV001': (True,'The explanation explicitly teaches a pattern as a repeatable rule, demonstrates adding three and tests the rule across neighbouring numbers.'),
 'DEV011': (False,'Diagnosed foundation is counting numbers. The response teaches parity and pairing seven objects, but assumes counting and does not explain the counting-number sequence or how to count.'),
 'DEV016': (False,'Diagnosed foundation is counting numbers. The response explains even-number pairing and divisibility, assuming rather than teaching the diagnosed counting foundation.'),
 'DEV021': (True,'Diagnosed foundation is straight angle. The first paragraph explicitly teaches a half-turn to the opposite direction and connects it to two 90-degree quarter-turns before explaining the target right angle.'),
 'DEV031': (True,'Diagnosed foundation is right angle. A rectangular-corner example explicitly identifies a right angle and its rotation invariance, followed by the obtuse-angle boundary comparison.'),
 'DEV036': (False,'Diagnosed foundation is degree as angle measure. The response only gives reflex-angle degree bounds; it does not explain degree units or their full-turn relationship.'),
 'DEV041': (False,'Diagnosed foundation is digit. The response explains place value of the digit four, but assumes the meaning of digit rather than teaching digits or distinguishing a digit from a multidigit number.'),
 'DEV051': (True,'Diagnosed foundation is comparing numbers. The explanation directly teaches the ordering rule: a number farther right on the number line is greater.'),
 'DEV056': (False,'Diagnosed foundation is mental math. The response defines estimation but provides no mental-calculation strategy or worked mental-arithmetic step.')
}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    for filename,expected in REVIEWED_INPUT_HASHES.items():
        if sha(OUT/filename)!=expected:
            raise ValueError('Answer text changed; fresh semantic review required: '+filename)
    path=OUT/'workflow_traces.json'; rows=json.loads(path.read_text(encoding='utf-8'))
    assert len(rows)==20 and len(CLAIMS)==10
    # Independent calculations use mathematical operations, not stored bank keys.
    arithmetic={
        'complete_graph_four_points': math.comb(4,2)==6,
        'mental_sum': 52+9==61 and 9==10-1,
        'frequency': [5,6,5,6,7,5,6,6].count(5)==3,
        'sixteen_factors': [i for i in range(1,17) if 16%i==0]==[1,2,4,8,16],
        'rectangle_area': 8*3==24,
        'fraction_sum': Fraction(1,5)+Fraction(1,8)==Fraction(13,40),
        'circle_radius': 10/2==5,
        'octagon_turns': 360/(360/8)==8,
        'integer_subtraction': 5-(-3)==8,
    }
    assert all(arithmetic.values())
    reviews=[]; source_hashes={}
    for row in rows:
        answer=row['answer']; sources={s['id']:s for s in answer['sources']}
        claims=[]
        for j,(pi,claim,en,hi,reason) in enumerate(CLAIMS[row['concept']],1):
            paragraph=answer['paragraphs'][pi]
            citations=[sources[c] for c in paragraph.get('citations',[])]
            assert citations
            for s in citations:
                filename=s['url'].split('#')[0].split('/')[-1]
                pdf=ROOT/'assets/textbooks'/row['language']/filename
                actual=source_hashes.setdefault(str(pdf.relative_to(ROOT)),sha(pdf))
                assert actual==s['sha256'],'Textbook changed since frozen output.'
            claims.append({'claim_id':f'{row["concept"]}-{row["language"]}-{j}',
                'canonical_claim':claim,'paragraph_index':pi,'actual_answer_paragraph':paragraph['text'],
                'mathematically_correct_ai_review':True,
                'citation_fully_supports_claim':en if row['language']=='en' else hi,
                'citation_review_reason':reason,
                'cited_excerpts':[{'id':s['id'],'url':s['url'],'excerpt':s['excerpt']} for s in citations]})
        reviews.append({'concept':row['concept'],'chapter':row['chapter'],'language':row['language'],
            'all_mathematical_claims_correct_ai_review':True,'claims':claims,
            'math_review_reason':'Definition/procedure and worked conclusion inspected for elementary mathematical correctness. Independent numeric computations recorded separately; this does not score clarity or teaching effectiveness.'})
    cycles=json.loads((OUT/'complete_chat_cycles.json').read_text(encoding='utf-8'))
    relevance=[]
    for row in cycles:
        answer=next(event for event in row['events'] if event.get('paragraphs'))
        decision=answer['learning_context']['teaching_decision']
        # Fully explaining selected degree focus requires what degrees measure,
        # not merely attaching a degree symbol to 90. Other focus-specific lessons
        # explicitly define right angle/acute angle and give the contrast/example.
        passed=row['profile']!='no_apparent_gap'
        relevance.append({'profile':row['profile'],'language':row['language'],
            'focus':decision['focus_concept_id'],'diagnosis_summary':answer['tutor_summary'],
            'paragraphs':answer['paragraphs'],'selected_focus_relevance_ai_review':passed,
            'confirmed_gap_case':row['profile']=='prerequisite_gap',
            'reason':('A complete degree-unit explanation is missing: the answer gives 90-degree/acute examples but does not define degree as an angular unit or relate it to a full turn.' if not passed else
                      'The explanation explicitly explains the selected right-angle or acute-angle focus with a definition and relevant contrast/example. This is content relevance, not proof of correct causal diagnosis.')})
    diagnosed_path=OUT/'diagnosed_answer_quality_cases.json'
    diagnosed_cases=json.loads(diagnosed_path.read_text(encoding='utf-8'))
    assert len(diagnosed_cases)==18
    diagnosed_reviews=[]
    for row in diagnosed_cases:
        passed,reason=DIAGNOSED_RELEVANCE[row['case_id']]
        assert row['answer'].get('paragraphs') and row['diagnosed_gap']
        diagnosed_reviews.append({'case_id':row['case_id'],'language':row['language'],'target':row['target'],
            'diagnosed_gap':row['diagnosed_gap'],'teaching_request':row['teaching_request'],
            'addresses_diagnosed_foundation_ai_review':passed,'reason':reason,
            'actual_paragraphs':row['answer']['paragraphs']})
    report={'review_type':'Explicit assistant AI content review; not independent teacher/human validation',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'generation_scope':'Frozen offline authored fallback answers from workflow_traces.json; no new cloud model generation',
        'rubric':{'correctness':'An answer passes only when all reviewed mathematical statements/procedures and original worked conclusions are correct. Style, completeness and educational impact are separate.',
            'claim_unit':'One definition, procedural assertion, mathematical relationship or original worked conclusion. Repeated definitions within the same answer are not counted twice.',
            'citation_support':'The actual cited retrieved excerpt must state or semantically establish the claim. A new numeric example may follow an explicitly stated source rule plus verified arithmetic. Topic overlap, a bare exercise, unseen diagrams and uncited retrieved sources do not suffice. Partial support fails the strict full-support test.',
            'unsupported_claim_rate':'Claims not fully supported by their attached retrieved excerpts / all reviewed claims. Includes incomplete support; unsupported does not mean mathematically false.',
            'diagnostic_relevance':'Primary score uses nine actual flagged-gap development cases per language, regenerated through the current offline answer path using their real teaching decision. At least one substantive accurate definition or example must teach the diagnosed prerequisite, not just the target or an assumed prerequisite symbol. Three missed-gap scenarios are excluded because no gap was diagnosed. Broader selected-focus checks from the five-profile chat cycles are separate.'},
        'by_language':{},'math_verifications':arithmetic,'answer_reviews':reviews,
        'diagnosed_foundation_relevance_reviews':diagnosed_reviews,'five_profile_focus_reviews':relevance,
        'provenance':{'workflow_traces_sha256':sha(path),'complete_cycles_sha256':sha(OUT/'complete_chat_cycles.json'),
                      'diagnosed_answer_cases_sha256':sha(diagnosed_path),
                      'textbook_hashes':source_hashes,'review_script_sha256':sha(Path(__file__))},
        'limits':['Single AI reviewer, which also worked on the application; no independent ratings or inter-rater agreement.',
                  'Only one paired answer per chapter, authored fallback generation, and known synthetic development cases.',
                  'Citation scoring covers retrieved text excerpts, not additional full-page context or visual diagrams absent from that text.',
                  'Diagnosis relevance has a much smaller and different denominator from answer correctness/citation support.']}
    for lang in ('en','hi'):
        answers=[r for r in reviews if r['language']==lang]
        claims=[c for a in answers for c in a['claims']]
        related=[r for r in relevance if r['language']==lang]
        confirmed=[r for r in diagnosed_reviews if r['language']==lang]
        supported=sum(c['citation_fully_supports_claim'] for c in claims)
        report['by_language'][lang]={
            'mathematical_answer_correctness':{'passed':sum(a['all_mathematical_claims_correct_ai_review'] for a in answers),'total':len(answers),
                                               'rate':sum(a['all_mathematical_claims_correct_ai_review'] for a in answers)/len(answers)},
            'citation_support_rate':{'supported':supported,'claims':len(claims),'rate':supported/len(claims)},
            'unsupported_or_incompletely_supported_claim_rate':{'unsupported':len(claims)-supported,'claims':len(claims),'rate':1-supported/len(claims)},
            'relevance_to_diagnosed_difficulty':{'passed':sum(r['addresses_diagnosed_foundation_ai_review'] for r in confirmed),'cases':len(confirmed),
                'rate':sum(r['addresses_diagnosed_foundation_ai_review'] for r in confirmed)/len(confirmed)},
            'selected_diagnostic_focus_relevance_all_profiles':{'passed':sum(r['selected_focus_relevance_ai_review'] for r in related),'cases':len(related),
                'rate':sum(r['selected_focus_relevance_ai_review'] for r in related)/len(related)}}
    output=OUT/'rag_answer_quality_ai_review.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    render(report)
    print(json.dumps(report['by_language'],indent=2))


def render(report):
    from html import escape
    metrics=[('Mathematical answer correctness','mathematical_answer_correctness'),
             ('Citation support rate (strict retrieved-excerpt support)','citation_support_rate'),
             ('Relevance to diagnosed prerequisite difficulty','relevance_to_diagnosed_difficulty'),
             ('Unsupported or incompletely supported claim rate','unsupported_or_incompletely_supported_claim_rate')]
    table='<table><thead><tr><th>Metric</th><th>English</th><th>Hindi</th></tr></thead><tbody>'
    for label,key in metrics:
        table+='<tr><th>'+escape(label)+'</th>'
        for lang in ('en','hi'):
            row=report['by_language'][lang][key]
            numerator=row.get('passed',row.get('supported',row.get('unsupported')))
            denominator=row.get('total',row.get('claims',row.get('cases')))
            table+=f'<td>{100*row["rate"]:.2f}% ({numerator}/{denominator})</td>'
        table+='</tr>'
    table+='</tbody></table>'
    body=''
    for row in report['answer_reviews']:
        body+=f'<details><summary>{escape(row["concept"])} / {row["language"].upper()}</summary>'
        for claim in row['claims']:
            verdict='Fully supported' if claim['citation_fully_supports_claim'] else 'Not fully supported'
            body+=f'<h3>{escape(claim["canonical_claim"])}</h3><p><strong>{verdict}.</strong> {escape(claim["citation_review_reason"])}</p><p>{escape(claim["actual_answer_paragraph"])}</p>'
            for cited in claim['cited_excerpts']:
                body+=f'<blockquote>{escape(cited["excerpt"])}</blockquote><p class="small">{escape(cited["url"])}</p>'
        body+='</details>'
    relevance=''
    for row in report['diagnosed_foundation_relevance_reviews']:
        verdict='Addresses foundation' if row['addresses_diagnosed_foundation_ai_review'] else 'Foundation not sufficiently explained'
        relevance+=f'<details><summary>{escape(row["case_id"])} / {row["language"].upper()} / {verdict}</summary><p>{escape(row["reason"])}</p>'
        for paragraph in row['actual_paragraphs']:relevance+='<p>'+escape(paragraph['text'])+'</p>'
        relevance+='</details>'
    markup='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RAG answer quality: AI review</title><style>body{font:16px/1.55 system-ui;max-width:1080px;margin:32px auto;padding:0 20px;color:#19343d}h1,h2{color:#126b61}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bdd2ce;padding:10px;text-align:left}thead{background:#eaf4f2}details{border-top:1px solid #bdd2ce;padding:12px 0}summary{cursor:pointer;font-weight:650}blockquote{border-left:4px solid #126b61;margin:12px 0;padding:8px 16px;background:#f0f6f4}.small{font-size:13px;overflow-wrap:anywhere}</style>'
    markup+='<h1>RAG answer quality: AI review</h1><p><strong>Provisional assistant review, not independent teacher validation.</strong> Offline authored fallback answers; no live-model quality claim.</p>'+table
    markup+='<h2>Sample and interpretation</h2><p>Correctness: 10 saved chapter answers per language. Citation support: 25 explicitly annotated claims per language. Diagnostic relevance: nine flagged-gap synthetic development cases per language, regenerated through the actual offline answer path. Samples overlap by concept and are not independent student observations.</p><p>Unsupported includes incomplete excerpt support; it does not mean mathematically false. Full PDF-page context, unseen diagrams and uncited passages are outside the strict citation rubric. Original examples pass when the excerpt explicitly supplies the governing rule and arithmetic verifies the result.</p>'
    markup+='<h2>Claim-by-claim citation review</h2>'+body+'<h2>Diagnosed-foundation relevance review</h2>'+relevance
    markup+='<h2>Limitations</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in report['limits'])+'</ul><p><a href="rag_answer_quality_ai_review.json">Detailed JSON, rubric and provenance hashes</a></p></html>'
    (OUT/'rag_answer_quality_ai_review.html').write_text(markup,encoding='utf-8')


if __name__=='__main__': review()
