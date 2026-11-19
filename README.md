# Concept Atlas

The learner interface is React. Build and run locally:

```powershell
npm install
python -m pip install -r requirements.txt
npm run build
python server.py
```

Open http://127.0.0.1:8000. For frontend development, run `python server.py`
and `npm run dev` in separate terminals; Vite proxies API requests to port 8000.

The public landing page has an animated 3D orbital sculpture that follows the device’s reduced-motion setting. Students can sign in
with a provisioned username and password or choose **Create account**. The account
keeps textbook chat, topic practice, and progress available across browsers on
the same server. **My space** recommends what to review using recent practice and
mapped topics from the student's own earlier report. **My progress** lists saved
practice results by topic and language.

**Revision** brings scored mistakes from practice and mock exams into a notebook.
Each entry includes the original response, a worked solution and a different question
on the same concept. The daily plan shows up to five due entries at a time. Correct
reviews are followed by reviews after one day and three days. A third correct review
completes an entry. A topic is marked understood when all its entries are complete.
An incorrect retry returns the entry to the due list.

**Mock exams** offers an 8-minute chapter paper or a 12-minute mixed paper in
English or Hindi. Use **Save & next** or the question navigation to save answers.
An unfinished paper can be resumed on the same account while its timer keeps
running. The server closes the paper at its deadline and grades the saved answers.
Fullscreen is available while taking the paper and viewing the solutions.

To provision newly imported students, export a fresh private CSV:

```powershell
python -m scripts.provision_students tmp/student-logins.csv
```

The command creates credentials only for students who lack an account. It refuses
to overwrite an existing export. Use `--resume` with the same path if provisioning
is interrupted. Keep the CSV private and give each student only their own row.
The SQLite database stores password hashes and session token hashes.

Question bank and pilot materials are developer files and are not learner navigation
screens. A 13-page bilingual diagnostic review pack is available at
`output/pdf/Concept_Atlas_Diagnostic_Review.pdf`. Individual learner results can be
printed or saved through the browser's **Save report as PDF** button.

The 3D renderer is bundled with the React build; no renderer CDN is required after
installation. WebGL is needed for the canvas. Python's standard library serves the
local API, so Streamlit is not required for the React app. The old Streamlit source
is retained for reference only.

## Diagnostic workflow (Steps 7–11)

### Bilingual textbook chat

The chat also detects Hinglish (Romanized Hindi with English maths terms). A
query such as `mujhe number pattern nahi samjhta theek se` switches the response
style to Hinglish. The chat selector offers English, Hindi, and Hinglish; subsequent
answers retain the active style. Bank questions use local Romanized renderings with
unchanged numbers/options/keys; generated explanations are prompted in Hinglish
using English textbook excerpts. Source quotations retain their original language.
Response style is request-scoped to avoid mixing languages across learners.

Normal concept explanations require at least three teaching sections, with headings,
a worked example, a comparison/common mistake and a complete practice question where
the source permits. Explicit requests for a brief answer can return a concise definition.
Citation checks remain mandatory. A nonempty answer that fails validation is revised
once; the app still falls back to labelled excerpts if the revised answer fails.

### Tutoring checks and practice inside chat

New topic queries first pass through a Gemini intent planner (`diagnostic/chat_router.py`).
Its structured decision is one of `check`, `explain`, `practice`, or `clarify`, with
a validated concept ID. The planner prompt covers confusion expressed in natural
language, explicit requests to explain without testing, connected angle comparisons,
follow-up context, and unsupported/ambiguous topics. It cannot issue tools, SQL,
scores, answer keys or diagnoses. Unknown IDs, invalid actions, low-confidence plans
and genuine chapter/scope ambiguity are guarded locally. API failures fall back to
the deterministic router and are marked `local_fallback` in saved response metadata.

Broad pattern requests use a stated number-pattern context, with an invitation to
switch to shapes, instead of requiring a chapter choice. Difficulty-led tutoring
checks incoming graph prerequisites before giving the explanation. The chat-only
bank (`diagnostic/tutor_bank.py`) adds eight original numeric probes for number,
digit, consecutive number and number line. These have exact keys but human review
is pending; they are not actual NCERT questions and do not change the diagnostic bank.
When bank-covered prerequisites exist, the three-question check stays on those
prerequisites; otherwise the target is a fallback. Two concordant observations can
support a tentative status for a checked foundation. Mixed evidence is insufficient,
and untested concepts, including the target, remain unassessed. This is a tutoring
selection policy, not a change to the separately evaluated diagnostic algorithm.
Explanation prompts require actual sequence values and self-contained practice;
references to unseen figures or unspecified sequences are disallowed by instruction.

The planner receives only the current query and public concept names/IDs (plus a
previous topic ID for follow-ups), never saved responses, scores, names, imported
gaps or evidence summaries. Pending check/practice answers are scored locally;
the planner is bypassed for these answers and **Explain now**. Both planning and
explanation use the configured Gemini model; the extra planning call adds latency.

Questions expressing difficulty or asking for practice start a short tutoring check
when the mapped topic has bank-covered foundations. Up to three existing bank items
are selected using graph-guided selection and available saved evidence. Answers are
scored locally with exact keys; the learner can choose **Explain now** or **I'm not
sure**. The explanation follows the check, with a local evidence summary and then an
original parameterised practice variation. Possible difficulty in a checked concept
prioritises that concept's practice. New practice is clearly distinguished from an
actual NCERT exercise and is not new diagnostic evidence. Questions/rules still await
human review; three answers cannot assess every prerequisite.

Chat tutoring state and answers persist separately in `book_chat_tutoring`,
`book_chat_check_answers`, and `book_chat_practice`; they do not modify diagnostic
sessions, report scores or the Previous checks dashboard. Learner isolation and
Clear all apply to these records. Existing diagnostic history can be read to avoid
repeating recent items. Learner answers and summaries stay local; Gemini receives
the original topic question and selected textbook passages, not the answers or scores.
Practice variations are generated from arithmetic/geometry templates with exact keys,
not unconstrained LLM-generated diagnostic questions.

**Ask my book** accepts English/Hindi questions and has an answer-language selector,
canonical bilingual terms, clickable PDF page citations, supporting excerpts, and
saved conversations scoped to the learner code. Clear all also removes that learner's
chats. Learner codes are identifiers, not secure account authentication.

Generation defaults to Gemini `gemini-3.5-flash-lite`, called only from Python.
Copy `.env.example` to `.env` if you do not already have a `.env`, then add your key:

```dotenv
ATLAS_CHAT_PROVIDER=gemini
ATLAS_CHAT_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your_key_here
```

Alternatively set these variables in the server's process environment. Process values
override `.env`; the simple file loader supports KEY=value and quoted values, without
variable expansion. Restart `python server.py` after setup. `.env` files are ignored
by Git; never put secrets in `VITE_` variables, frontend code, URLs or screenshots.
No extra Gemini SDK is needed: the server uses Google's REST generateContent API.

Gemini receives the current question, selected textbook excerpts, concept IDs and
bilingual terminology. Saved learner history, imported reports, scores, identifiers
and evidence summaries are not included in cloud requests. Learner evidence still
guides prerequisite/source selection locally and appears in the local context panel.
Only the optional local Ollama provider receives evidence summaries. To use it, set
`ATLAS_CHAT_PROVIDER=ollama` and `ATLAS_CHAT_MODEL=qwen2.5:0.5b` (or an installed model).
There is no automatic provider/model switch. Missing keys, quota/permission errors,
blocked responses and source-check failures produce labelled textbook excerpts.
`GET /api/chat/status` returns provider/model/configuration status, never the key;
configured status is not proof of valid credentials or model access.

Implementation references: [Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[generateContent](https://ai.google.dev/api/generate-content).

Retrieval uses catalogued, hash-checked uploaded textbook pages in the selected
language. Sentences form a weighted graph with multilingual cosine-similarity edges at
.48 or above. Contiguous communities merge by strongest mean cross-community
edge weight (missing edges count as zero), including links between non-adjacent
sentences. Chunks preserve reading order and page boundaries, with a 650-character
safety ceiling. The active chunker version is `graph-metadata-page-v2`.
Retrieval combines evidence cosine (75%), metadata-context cosine (15%), and
language-specific concept-term coverage (10%). Context includes chapter, section,
concept labels and language; evidence excerpts remain exact. Sources retain stable
chunk IDs, chunk index/count and character offsets in the normalized page text.
Run `python -m diagnostic.evaluate_chunking` for a three-way development comparison.
Query-to-chunk cosine similarity retrieves up to two target chunks and one chunk
for each of at most two direct prerequisites. Page embeddings are cached in memory.
This searches catalogued concept pages, not every page of every chapter. The chunk
threshold is a development heuristic, not an educationally validated setting.
If embeddings are unavailable, responses explicitly record a page-excerpt fallback.

Prerequisites are ordered by possible difficulty in saved checks, then mapped
earlier-report revision signals, bank coverage (concrete assessed foundations before
broad chapter nodes), graph confidence, and concept ID. Foundation retrieval uses its
own concept query so target wording cannot dominate the foundation's evidence. Evidence uses
the latest three distinct question items per relevant concept in the current bank
version; two or more uniformly correct/incorrect answers use the existing conservative
status rules, mixed/limited answers remain insufficient. Unassessed concepts are never
called weaknesses. Only the selected learner's history and linked report are used.
The UI exposes these inputs in **How this answer uses your learning**. Citation/source
validation still applies; learner evidence is not a source for mathematical facts.
Unclear topics require clarification; missing sources produce an explicit
unavailable message. Generated paragraphs must cite supplied source IDs and include
an exact supporting evidence span. These checks do not prove factual entailment.
If generation is unavailable or fails validation, clearly labelled direct textbook
excerpts are returned. The installed small model fell back to excerpts in both live
English and Hindi checks; fluent generated explanations are not yet quality-validated.
Chat never changes assessment scores. Tests: `python -m unittest discover -s tests`.

### Reproducible results metrics

For the current diagnostic selection comparison, run `python -m diagnostic.pilot_final`.
The separately frozen twenty-case final-candidate set is `reports/pilot_final_v3_cases.json`.
Read `pilot_final_v3_report.md` for the results table, per-case comparisons, metric
definitions and observed limitations. Item-level results and provenance are saved in
`pilot_final_v3_results.csv` and `pilot_final_v3_summary.json`. No student database is
written. Development fixtures live in `tests/test_pilot_final.py`.

An independent reviewer should complete `pilot_final_v3_blind_review.csv` before
consulting `pilot_final_v3_draft_expectations.csv` or method outputs. The runner does
not overwrite the reviewer file. Human review remains pending; these are synthetic
development observations, not a validated final study. The old legacy pilot remains
separate. Version 2 of the new pilot is invalid due to Hindi transport corruption;
see `pilot_final_v2_INVALID.md`. Version 3 corrects encoding without tuning labels.

Compare retrieval depths with `python -m diagnostic.evaluate_retrieval_k --ks 1 2 3 5 10`.
The same complete ranking is truncated at each k. Tables and case-level data are in
`reports/rag_k_comparison.md`, `rag_k_comparison.csv`, `rag_k_case_results.csv`, and
`rag_k_comparison.json` (includes ranked excerpts for audit). This does not change
the chatbot's live retrieval depth or rerun generation. Recall excludes zero-evidence
cases and remains limited to concept-scoped pages. Development tuning is not an
independently validated optimum.

Compare retrieval depths with `python -m diagnostic.evaluate_retrieval_k --ks 1 2 3 5 10`.
The same complete ranking is truncated at each k. Tables and case-level data are in
`reports/rag_k_comparison.md`, `rag_k_comparison.csv`, `rag_k_case_results.csv`, and
`rag_k_comparison.json` (includes ranked excerpts for audit). This does not change
the chatbot's live retrieval depth or rerun generation. Recall excludes zero-evidence
cases and remains limited to concept-scoped pages. Development tuning is not an
independently validated optimum.

Run `python -m diagnostic.evaluate_rag --generation-cases 2` to evaluate twelve
bilingual retrieval cases, the existing 24-case mapping set, synthetic learner-evidence
policies, and two live generation requests (one per language). Use up to twelve
generation cases or omit the flag to skip generation. This uses a temporary learner
database and does not add test performances to student histories.

Outputs are `reports/rag_results.md` (report-ready table and metric definitions),
`rag_metrics.json` (configuration, hashes and summary), `rag_retrieval_results.csv`,
`rag_generation_results.csv`, and `rag_personalisation_results.csv`. Timestamped
`rag_human_review_*.csv` worksheets preserve previous reviews. Automated checks
include Hit@1/2, MRR@2, Precision@2, mapping accuracy/precision/recall, false-mapping
rate, structural citation coverage/validity, exact evidence spans, generation/fallback
rates, cache-aware latency, and personalisation policy checks.

These are development measurements, not independently reviewed learner results.
Retrieval labels are page-plus-substring proxies; citation validity is not factual
faithfulness. Report generated versus excerpt modes separately. Human mathematical
correctness, terminology, helpfulness and learning improvement are explicitly
unmeasured until a reviewer completes the worksheets and a learner study is run.

- `diagnostic/question_bank.json`: 30 bilingual items across ten concepts, including
  IDs, keys, scoring rules, possible difficulties and provisional graph reference IDs.
- `reports/question_bank.csv`: spreadsheet-friendly review copy.
- `diagnostic/engine.py`: conservative English/Hindi term mapping, direct prerequisite
  retrieval, reproducible selection/scoring/report rules and SQLite persistence.
- `src/Learner.jsx`: guided learner interaction, saved checks and printable report.
- `server.py`: local JSON API backed by the existing Python diagnostic engine.
- `reports/review_checklist.csv`: your final question/rule review and independent pilot
  expectation review. All human review records start pending.
- `reports/pilot_cases.json`: 20 separate synthetic pilot cases, frozen before execution.
- `reports/pilot_results.csv`, `pilot_summary.json`, `pilot_error_analysis.md`: paired
  fixed versus graph-guided results, metrics and limitations.

Submit an English or Hindi question or choose a topic, clarify when needed, and
start a check. At most three new questions are asked. Previous checks reopens saved
interactions from the same browser.
Responses and reports are saved in `diagnostic/history.sqlite3`. Learner codes provide
local lookup, not authentication. This development app is not a multi-user deployment.

Rules are displayed in the app and saved in each JSON report. Fixed selection orders
eligible concept and item IDs. Graph-guided selection prioritizes a one-observation
check, then direct prerequisites by graph confidence, then target. Both have the same
bank, eligible concepts and three-item budget. They do not use unrestricted graph walks,
so cycles cannot cause infinite traversal. Historical evidence uses at most the latest
two same-version observations per concept, with their question IDs excluded from reuse.

Labels require at least two concordant valid observations; mixed evidence is insufficient.
Untested concepts remain explicitly unassessed. No mastery probability is reported.
All decision rules and materials remain provisional pending human review.

## Validation and reproduction

Run `python -m unittest discover -s tests -v` for development checks. Run
`python -m diagnostic.pilot` to reproduce the frozen synthetic pilot comparison.
The output records the case and bank SHA-256 hashes. Do not tune against frozen pilot
cases; use a new case version for a later independent final study. Unit checks are
development examples, separate from the pilot case file.

`python -m diagnostic.build_bank` and `python -m diagnostic.prepare_review` are
authoring utilities, not normal startup steps: they overwrite draft artifacts.
Do not run them after a human review without preserving the completed records.

The supplied graph is provisional. Only passage identifiers, not the source textbook
passages or PDFs, are present. Consequently textbook alignment has not been verified,
and synthetic results do not establish diagnostic validity or superiority in learners.

## Local textbook practice links

The supplied English and Hindi chapter ZIPs were extracted into `assets/textbooks/en`
and `assets/textbooks/hi`. All ten chapters plus preliminaries are retained per language.
`diagnostic/textbook_catalog.json` records file hashes, page counts and selected verified
reading/practice locations for the current diagnostic scope (17 concept IDs, including
chapter-specific duplicate concepts and angle subskills).

The results screen shows an evidence-based study plan with English/Hindi PDF links,
section/exercise identifiers, printed page numbers and PDF page numbers. Existing
saved reports receive the plan when reopened through the API. These recommendations
do not change diagnostic scores or propagate difficulties to untested concepts.

English files include appended solution sheets. Catalogued practice links stay before
the detected solutions and point to inspected textbook locations. These are uploaded,
watermarked copies of pages marked Reprint 2026-27, not a claim that the entire file
or every graph relationship has been independently validated. Place-value guidance
is explicitly labelled related number-ordering practice, not a direct lesson.

Textbook links use the JSON catalog; chatbot passage extraction also requires
PyMuPDF, included in `requirements.txt`. To rebuild source metadata, run:
`python -m diagnostic.build_textbook_catalog`. The existing graph passage identifiers
remain separately unverified; they are not retroactively treated as verified exercises.

## Imported report context for feedback

The two supplied CSVs are imported into the ignored local database
`diagnostic/imported_reports.sqlite3`. Source payloads, original labels and SHA-256
hashes are retained. Neither source CSV is changed. Reimport with:

```powershell
python -m diagnostic.imported_reports "path/to/student_report.csv" "path/to/student_gap_report.csv"
```

The provisioning command links each student account to its imported report.
The linked summary appears under **My space** after signing in.

Relevant imported findings enrich the result's **From your earlier learning report**
section. An explicit vocabulary crosswalk distinguishes exact and related concepts;
unmapped topics are not silently treated as NCERT graph concepts. Source confirmed,
pending, inconclusive and not-supported flags remain attributed to the external
report. The imported files contain retrospective aggregate findings and no original
item responses or assessment dates, so they do not become scored answers, establish
current mastery, change question selection, or support claims of improvement.

The student API checks the signed-in account before returning private reports
or saved work. Links and session snapshots live in the SQLite history database.
The server binds to localhost by default.

Validation: `python -m unittest discover -s tests -p test_imported_reports.py -v`.

## Student learning spaces and graph workspace

The student screens include **My space**, **Practice**, **My progress**,
**Ask my book**, and **Concept map**. Imported profiles use deterministic display
aliases because the source CSVs supply student IDs. The report summary shows
recorded strengths, topics for practice, earlier percentages, and subject trends.

Map controls: drag a sphere to move and pin it; drag the background to orbit;
scroll to zoom; right-drag to pan. Select an idea and choose Expand connections,
or double-click its label / right-click its sphere. Expansion accumulates visible
neighbours. Collapse, hide, show all, pin/unpin and numerical X/Y/Z controls support
exploration. Save layout retains node positions in this browser. Reset layout clears
those positions, and Full screen enlarges the map. These actions customise the visual
workspace; they do not rewrite the source prerequisite graph or diagnostic rules.

## Steps 8?10 evidence record

`diagnostic.engine.map_question(text, nodes, edges)` accepts explicit English/Hindi
concept names and aliases; ambiguous, missing or duplicate matches ask for clarification.
`describe_concept(target, nodes, edges)` retrieves bilingual concept metadata, direct
incoming prerequisites and mapped verified textbook sections. They are exposed through
`POST /api/map` and `GET /api/concepts/<concept_id>`, and the learner sees the foundations
and book links before starting the check. Lexical mapping is conservative and is not a
semantic confidence probability; known contextual limitations remain documented in the pilot.

The existing three-question engine checks same-version response history, selects a
relevant item, scores it, and follows up one-observation concepts before moving to
another prerequisite where possible. The complete deterministic ranking, tie-breaking,
item reuse and stopping rules are saved in every report and viewable under the evidence
record. Responses and reports persist in SQLite and can be resumed.

Assessed concepts now include explicit status codes: 1 = Evidence supports understanding;
2 = Possible prerequisite difficulty; 3 = Insufficient evidence. Unassessed concepts
have no code and never receive an inferred difficulty. The readable report includes the
questions, responses, numeric scores, historical evidence, textbook links, and review
status. Older saved reports are enriched on read without changing their recorded findings.
First AI review is complete; independent human decision-rule review is still pending.

## Semantic mapping v2 and full source audit

The current mapper combines a pinned local multilingual MiniLM ONNX model with scope,
explicit-ambiguity and mathematical-constraint guards. It can retrieve paraphrases,
not just exact concept aliases. It does not claim unrestricted language understanding;
uncertain candidates require clarification. Similarity scores are not confidence
probabilities. The original mapper is retained as `legacy_map_question` so the frozen
20-case pilot remains reproducible.

Install optional dependencies with `python -m pip install -r requirements-semantic.txt`
and download the pinned model with `python -m diagnostic.setup_semantic`. This checkout
also supports the workspace-local dependencies in `.dist/semantic-runtime`. Model
files stay in ignored `assets/models/`; the manifest records repository revision and
file SHA-256 hashes. Learner text is embedded locally, not uploaded to a hosted API.

`python -m diagnostic.evaluate_mapping` reproduces the separate 24-case v2 holdout.
Results and limits are in `reports/semantic_mapping_results_v2.json`. Do not tune the
mapper to these held-out examples; use a new version for a later independent benchmark.

`reports/textbook_coverage_audit.json` audits all 53 graph concepts: 51 have bilingual
locations; two are explicitly unavailable. Direct references, related activities and
absent matches are distinct. Running `python -m diagnostic.build_textbook_catalog`
now builds the full audited catalog. PyMuPDF is required for this authoring utility
and runtime chatbot passage extraction; serving PDF files alone does not require it.

## Real learner study (not yet completed)

Open http://127.0.0.1:8000/study for the separate optional development-study flow.
The organiser must arrange participants, permissions and independent teacher review.
One pseudonymous participant code receives one persisted random assignment to fixed
or graph-guided selection, with empty initial history and at most three questions.
Export through http://127.0.0.1:8000/api/study/export. Review the protocol and fill
independent gold labels before running the analyser:

`python -m diagnostic.learner_study reviewed_export.json`

The collector never manufactures learner responses. Educational usefulness and learning
gains remain unestablished until actual reviewed evidence is collected. This local
research flow is not an authenticated multi-user service. See
`reports/real_learner_study_protocol.md` and `reports/completion_audit_v2.md`.

## Saved performance and profile continuity

**My past checks & progress** reads persisted SQLite responses and shows dated attempts,
actually checked concepts, scored/unscored counts and same-concept comparisons. It does
not assign the target a score when only a foundation was checked. A percentage-point
change is shown only for fully scored, identical item sets in the current bank version;
different item sets are flagged as not directly comparable. Repeated-item gains are
not proof of learning or mastery.

Provisioned accounts reuse an existing canonical learning space when available.
This keeps prior saved work accessible after the student signs in.

**Start again** and **Check another topic** preserve saved performance. **Clear all &
start again** intentionally deletes the current learner's saved checks after confirmation.
Deleted records cannot be reconstructed from the aggregate imported reports.

The answer review uses explicit cards with question text, answer, key and score; the
long technical record is optional. Print/PDF includes those answer cards even if their
on-screen section is closed. Irrelevant imported-context sections are omitted.

The graph loader accepts either `prerequisite_edges.csv` or the first sheet of
`prerequisite_edges.xlsx`. It reads the workbook without modifying it, preserving
bilingual strings and boolean metadata. The legacy Streamlit reader uses the same loader.
