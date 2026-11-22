"""Compile preserved evaluations into a traceable PDF; no new accuracy claims."""
import hashlib
import json
from pathlib import Path
from statistics import mean
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether, Flowable)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'output/pdf/Athena_Results_Previous_vs_Latest.pdf'
SOURCE_FILES = [
    'reports/phase2_evaluation_v2/results.json',
    'reports/graph_chunking_comparison.json',
    'reports/graph_metadata_comparison.json',
    'reports/retrieval_v3/comparison.json',
    'reports/retrieval_v4/comparison.json',
    'reports/retrieval_v5/comparison.json',
    'reports/retrieval_v6/comparison.json',
    'reports/rag_k_comparison.json',
    'reports/rag_metrics.json',
    'reports/semantic_mapping_results_v2.json',
    'reports/finetuning_v2/comparison.json',
    'reports/pilot_summary.json',
    'reports/pilot_final_v3_summary.json',
    'reports/phase2_validation.json',
    'reports/curriculum_v2/regression.json',
    'reports/curriculum_v2/browser.json',
    'reports/curriculum_v2/platform_accessibility.json',
    'reports/phase2_evaluation_v2/workflow_document_checklist.json',
    'reports/phase2_evaluation_v2/failure_examples.json',
    'reports/phase2_evaluation_v2/prerequisite_ranking.json',
    'reports/phase2_evaluation_v2/complete_chat_cycles.json',
    'reports/phase2_evaluation_v2/evaluation_manifest.json',
]
DATA = {f: json.loads((ROOT/f).read_text(encoding='utf-8')) for f in SOURCE_FILES}
L = DATA[SOURCE_FILES[0]]
TEAL = colors.HexColor('#126b61')
INK = colors.HexColor('#19343d')
MUTED = colors.HexColor('#53666d')
PALE = colors.HexColor('#eaf4f2')
GRID = colors.HexColor('#c9d9d6')
WIDTH = A4[0] - 36*mm
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleA', fontName='Helvetica-Bold', fontSize=27,
    leading=32, textColor=INK, spaceAfter=15))
styles.add(ParagraphStyle(name='HeadingA', fontName='Helvetica-Bold', fontSize=19,
    leading=24, textColor=TEAL, spaceAfter=13))
styles.add(ParagraphStyle(name='SubA', fontName='Helvetica-Bold', fontSize=11,
    leading=15, textColor=INK, spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle(name='BodyA', fontName='Helvetica', fontSize=9.4,
    leading=14, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name='SmallA', fontName='Helvetica', fontSize=8,
    leading=11, textColor=MUTED, spaceAfter=6))
styles.add(ParagraphStyle(name='CellA', fontName='Helvetica', fontSize=8.2,
    leading=11.1, textColor=INK))
styles.add(ParagraphStyle(name='HeadCellA', fontName='Helvetica-Bold', fontSize=8.2,
    leading=11.1, textColor=colors.white))
story = []
page_titles = []


def p(text, style='BodyA'):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style])


def text(value, style='BodyA'):
    story.append(p(value, style))


def title(value, subtitle=None):
    if story: story.append(PageBreak())
    page_titles.append(value)
    text(value, 'HeadingA')
    if subtitle: text(subtitle)


def table(headers, rows, widths=None, small=False):
    data = [[p(x, 'HeadCellA') for x in headers]] + [[p(x, 'SmallA' if small else 'CellA') for x in row] for row in rows]
    weights = widths or [1]*len(headers)
    t = Table(data, colWidths=[WIDTH*x/sum(weights) for x in weights], repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('LINEBELOW', (0, 0), (-1, 0), .5, TEAL),
        ('LINEBELOW', (0, 1), (-1, -1), .3, GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t); story.append(Spacer(1, 8))


def percent(value):
    return 'Not measured' if value is None else f'{100*value:.2f}%'


def delta(a, b):
    return f'{100*(b-a):+.2f} pp'


def sub(value): text(value, 'SubA')
def note(value): text(value, 'SmallA')


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID); canvas.line(18*mm, 17*mm, A4[0]-18*mm, 17*mm)
    canvas.setFillColor(MUTED); canvas.setFont('Helvetica', 8)
    canvas.drawString(18*mm, 12*mm, 'ATHENA / CONCEPT ATLAS | Evaluation record | 21 November 2026 IST')
    canvas.drawRightString(A4[0]-18*mm, 12*mm, str(doc.page))
    canvas.restoreState()


class CompareChart(Flowable):
    def __init__(self, rows):
        Flowable.__init__(self); self.width=WIDTH; self.height=118; self.rows=rows

    def draw(self):
        c=self.canv
        for i,(label,before,after) in enumerate(self.rows):
            y=91-i*48
            c.setFont('Helvetica-Bold',9);c.setFillColor(INK);c.drawString(0,y+13,label)
            for offset,value,color in [(0,before,colors.HexColor('#9db4b0')),(-14,after,TEAL)]:
                c.setFillColor(color);c.rect(118,y+offset,220*value,10,fill=1,stroke=0)
                c.setFillColor(INK);c.setFont('Helvetica',8);c.drawString(344,y+offset+1,percent(value))
        c.setFont('Helvetica',8);c.setFillColor(MUTED)
        c.drawString(0,0,'Grey: saved v5 baseline. Teal: cross-encoder. Same candidate pool and budget. [S07]')


def build():
    graph=L['graph']; diag=L['diagnosis']['by_language']['en']['graph_guided']
    v6=DATA[SOURCE_FILES[6]]; ft=DATA[SOURCE_FILES[10]]
    # 1
    text('ATHENA / CONCEPT ATLAS', 'SubA')
    text('Results and progress\nPrevious vs latest', 'TitleA')
    text('Consolidated evaluation report | 21 November 2026 | English and Hindi')
    text('This report combines the saved historical experiments with the latest ten-chapter application evaluation. It includes improvements, regressions and unmeasured results. Earlier evaluations were not rerun for this document.')
    sub('Current application and development results')
    table(['Area','Latest recorded result'],[
        ['Curriculum','10 chapters; 144 bilingual concepts, including 14 prior-knowledge concepts; 211 prerequisite links.'],
        ['Prerequisite ranking','Recall@3 99.63%; Recall@5 100.00% over 134 targets. Same graph defines reference links and candidate eligibility.'],
        ['Synthetic diagnosis','75.00% gap detection; 0.00% false-gap rate; 60.00% of cases retain some insufficient tested evidence.'],
        ['English evidence @5','Precision 66.67%; candidate-pool recall 77.26%.'],
        ['Hindi evidence @5','Precision 70.00%; candidate-pool recall 78.22%.'],
        ['Complete chat cycle','10/10 offline cycles passed: five synthetic profiles in both languages.'],
        ['Regression','162 passed, one skipped; zero failures/errors in 163 tests.'],
    ],[1.1,3.6])
    sub('Strongest saved controlled retrieval improvement')
    before=next(r for r in v6['summary'] if r['language']=='all' and r['arm']=='v5_baseline')
    after=next(r for r in v6['summary'] if r['language']=='all' and r['arm']=='cross_encoder')
    text(f'Cross-encoder reranking increased precision from {percent(before["precision"])} to {percent(after["precision"])} ({delta(before["precision"],after["precision"])}), and pool recall from {percent(before["recall"])} to {percent(after["recall"])} ({delta(before["recall"],after["recall"])}). Support-span overlap coverage decreased; that tradeoff is reported on page 7. [S07]')
    note('pp = percentage points. Synthetic agreement and automated structural checks do not establish learner accuracy, explanation quality or learning gains. Sources use stable IDs listed at the end.')
    # 2
    title('1. Latest nine-test evaluation', 'Source: latest Phase 2 development evaluation [S01].')
    table(['Test','Measured result','Interpretation / remaining work'],[
        ['1. Concept graph','144 bilingual concepts; 211 links; acyclic; zero duplicate/self links.','User confirmed reviewed positive links. Negative-pair labels needed for unconditional prerequisite precision/F1.'],
        ['2. Prerequisite retrieval','Recall@3 99.63%; Recall@5 100.00%.','Macro direct-link retrieval over 134 targets; tests rank and bank coverage.'],
        ['3. Question selection','2.77 questions on average; maximum 3.','60 paired synthetic scenarios; same bank, target and response budget across three methods.'],
        ['4. Diagnosis','Gap detection 75.00%; false-gap 0.00%; some evidence unresolved 60.00%.','Development oracle profiles, not independently reviewed learner accuracy.'],
        ['5. Evidence retrieval','English @5 P/R: 66.67% / 77.26%. Hindi @5: 70.00% / 78.22%.','12 known queries. Recall denominator is the scoped chunk pool. Semantic support-span ratings pending.'],
        ['6. Explanation quality','20 offline answers: limited math checks and citation-ID integrity 100%.','Mathematical correctness, citation entailment and difficulty alignment are unscored. Live provider request failed.'],
        ['7. Bilingual consistency','144 definitions and 432 question pairs passed number/unit checks; canonical labels match.','Translation accuracy and semantic terminology suitability require blind review.'],
        ['8. Feedback/follow-up','8 feedback-mode cases answered; 8 rotated-question assertions passed.','Execution/scoring verified; pedagogically appropriate next-action rate is unmeasured.'],
        ['9. End-to-end','10/10 persisted offline chat cycles passed; 20/20 chapter/language answer smoke cases passed.','Includes inline grading, separate saved follow-up evidence and a fresh question; no real-learner study.'],
    ],[1.1,1.8,2.2])
    sub('What counts as an improvement')
    text('A controlled difference holds the case set, reference labels, candidate pool, metric definition and context budget fixed. A historical-to-current difference with changed graph, corpus or denominator is a descriptive change. This report separates the two and does not force every later score to be higher.')
    # 3
    title('2. Curriculum and concept-graph results')
    table(['Component','Previous','Latest','Meaning'],[
        ['Application chapter scope','3 core chapters','10 chapters','Expanded coverage, not an accuracy gain.'],
        ['Graph concepts','53 in original workbook','144','130 chapter concepts + 14 prior concepts.'],
        ['Prerequisite links','307 original proposed links','211 reviewed-file links','Different node set and link policy; fewer links is not a recall loss by itself.'],
        ['Core diagnostic items','30 original bank items','432 current bank items','Original keys retained; v1 tutor/scenario banks may contain extra items. New items await review.'],
    ],[1.3,1.2,1.2,2])
    table(['Chapter','Count','Chapter','Count'],[
        ['1. Patterns in Mathematics',19,'6. Perimeter and Area',15],
        ['2. Lines and Angles',20,'7. Fractions',14],
        ['3. Number Play',11,'8. Playing with Constructions',9],
        ['4. Data Handling and Presentation',10,'9. Symmetry',6],
        ['5. Prime Time',15,'10. The Other Side of Zero',11],
    ],[2.4,.6,2.4,.6])
    sub('Original graph versus the reviewed positive reference')
    g=graph['original_graph_comparison']
    text(f'Comparison uses {g["compatible_concepts"]} semantically compatible shared concept IDs. There are {g["original_predicted_links"]} original predicted links and {g["reviewed_positive_links"]} reviewed positive links in this restricted scope: {g["true_positive"]} overlaps, {g["missed_reviewed_links"]} reviewed links missed, and {g["unmatched_original_links"]} unmatched original links. [S01]')
    table(['Metric','Result','Qualification'],[
        ['Positive-link recall',percent(g['positive_link_recall']),'Original graph coverage of reviewed positives.'],
        ['Conditional precision',percent(g['conditional_precision']),'Assumes every absent reviewed-file link is negative.'],
        ['Conditional F1',percent(g['conditional_f1']),'Same unverified negative assumption; not independently validated precision/F1.'],
    ],[1.5,.8,3])
    note('Shared IDs MATH6_C0036 and MATH6_C0049 were excluded because their meanings changed. Direct-link versus transitive-link redundancy can affect agreement. The user attested that v2 is reviewed; its 211 PENDING_HUMAN_REVIEW CSV flags were preserved, not silently rewritten. [S01]')
    sub('Earlier prerequisite retrieval cited in the workflow')
    text('The workflow quotes earlier prerequisite Recall@3 of 77.14% and Recall@5 of 92.86%. Latest direct-link scores are 99.63% and 100.00%, nominal changes of +22.49 pp and +7.14 pp. The original evaluation population/importance labels are not a matched current benchmark, so these are historical-to-current score differences, not controlled accuracy gains. [S23, S01]')
    # 4
    title('3. Diagnosis and question selection', '60 new development scenarios across the original three chapters; 120 language variants and 360 method-language runs. No independent learner labels supplied. [S01]')
    rows=[]
    for lang,methods in L['diagnosis']['by_language'].items():
        for method,r in methods.items():
            rows.append([lang.upper(),method.replace('_',' '),percent(r['gap_detection_rate']),percent(r['false_gap_rate']),percent(r['unresolved_rate']),f'{r["average_questions"]:.2f}'])
    table(['Lang.','Selection method','Gap detection','False gap','Some evidence unresolved','Avg. Q'],rows,[.55,1.65,1,1,1.15,.65])
    text('Identical English/Hindi diagnosis scores are expected here: the response oracle uses equivalent answer keys. They do not show that language understanding or translations are equally accurate. Fixed and non-graph adaptive arms are simple target-first heuristics, not tuned state-of-the-art baselines.')
    sub('Graph-guided results by synthetic profile (same in both languages)')
    rows=[]
    for profile,r in diag['profile_breakdown'].items():
        rows.append([profile.replace('_',' '),percent(r['exact_gap_set_agreement']),percent(r['unresolved_rate'])])
    table(['Profile (12 cases each)','Exact predicted gap-set agreement','Some evidence unresolved'],rows,[2.1,1.6,1.6])
    note('Exact gap-set agreement is 95% overall. Non-gap cases count an empty predicted gap set as an agreement even when evidence is insufficient. Thus this figure must not be presented as 95% full diagnostic accuracy.')
    sub('Failure analysis and budget')
    failures=DATA[SOURCE_FILES[18]]['missed_synthetic_gaps']
    text('Three of the 12 simulated prerequisite gaps were missed. With multiple incoming prerequisites, the three-question cap may allow confirmation of only the first foundation and one observation on another. Mixed or unscorable answers remain insufficient rather than becoming a weakness label. Missed cases: '+', '.join(r['case_id']+' ('+r['target']+')' for r in failures)+'.')
    note('All arms saw only answers to items they actually asked, with no prior learner evidence and no repeated item IDs. Synthetic gap placement rotates across prerequisite ranks; final-candidate cases remain untouched. [S01]')
    # 5
    title('4. Latest evidence retrieval by k', 'Same 12 known development queries: six English and six Hindi. These query topics do not constitute a ten-chapter retrieval-quality benchmark. [S01]')
    rows=[]
    for lang,ks in L['retrieval']['by_language'].items():
        for k,r in ks.items(): rows.append([lang.upper(),k,percent(r['precision']),percent(r['recall']),percent(r['support_span_coverage_proxy'])])
    table(['Language','k','Precision@k','Pool recall@k','Lexical coverage proxy'],rows,[1,.5,1.3,1.4,1.8])
    sub('How to read the scores')
    text('Precision@k divides relevant retrieved chunks by k, including missing output slots as non-relevant. Relevance is a fixed page-and-substring proxy. Recall divides retrieved relevant chunks by all relevant chunks in that query\'s concept-scoped candidate pool; it does not measure recall over every NCERT passage.')
    text('Recall is defined for five cases per language. R09 (English place value) and R10 (Hindi place value) have no relevant chunk under the frozen reference criteria. They are reported as zero-evidence cases, not perfect-recall successes, and contribute to precision. Unsupported-source abstention is appropriate.')
    text('The lexical coverage proxy counts reference-term occurrences in page-matching chunks. Earlier overlap-adjusted support-span coverage measures text intervals instead. Neither is independent human evidence-entailment coverage, and the two metrics must not be subtracted.')
    sub('Within the latest run: increasing k from 2 to 5')
    rows=[]
    for lang in ('en','hi'):
        a=L['retrieval']['by_language'][lang]['2'];b=L['retrieval']['by_language'][lang]['5']
        rows.append([lang.upper(),delta(a['precision'],b['precision']),delta(a['recall'],b['recall'])])
    table(['Language','Precision change','Recall change'],rows,[1,2,2])
    text('Returning more chunks improves candidate-pool recall but lowers precision. The above is a valid within-run k tradeoff because the candidate pool and labels are fixed. It is not evidence that longer explanations teach students better.')
    # 6
    title('5. Historical retrieval experiments', 'Archived results are retained even where performance decreased. All listed tests used a small known development query set; human relevance review was pending.')
    chunk=DATA[SOURCE_FILES[1]];meta=DATA[SOURCE_FILES[2]];v3=DATA[SOURCE_FILES[3]];v4=DATA[SOURCE_FILES[4]];v5=DATA[SOURCE_FILES[5]]
    versions=[('Adjacent-sentence baseline',chunk['results']['previous']['metrics'],'S02'),
        ('Graph chunking',chunk['results']['graph']['metrics'],'S02'),
        ('Graph + metadata',meta['results']['graph_metadata']['metrics'],'S03'),
        ('v3 contextual retrieval',v3['results']['candidate']['metrics'],'S04'),
        ('v4 hybrid retrieval',v4['results']['hybrid']['metrics'],'S05')]
    table(['Recorded variant','P@2','Pool R@2','Hit@1','MRR@2','Source'],[[name,percent(r['precision_at_2']),percent(r['recall_at_2']),percent(r['hit_at_1']),f'{r["mrr_at_2"]:.3f}',sid] for name,r,sid in versions],[2.3,1,1.1,1,.8,.6])
    text('Graph chunking alone did not improve the original baseline: overall P@2 fell from 45.83% to 41.67% (-4.17 pp); pool R@2 fell from 75.71% to 60.71%. Chunk boundaries change the relevant-chunk denominator, so the recall difference is a recorded score change rather than a fair fact-recall improvement. Metadata recovered ranking in some cases without recovering top-two precision. [S02, S03]')
    table(['Language','Adjacent P@2','Graph P@2','Metadata P@2','Metadata Hit@1'],[
        [lang.upper(),percent(chunk['results']['previous']['by_language'][lang]['precision_at_2']),percent(chunk['results']['graph']['by_language'][lang]['precision_at_2']),percent(meta['results']['graph_metadata']['by_language'][lang]['precision_at_2']),percent(meta['results']['graph_metadata']['by_language'][lang]['hit_at_1'])] for lang in ('en','hi')],[1,1.2,1.1,1.3,1.4])
    sub('Historical generation and mapping')
    rag=DATA[SOURCE_FILES[8]];mapping=DATA[SOURCE_FILES[9]]
    text('The older RAG evaluation recorded P@2 41.67%, R@2 74.29%, 14/14 personalization policy checks passing and two generation cases with 100% fallback. It is a separate saved run from the 45.83% adjacent-sentence comparison; those values are not interchangeable baselines. [S09]')
    table(['Mapping method','Expectation matches / 24','False mappings'],[
        ['Legacy lexical',mapping['summary']['legacy']['expectation_matches'],mapping['summary']['legacy']['false_mappings']],
        ['Semantic v2',mapping['summary']['semantic-v2']['expectation_matches'],mapping['summary']['semantic-v2']['false_mappings']],
    ],[2.5,1.7,1])
    note('Mapping expectation agreement increased from 54.17% to 75.00% (+20.83 pp) on that saved 24-case experiment. This is historical development evidence; current 144-concept mapping accuracy was not rerun on an independent benchmark. [S10]')
    # 7
    title('6. Controlled retrieval improvements', 'The saved v6 comparison reuses the same v5 candidate pool, queries, labels, up-to-three-passage policy and 1,300-character ceiling. [S07]')
    story.append(CompareChart([('Precision',before['precision'],after['precision']),('Pool recall',before['recall'],after['recall'])]));story.append(Spacer(1,8))
    rows=[]
    for lang in ('all','en','hi'):
        a=next(r for r in v6['summary'] if r['language']==lang and r['arm']=='v5_baseline')
        b=next(r for r in v6['summary'] if r['language']==lang and r['arm']=='cross_encoder')
        for metric,label in [('precision','Precision'),('recall','Pool recall'),('support_span_coverage','Span overlap coverage')]:
            rows.append([lang.upper(),label,percent(a[metric]),percent(b[metric]),delta(a[metric],b[metric])])
    table(['Lang.','Metric','Before','After','Change'],rows,[.7,1.9,1.1,1.1,1.2])
    text('The cross-encoder improved precision and recall, while overlap-adjusted support-span coverage decreased by 6.27 pp overall. Redundant text fraction rose from 28.68% to 46.46% (+17.78 pp). Hit rate stayed at 83.33%. Better ranking scores therefore came with a context-diversity tradeoff. These are not new latest-v2 learner results.')
    sub('Other saved controlled changes')
    rows=[]
    a=v4['results']['v3_baseline']['metrics'];b=v4['results']['hybrid']['metrics']
    rows.append(['v3 to v4 hybrid','P@2',percent(a['precision_at_2']),percent(b['precision_at_2']),delta(a['precision_at_2'],b['precision_at_2'])])
    rows.append(['v3 to v4 hybrid','Pool R@2',percent(a['recall_at_2']),percent(b['recall_at_2']),delta(a['recall_at_2'],b['recall_at_2'])])
    a=next(r for r in v5['policy_summary'] if r['language']=='all' and r['policy']=='v4_fixed_two')
    b=next(r for r in v5['policy_summary'] if r['language']=='all' and r['policy']=='bounded_three')
    rows.append(['Two to bounded three','Pool recall',percent(a['recall']),percent(b['recall']),delta(a['recall'],b['recall'])])
    table(['Experiment','Metric','Before','After','Change'],rows,[1.8,1.1,1,1,1.1])
    note('Bounded-three increases the passage budget, so it is a policy/budget tradeoff rather than a same-budget ranking improvement. Historical retrieval code/controls and source hashes are retained in the source files. [S05, S06]')
    # 8
    title('7. Previous versus latest k results', 'Earlier sweep: 2 November 2026, semantic-page-v1. Latest: 21 November 2026, v2 catalog/application. Same known query IDs, but catalog, chunks and relevant-pool denominators changed. [S08, S01]')
    old=DATA[SOURCE_FILES[7]]
    rows=[]
    for lang in ('en','hi'):
        for k in (1,2,3,5):
            a=next(r for r in old['summary'] if r['language']==lang and r['k']==k)
            b=L['retrieval']['by_language'][lang][str(k)]
            rows.append([lang.upper(),k,percent(a['precision']),percent(b['precision']),delta(a['precision'],b['precision']),percent(a['recall']),percent(b['recall'])])
    table(['Lang.','k','Earlier P','Latest P','P change','Earlier R','Latest R'],rows,[.65,.4,1,1,1,1,1])
    text('Precision changes above are descriptive observed differences on the same query set and k, not an isolated causal effect of one feature. Recall columns are shown side by side without an improvement delta because the relevant-pool denominator changed. Earlier recall was defined for five English and four Hindi cases; the latest run has five in each language.')
    sub('Latest k=5 compared with the earlier sweep')
    text('English precision increased from 30.00% to 66.67% (+36.67 pp). Hindi precision increased from 16.67% to 70.00% (+53.33 pp). English recorded pool recall is lower (94.29% versus 77.26%); Hindi is higher (26.79% versus 78.22%). Neither recall change is a controlled improvement claim.')
    sub('Earlier k=10, retained for completeness')
    rows=[]
    for lang in ('all','en','hi'):
        a=next(r for r in old['summary'] if r['language']==lang and r['k']==10)
        rows.append([lang.upper(),percent(a['precision']),percent(a['recall']),a['recall_defined_cases']])
    table(['Language','Earlier precision@10','Earlier pool recall@10','Recall-defined cases'],rows,[1,1.6,1.6,1.4])
    note('Latest k=10 was not evaluated. Earlier 100% pool recall at k=10 means all relevant chunks in that earlier scoped pool were retrieved, not that all NCERT evidence was found.')
    # 9
    title('8. LoRA, QLoRA and full fine-tuning', 'Historical generator-only experiment: Qwen/Qwen3-0.6B, nine model-evaluation prompts (four English, five Hindi), identical prompt hashes across methods. Not retrained for the latest ten-chapter curriculum. [S11]')
    table(['Method','Valid JSON','Source-checked','Canonical term','Mean latency (s)'],[
        [r['method'].upper(),percent(r['json_valid']),percent(r['source_checked']),percent(r['terminology_present']),f'{r["mean_latency_seconds"]:.2f}'] for r in ft['rows']],[1.2,1.1,1.2,1.2,1.3])
    sub('English and Hindi separately')
    rows=[]
    for lang in ('en','hi'):
        for r in ft['rows']:
            a=r['by_language'][lang]
            rows.append([lang.upper(),r['method'].upper(),a['cases'],percent(a['json_valid']),percent(a['source_checked']),percent(a['terminology_present'])])
    table(['Lang.','Method','n','Valid JSON','Source-checked','Canonical term'],rows,[.7,1,.4,1.3,1.4,1.4])
    sub('Training cost and capacity')
    table(['Method','Trainable weights','Train time (s)','Peak GiB','Checkpoint MiB','Val. loss'],[
        [r['method'].upper(),f'{r["trainable_percent"]:.2f}%',f'{r["train_seconds"]:.2f}',f'{r["peak_allocated_gib"]:.2f}',f'{r["checkpoint_bytes"]/1024**2:.2f}',f'{r["validation_loss"]:.4f}'] for r in ft['rows'] if r['method']!='baseline'],[1,1.3,1.1,1,1.3,1])
    text('Shared training settings: one epoch, seed 42, learning rate 0.0001, 768-token sequence cap, micro-batch 1, gradient accumulation 4 and AdamW8bit. LoRA rank 8, alpha 16, dropout 0.05. Training set: 72 paired-language examples (36 English, 36 Hindi), four validation examples. QLoRA trained with NF4 and was evaluated on a BF16 base plus adapter, controlling inference precision.')
    note('QLoRA source-checked rate exceeds full FT by 44.44 pp and LoRA by 22.22 pp on nine prompts. Single seed, tiny synthetic sample and no human ratings prevent general-superiority claims. Source-checked is structural validation, not human correctness. Removing a single Markdown fence post hoc raises baseline JSON validity from 0/9 to 4/9; source-checked remains 0/9. Other methods are unchanged. Primary strict results remain above. Baseline validation loss: 0.9014. Latency excludes retrieval/diagnosis; peak GiB is allocated tensor memory, not total GPU residency.')
    # 10
    title('9. Explanation, bilingual and feedback results')
    table(['Measure','Earlier record','Latest record','Can claim improvement?'],[
        ['Generated versus fallback','2 generation cases; 0% generated, 100% fallback [S09]','20 offline authored fallback answers [S01]','No: different generator and sample; live provider failed.'],
        ['Citation-ID integrity','100% on 2 cases [S09]','100% on 20 cases [S01]','Maintained structural validity with wider coverage; not entailment.'],
        ['Math correctness / alignment','Human ratings unavailable','Human ratings unavailable','No measured quality delta.'],
        ['Bilingual checks','No directly comparable denominator retained here','144 definitions + 432 question pairs passed numeric/unit parity; labels match','Coverage expansion; translation accuracy remains unmeasured.'],
        ['Feedback actions','Earlier tutoring regression artifacts retained','4 actions x 2 languages answered; 8 transfer assertions passed','Functional verification, not pedagogical effectiveness.'],
    ],[1.3,1.7,1.8,1.8])
    sub('Five complete demonstration profiles')
    table(['Profile','English cycle','Hindi cycle','What the trace demonstrates'],[
        ['Prerequisite gap','Passed','Passed','Repeated wrong checks, source-guided teaching and follow-up.'],
        ['No apparent gap','Passed','Passed','Correct checks; does not claim mastery of untested concepts.'],
        ['Calculation slip','Passed','Passed','Mixed answers remain insufficient rather than a confirmed gap.'],
        ['Language confusion','Passed','Passed','Unscorable wording request does not itself prove weakness.'],
        ['Insufficient evidence','Passed','Passed','Budget respected; unsupported weakness labels avoided.'],
    ],[1.5,.8,.8,2.9])
    text('Each cycle uses the persisted chat send path: initial check, explanation, inline practice grading, separate saved follow-up evidence and a fresh question after feedback. The inline answer does not become another user-chat bubble. Diagnostic scores remain untouched; another learner cannot read the synthetic learner\'s follow-up evidence. [S21]')
    note('A successful demonstration tests execution. It does not confirm that the author-assumed slip or language cause was correctly inferred, or that the explanation helped a real student. Blind bilingual review files are available beside the latest JSON report. [S01]')
    # 11
    title('10. Workflow timing and application checks')
    rows=[]
    for lang in ('en','hi'):
        a=L['workflow']['by_language'][lang];b=L['workflow']['complete_chat_cycles']['by_language'][lang]
        rows.extend([[lang.upper(),'Ten-chapter first-pass answer',a['cases'],f'{a["median_seconds"]:.2f}',f'{a["p95_seconds"]:.2f}'],
            [lang.upper(),'Complete cached-angle chat cycle',b['cases'],f'{b["median_cycle_seconds"]:.2f}',f'{b["p95_cycle_seconds"]:.2f}']])
    table(['Lang.','Measured path','n','Median (s)','p95 (s)'],rows,[.7,2.6,.4,1.1,1.1])
    text('These are local offline timings, not cloud-model latency or an isolated production benchmark. First-pass answer runs shared CPU with other evaluations; complete cycles reuse popular angle caches. For five cycles, reported p95 is the maximum sample. The very different timing scopes should not be averaged together or described as a speed improvement.')
    sub('Regression and accessible UI')
    oldreg=DATA[SOURCE_FILES[13]];newreg=DATA[SOURCE_FILES[14]]
    table(['Check','Earlier','Latest','Interpretation'],[
        ['Regression tests run',oldreg['tests_run'],newreg['tests_run'],'More test coverage; not an accuracy percentage.'],
        ['Passed / skipped',f'{oldreg["tests_run"]-oldreg["skipped"]} / {oldreg["skipped"]}',f'{newreg["tests_run"]-newreg["skipped"]} / {newreg["skipped"]}','Zero failures and errors in both runs.'],
        ['Ten-chapter browser checks','Not the same scope','8 checks; no browser errors','Dashboard, practice, revision, exams and Hindi/mobile graph exercised.'],
        ['Accessibility screen checks','Earlier scopes differ','21 screens; 0 serious/critical violations','Automated axe checks do not certify complete accessibility.'],
    ],[1.6,1,1.7,2])
    sub('Earlier diagnosis pilots, shown without a latest delta')
    a=DATA[SOURCE_FILES[11]];b=DATA[SOURCE_FILES[12]]
    table(['Saved 20-case pilot','Method','Correct diagnosis count','Case unresolved','Avg. questions'],[
        [label,method,r['correct_diagnoses'],r['case_unresolved'],f'{r["questions_asked"]/d["case_count"]:.2f}']
        for label,d in [('Original pilot',a),('Revised v3 pilot',b)] for method,r in d['results'].items()],[1.2,1.2,1.2,1.2,1.1])
    note('These older counts use concept-level diagnosis agreements and different case packs, not the latest 60-scenario gap-detection denominator. A percentage-point improvement versus latest 75% gap detection would be invalid. Old pilot reports remain synthetic development evidence. [S12, S13]')
    note('Excluded invalid results: pilot_final_v2 has corrupted Hindi text replaced with question marks. Its own invalidation notice says not to use its metrics; the corrected v3 record is used above. [S24]')
    # 12
    title('11. Workflow-document coverage and limits', 'All 30 non-empty paragraphs of Phase 2 Workflow.docx were audited. Headings and greeting are included in the source checklist; substantive requirements are consolidated below. [S18]')
    table(['Workflow requirement','Status and evidence'],[
        ['Original / reviewed graph','Original workbook/results retained; user-attested v2 positives used; graph overlap, rank misses and hashes saved. Independent negative labels still needed.'],
        ['Reviewed bilingual item bank','432 keyed items with bilingual feedback and concept IDs. New item suitability and wrong-answer interpretations require teacher review.'],
        ['Adaptive diagnostic workflow','Three selection methods, response-only access, max three questions, logs and conservative evidence status tested.'],
        ['Target + weak-prerequisite sources','Actual local NCERT retrieval and source metadata exercised. Semantic suitability/entailment ratings pending.'],
        ['Shared-ID bilingual glossary','144 terms/definitions checked structurally; semantic review pending.'],
        ['Feedback + new transfer','Four actions and rotated angle scoring checked. Ten complete offline cycles saved, with new-question and ownership checks.'],
        ['50-80 reviewed learner scenarios','60 distinct paired development drafts authored with five profiles, reasons and textbook locations; 0 independently reviewed learner scenarios supplied.'],
        ['Family-separated final test','Original final candidates untouched. New pack is development only; no reviewed frozen final accuracy claim.'],
        ['Fair diagnosis comparison','Executed with simple heuristics and graph-derived synthetic labels; limits documented.'],
        ['Fair explanation comparison','Three offline authored-generator contexts saved under a 2,400-character ceiling. Live-model comparison and blind ratings pending.'],
        ['Five complete demonstrations','All five synthetic profiles run in both languages through inline grading and a fresh follow-up.'],
        ['Team setup / paper / learning gains','Application/setup instructions available; independent teammate setup and paper draft not completed by automated testing. No learner-learning gains claimed.'],
    ],[1.6,4.2])
    sub('Priority work before a final accuracy claim')
    text('Review and freeze scenario labels, bank items and glossary; label non-prerequisite pairs; rate blinded explanations for correctness, support and difficulty; restore the configured generation service; then run the frozen final evaluation once with unchanged settings. Address the three missed synthetic gaps without tuning against final cases.')
    note('The document originally limits evaluation to three chapters; the later explicit user request expanded the deployed application to ten. The diagnosis comparison retains three-chapter scope while integration tests cover all ten. Existing LoRA/QLoRA/full-FT experiments remain historical generator-only results.')
    # 13
    title('12. Source index and reproducibility', 'All paths are relative to E:/Capstone. Values were read from the saved JSON artifacts, not reconstructed from conversational claims. Sources have not been overwritten.')
    rows=[]
    for i,f in enumerate(SOURCE_FILES,1):
        sha=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()[:12]
        # Break filename tokens in the rendered paragraph to keep paths readable.
        rows.append([f'S{i:02}',f,sha])
    workflow_path=Path(r'C:\Users\Namrata Dalvi\Downloads\Phase 2 Workflow.docx')
    rows.append(['S23','User-supplied Phase 2 Workflow.docx (Downloads)',hashlib.sha256(workflow_path.read_bytes()).hexdigest()[:12]])
    invalid_path=ROOT/'reports/pilot_final_v2_INVALID.md'
    rows.append(['S24','reports/pilot_final_v2_INVALID.md',hashlib.sha256(invalid_path.read_bytes()).hexdigest()[:12]])
    table(['ID','Saved result artifact','SHA-256 prefix'],rows,[.5,4.6,1.2],small=True)
    note('Report generation: .\\venv\\Scripts\\python.exe scripts\\build_results_pdf.py. Latest evaluation reproduction: .\\venv\\Scripts\\python.exe scripts\\evaluate_phase2_v2.py. A new evaluation can differ in latency; old model-generation results are preserved historical runs.')
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,
        topMargin=18*mm,bottomMargin=23*mm,title='Athena Results: Previous versus Latest',
        author='Concept Atlas project',subject='Historical and current bilingual RAG evaluation with qualified improvement comparisons')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(str(OUTPUT))


if __name__=='__main__': build()
