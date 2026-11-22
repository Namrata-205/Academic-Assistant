# Concept Atlas

Concept Atlas is a bilingual (English and Hindi) learning assistant for the Grade 6 NCERT mathematics textbook *Ganita Prakash* (Chapters 1–10). It answers questions from the textbook with page citations, uses a prerequisite knowledge graph to find and check the foundations a topic depends on, and adapts its explanations to the learner.

| Component | Summary |
|---|---|
| Textbook corpus | Chapters 1–10, English and Hindi editions |
| Prerequisite knowledge graph | 144 concepts, 211 directed edges, 0 cycles, Hindi names from the Hindi edition |
| Diagnostic question bank | 432 draft bilingual items (at most 3 per prerequisite check) |
| Retrieval | Graph-based chunking, hybrid BM25 + semantic search, metadata-aware ranking, cross-encoder reranking |
| Generation | Configurable: Gemini (cloud), local Ollama, or offline authored explanations |
| Interface | React web app served by a Python standard-library HTTP server, SQLite storage |

All question banks, rules and pilot materials are provisional and await independent human review. See [Limitations](#limitations).

## Contents

1. [Quick start](#quick-start)
2. [Features for learners](#features-for-learners)
3. [Architecture](#architecture)
4. [Knowledge graph](#knowledge-graph)
5. [Textbook corpus and catalogue](#textbook-corpus-and-catalogue)
6. [Chunking and retrieval](#chunking-and-retrieval)
7. [Bilingual textbook chat](#bilingual-textbook-chat)
8. [Tutoring checks and practice inside chat](#tutoring-checks-and-practice-inside-chat)
9. [Diagnostic engine](#diagnostic-engine)
10. [Personalization](#personalization)
11. [Generation providers and configuration](#generation-providers-and-configuration)
12. [Accounts, privacy and storage](#accounts-privacy-and-storage)
13. [Evaluation and reproducibility](#evaluation-and-reproducibility)
14. [Real learner study](#real-learner-study-not-yet-completed)
15. [Repository layout](#repository-layout)
16. [Limitations](#limitations)

## Quick start

```powershell
npm install
python -m pip install -r requirements.txt
npm run build
python server.py
```

Open http://127.0.0.1:8000. For frontend development, run `python server.py` and `npm run dev` in separate terminals; Vite proxies API requests to port 8000.

Python's standard library serves the local API, so Streamlit is not required for the React app. The old Streamlit source is retained for reference only. The 3D renderer is bundled with the React build, so no renderer CDN is needed after installation. WebGL is required for the canvas.

Optional semantic mapping dependencies:

```powershell
python -m pip install -r requirements-semantic.txt
python -m diagnostic.setup_semantic
```

Model files are stored in the ignored `assets/models/` folder, and the manifest records the repository revision and file SHA-256 hashes. This checkout also supports the workspace-local dependencies in `.dist/semantic-runtime`. Learner text is embedded locally and is not uploaded to a hosted API.

Run the development tests with:

```powershell
python -m unittest discover -s tests -v
```

## Features for learners

The public landing page has an animated 3D orbital sculpture that follows the device's reduced-motion setting. Students sign in with their email or a provisioned username and password, or choose **Create account**. Registration asks for full name, email and a password of at least 12 characters. The account keeps textbook chat, topic practice and progress available across browsers on the same server.

- **My space** recommends what to review using recent practice and the mapped topics from the student's own earlier report.
- **My progress** lists saved practice results by topic and language.
- **Ask my book** answers English and Hindi questions with an answer-language selector, canonical bilingual terms, clickable PDF page citations and supporting excerpts. Conversations are saved per learner.
- **Practice** offers topic practice with exact answer keys.
- **Revision** brings scored mistakes from practice and mock exams into a notebook. Each entry includes the original response, a worked solution and a different question on the same concept. The daily plan shows up to five due entries at a time. A correct review is followed by reviews after one day and three days, and a third correct review completes the entry. A topic is marked understood when all its entries are complete. An incorrect retry returns the entry to the due list.
- **Mock exams** let students select one or more of the ten chapters, configure question count and time settings, and practise from easy to difficult. Papers prioritize concepts from previous mistakes and can follow an uploaded past-paper format profile. Starting an exam requests fullscreen with a focused-layout fallback. Saved papers retain their original questions and timing settings.

- **Concept map** is an interactive 3D view of the prerequisite graph:
  - Drag a sphere to move and pin it; drag the background to orbit; scroll to zoom; right-drag to pan.
  - Select an idea and choose *Expand connections* (or double-click its label, or right-click its sphere). Expansion accumulates visible neighbours.
  - Collapse, hide, show all, pin/unpin and numerical X/Y/Z controls support exploration. *Save layout* keeps node positions in this browser, *Reset layout* clears them, and *Full screen* enlarges the map.
  - These actions customise the visual workspace only. They do not rewrite the source prerequisite graph or the diagnostic rules.
- **Reports.** Individual results can be printed or saved with the browser's **Save report as PDF** button. A 13-page bilingual diagnostic review pack is available at `output/pdf/Concept_Atlas_Diagnostic_Review.pdf`.

The question bank and pilot materials are developer files and are not learner navigation screens.

## Architecture

The system has four parts.

1. **Knowledge preparation (built once, offline).** Page-wise text extraction (English: PyMuPDF; Hindi: PDFium + PyMuPDF + lexicon repair), cleaned page text, a verified textbook catalogue, the prerequisite knowledge graph (with historical model proposals preserved and the active user-reviewed v2 CSV loaded separately), the diagnostic question bank, graph-based chunking with chunk metadata, a BM25 keyword index, a multilingual MiniLM encoder (ONNX Runtime, local CPU) and cached in-memory passage vectors.
2. **Request routing.** Intent routing and concept mapping send each request to the retrieval pipeline, adaptive tutoring, the assessment services (practice, revision, mock exams) or a clarification step.
3. **Retrieval pipeline.** Concept-guided candidate pages, lexical and semantic search, reciprocal rank fusion, metadata-aware ranking and cross-encoder reranking (multilingual mMARCO MiniLM).
4. **Explanation and validation.** Answer generation from retrieved passages, followed by citation and output checks, with labelled textbook excerpts as the fallback.

Accounts, chat history, practice results, diagnostic evidence, and revision and exam records are stored in SQLite.

The prerequisite graph and the sentence-similarity graph used for chunking serve different purposes. The prerequisite graph guides diagnostic selection and the choice of foundations to retrieve, and supplies concept tags to chunks. The sentence-similarity graph groups related sentences within a page. The prerequisite graph does not decide chunk boundaries.

## Knowledge graph

The final graph was rebuilt from the cleaned textbook text. It replaces an earlier version that classified every concept pair with a language model.

| Property | Earlier graph | Final graph |
|---|---|---|
| Chapters covered | 3 (Ch. 1–3) | 10 (Ch. 1–10) |
| Concepts | 53 | 144 |
| Directed prerequisite edges | 307 | 211 |
| Edges in cycles | 13 | 0 |
| Duplicate concepts | present | none |
| Hindi-name matching reported by the graph notebook | 75% | 96% |

The notebook matching figures above are text-matching audit results, not independently rated bilingual semantic accuracy.

Each concept has a stable identifier, an English name, a Hindi name and a chapter. Stable identifiers from the earlier graph were kept, so the question bank, textbook catalogue, concept mapping and saved learning records remain valid. Edges carry the reason given when they were proposed.

Every concept is checked automatically against both editions, and the graph is checked for cycles. The user confirmed `prerequisite_edges_v2.csv` as the reviewed positive graph reference. Its original pending-review metadata is preserved; no independent teacher rating or reviewed negative-pair set is inferred from that confirmation.

The graph loader prefers `assets/NCERT_Knowledge_Graph/prerequisite_edges_v2.csv`, with the older CSV/workbook retained as historical fallback inputs. It reads the workbook without modifying it and preserves bilingual strings and boolean metadata. The legacy Streamlit reader uses the same loader. Graph traversal in the diagnostic rules is limited to direct prerequisites, so cycles could never cause infinite traversal.

## Textbook corpus and catalogue

The supplied English and Hindi chapter ZIP files were extracted into `assets/textbooks/en` and `assets/textbooks/hi`. All ten chapters plus the preliminaries are kept for each language.

`diagnostic/textbook_catalog.json` records file hashes, page counts and verified reading and practice locations. The results screen shows an evidence-based study plan with English and Hindi PDF links, section or exercise identifiers, printed page numbers and PDF page numbers. Saved reports receive the plan when reopened through the API. These recommendations do not change diagnostic scores and do not propagate difficulties to untested concepts.

English files include appended solution sheets. Catalogued practice links stay before the detected solutions. The files are uploaded, watermarked copies of pages marked Reprint 2026-27. Place-value guidance is explicitly labelled as related number-ordering practice, not a direct lesson.

Textbook links use the JSON catalogue. Chatbot passage extraction also requires PyMuPDF, which is included in `requirements.txt`. To rebuild the source metadata:

```powershell
python -m diagnostic.build_textbook_catalog
```

`reports/textbook_coverage_audit.json` records the source audit of the earlier 53-concept graph (51 concepts with bilingual locations, two explicitly unavailable). Direct references, related activities and absent matches are kept distinct.

## Chunking and retrieval

Retrieval uses catalogued, hash-checked textbook pages in the selected language.

Retrieval uses catalogued, hash-checked uploaded textbook pages in the selected
language. Sentences form a weighted graph with multilingual cosine-similarity edges at
.48 or above. Contiguous communities merge by strongest mean cross-community
edge weight (missing edges count as zero), including links between non-adjacent
sentences. Chunks preserve reading order and page boundaries, with a 650-character
  safety ceiling. The active chunker version is `graph-cross-encoder-page-v6`.
  The semantic stage combines evidence cosine (65%), metadata-context cosine (15%),
  language-specific concept-term coverage (10%), and query-term coverage (10%).
  Hindi tokenization preserves vowel signs and other combining marks. Long evidence
  is searched through overlapping token windows instead of only its first 128 tokens.
  After ranking, up to two neighboring communities per side supply bounded context
  on the same page, with a maximum returned excerpt of 650 characters. This keeps
  question headings with their nearby answers without embedding the expanded window
  as the ranking anchor. Exact duplicate expanded passages are removed.
  BM25 keyword retrieval uses Unicode words and normalized decimal digits from
  the anchor text only. Its positive-match ranks are combined with semantic ranks
  using reciprocal-rank fusion (k=60; BM25 k1=1.2, b=0.75). At this stage, no keyword
  match leaves the semantic order intact. Returned sources include both ranks and their scores;
  the final fused score is not a cosine similarity or a probability.
  A guarded diversity pass penalizes overlap with already selected page spans.
  A replacement must match or exceed the next original candidate's semantic
  score and query-term coverage; novelty cannot compensate for weaker relevance.
  This diversity stage preserves the first hybrid result and the full candidate pool.
  An optional local multilingual cross-encoder then scores the query together
  with each expanded passage in the top 20 candidates. The tail is preserved and
  labelled unscored. Its raw logits are ranking signals, not probabilities.
  Install the pinned, hash-recorded public model with
  `python -m diagnostic.setup_reranker`. No learner text is uploaded, no remote
  model code is executed, and normal requests never download model files.
  `ATLAS_RERANKER=auto` (default) uses installed artifacts; `off` keeps the v5
  ranking and `on` attempts reranking with an explicit status on failure. Set this
  as a process environment variable before starting the server. Missing or failed
  optional inference preserves the preceding ranking.
  Model: https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
  Context includes chapter, section,
concept labels and language; evidence excerpts remain exact. Sources retain stable
  chunk IDs, ranking anchors, context index ranges and character offsets in the
  reconstructed chunk sequence (not original PDF offsets).
  Run `python scripts/evaluate_passage_reranker.py` for the current comparison.
  Results are in `reports/retrieval_v6/comparison.md` and `comparison.json`.
  The experiment retains the saved v5 candidate pool and validates that live
  retrieval reproduces the same ranking and bounded context policy. It reports
  raw recall and precision alongside the coverage regression and added scoring
  latency. The v5 diversity experiment is preserved in `reports/retrieval_v5`.
  Original chunk recall is retained against the same candidate pool. A separate
  support-span coverage measure counts the union of baseline proxy-relevant
  source intervals, without double-counting overlapping excerpts. It measures
  source-text coverage, not human-reviewed facts or answer accuracy. The v3 and
  v4 experiments are preserved in their respective report directories.
  To compare current hybrid retrieval depths while preserving historical results,
    run `python -m diagnostic.evaluate_retrieval_k --ks 1 2 3 5 10 --output-dir reports/retrieval_v6/k_sweep`.
  The report separates returned-evidence metrics from anchor-ranking metrics and
  records context size. It does not change the application's retrieval depth.
  Chat allows up to three target passages only while their combined excerpts fit
  the existing 1300-character maximum (previously two passages of at most 650).
  Each of at most two direct prerequisites can contribute one separate passage.
  Fixed-k experiments and this bounded live policy are reported separately;
  actual context lengths can differ despite the same maximum. Page embeddings
  are cached in memory.
This searches catalogued concept pages, not every page of every chapter. The chunk
threshold is a development heuristic, not an educationally validated setting.
If embeddings are unavailable, responses explicitly record a page-excerpt fallback.

**Prerequisite ordering.** Prerequisites are ordered by possible difficulty in saved checks, then mapped earlier-report revision signals, bank coverage (concrete assessed foundations before broad chapter nodes), graph confidence, and concept ID. Evidence uses the latest three distinct question items per relevant concept in the current bank version. Two or more uniformly correct or incorrect answers use the existing conservative status rules, and mixed or limited answers remain insufficient. Unassessed concepts are never called weaknesses. Only the selected learner's history and linked report are used. The UI shows these inputs under **How this answer uses your learning**.

## Bilingual textbook chat

The chat accepts English, Hindi and Hinglish (Romanized Hindi with English maths terms). A query such as `mujhe number pattern nahi samjhta theek se` switches the response style to Hinglish. The selector offers English, Hindi and Hinglish, and later answers keep the active style. Response style is request-scoped so languages are not mixed across learners. Bank questions use local Romanized renderings with unchanged numbers, options and keys, and generated Hinglish explanations are prompted from English textbook excerpts. Source quotations keep their original language.

Normal concept explanations need at least three teaching sections, with headings, a worked example, a comparison or common mistake, and a complete practice question where the source permits. An explicit request for a brief answer can return a concise definition.

**Validation.** Generated paragraphs must cite supplied source IDs and include an exact supporting evidence span. A nonempty answer that fails validation is revised once. If the revised answer also fails, or generation is unavailable, the app uses local authored bilingual lessons when suitable direct support is available, with labelled excerpts as a further fallback. Unclear topics require clarification, and missing sources produce an explicit unavailable message. These checks verify citation structure and quoted evidence; they do not prove factual entailment or mathematical correctness. Learner evidence is never a source for mathematical facts, and chat never changes assessment scores.

## Tutoring checks and practice inside chat

**Intent planner.** New topic queries first pass through a Gemini intent planner (`diagnostic/chat_router.py`). Its structured decision is one of `check`, `explain`, `practice` or `clarify`, with a validated concept ID. The prompt covers confusion expressed in natural language, explicit requests to explain without testing, connected angle comparisons, follow-up context, and unsupported or ambiguous topics. The planner cannot issue tools, SQL, scores, answer keys or diagnoses. Unknown IDs, invalid actions, low-confidence plans and genuine chapter or scope ambiguity are guarded locally. API failures fall back to the deterministic router and are marked `local_fallback` in the saved response metadata.

The planner receives only the current query and public concept names and IDs (plus a previous topic ID for follow-ups). It never sees saved responses, scores, names, imported gaps or evidence summaries. Pending check or practice answers are scored locally, and the planner is bypassed for these and for **Explain now**. Planning and explanation both use the configured Gemini model, so the extra planning call adds latency.

**Check, explain, practise.** Questions that express difficulty or ask for practice start a short tutoring check when the mapped topic has bank-covered foundations.
- Up to three existing bank items are selected using graph-guided selection and available saved evidence. When bank-covered prerequisites exist, the check stays on those prerequisites; otherwise the target is a fallback.
- Answers are scored locally with exact keys. The learner can choose **Explain now** or **I'm not sure**.
- The explanation follows the check, with a local evidence summary and then an original parameterised practice variation. Possible difficulty in a checked concept prioritises that concept's practice.
- Two concordant observations can support a tentative status for a checked foundation. Mixed evidence is insufficient, and untested concepts, including the target, remain unassessed. This is a tutoring selection policy, not a change to the separately evaluated diagnostic algorithm.
- The chat-only bank (`diagnostic/tutor_bank.py`) adds eight original numeric probes for number, digit, consecutive number and number line. They have exact keys but human review is pending. They are not NCERT questions and do not change the diagnostic bank.
- Practice variations are generated from arithmetic and geometry templates with exact keys, not by unconstrained LLM generation. New practice is clearly distinguished from an actual NCERT exercise and is not new diagnostic evidence. Explanation prompts require actual sequence values and self-contained practice, and references to unseen figures or unspecified sequences are disallowed by instruction.
- Broad pattern requests use a stated number-pattern context with an invitation to switch to shapes, instead of requiring a chapter choice.

**Persistence.** Tutoring state and answers persist separately in `book_chat_tutoring`, `book_chat_check_answers` and `book_chat_practice`. They do not modify diagnostic sessions, report scores or the Previous checks dashboard. Learner isolation and **Clear all** apply to these records. Existing diagnostic history can be read to avoid repeating recent items. Learner answers and summaries stay local; Gemini receives the original topic question and selected textbook passages, not answers or scores.

## Diagnostic engine

**Mapping.** `diagnostic.engine.map_question(text, nodes, edges)` accepts explicit English and Hindi concept names and aliases. Ambiguous, missing or duplicate matches ask for clarification. The current mapper (semantic mapping v2) combines a pinned local multilingual MiniLM ONNX model with scope, explicit-ambiguity and mathematical-constraint guards. It can retrieve paraphrases, not only exact aliases, and it does not claim unrestricted language understanding. Uncertain candidates require clarification, and similarity scores are not confidence probabilities. The original mapper is retained as `legacy_map_question` so the frozen pilot stays reproducible.

`describe_concept(target, nodes, edges)` returns bilingual concept metadata, direct incoming prerequisites and mapped verified textbook sections. They are exposed through `POST /api/map` and `GET /api/concepts/<concept_id>`, so the learner sees the foundations and book links before starting a check.

**Selection and scoring.**
- At most three new questions are asked. Fixed selection orders eligible concept and item IDs. Graph-guided selection prioritises a one-observation check, then direct prerequisites by graph confidence, then the target. Both use the same bank, eligible concepts and three-item budget.
- Historical evidence uses at most the latest two same-version observations per concept, and their question IDs are excluded from reuse.
- A one-observation concept is followed up before moving to another prerequisite where possible.
- Labels require at least two concordant valid observations, and mixed evidence is insufficient. No mastery probability is reported.

**Status codes.** 1 = Evidence supports understanding; 2 = Possible prerequisite difficulty; 3 = Insufficient evidence. Unassessed concepts have no code and never receive an inferred difficulty.

The complete ranking, tie-breaking, item reuse and stopping rules are shown in the app and saved in every report. The readable report includes the questions, responses, numeric scores, historical evidence, textbook links and review status. Older saved reports are enriched on read without changing their recorded findings. Responses and reports persist in SQLite and can be resumed. All decision rules and materials remain provisional pending independent human review.

**Saved performance.** **My past checks & progress** reads persisted SQLite responses and shows dated attempts, the concepts actually checked, scored and unscored counts, and same-concept comparisons. It does not assign the target a score when only a foundation was checked. A percentage-point change is shown only for fully scored, identical item sets in the current bank version. Different item sets are flagged as not directly comparable, and repeated-item gains are not proof of learning or mastery.

**Start again** and **Check another topic** preserve saved performance. **Clear all & start again** deletes the current learner's saved checks after confirmation. Deleted records cannot be reconstructed from the aggregate imported reports. The answer review uses cards with question text, answer, key and score, and the long technical record is optional. Print/PDF includes the answer cards even if their on-screen section is closed.

## Personalization

To adapt explanations to the learner, the system identifies the concepts on which a student is weak and supplies them to the language model together with the retrieved passages and the teaching focus. Weak points are estimated from the NeurIPS 2020 Education Challenge diagnostic-question data (students' answers to multiple-choice mathematics questions). The dataset is in English and is not drawn from NCERT learners, so it provides realistic response patterns, not evidence about the target students.

Locally, learner evidence also guides prerequisite and source selection and appears in the local context panel.

**Imported report context.** Two supplied CSV files (a student report and a student gap report) are imported into the ignored local database `diagnostic/imported_reports.sqlite3`. Source payloads, original labels and SHA-256 hashes are retained, and the CSVs are not changed. Re-import with:

```powershell
python -m diagnostic.imported_reports "path/to/student_report.csv" "path/to/student_gap_report.csv"
```

The provisioning command links each student account to its imported report, and the linked summary appears under **My space**. Relevant findings enrich the result's **From your earlier learning report** section. An explicit vocabulary crosswalk distinguishes exact and related concepts, and unmapped topics are not silently treated as NCERT graph concepts. Source confirmed, pending, inconclusive and not-supported flags remain attributed to the external report. The files contain retrospective aggregate findings and no item responses or assessment dates, so they never become scored answers, establish current mastery, change question selection, or support claims of improvement. Imported profiles use deterministic display aliases.

Validation: `python -m unittest discover -s tests -p test_imported_reports.py -v`.

## Generation providers and configuration

Generation defaults to Gemini `gemini-3.5-flash-lite`, called only from Python through Google's REST `generateContent` API, so no extra SDK is needed. Copy `.env.example` to `.env` if you do not already have one, then add your key:

```dotenv
ATLAS_CHAT_PROVIDER=gemini
ATLAS_CHAT_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your_key_here
```

Alternatively, set these variables in the server's process environment. Process values override `.env`. The simple file loader supports `KEY=value` and quoted values, without variable expansion. Restart `python server.py` after setup. `.env` files are ignored by Git. Never put secrets in `VITE_` variables, frontend code, URLs or screenshots.

To use the optional local Ollama provider, set `ATLAS_CHAT_PROVIDER=ollama` and `ATLAS_CHAT_MODEL=qwen2.5:0.5b` (or another installed model). There is no automatic provider or model switch.

`GET /api/chat/status` returns the provider, model and configuration status, never the key. A configured status is not proof of valid credentials or model access. Missing keys, quota or permission errors, blocked responses and source-check failures produce labelled textbook excerpts.

**What each provider receives.** Gemini receives the current question, selected textbook excerpts, concept IDs and bilingual terminology. Saved learner history, imported reports, scores, identifiers and evidence summaries are not included in cloud requests. Only the optional local Ollama provider receives evidence summaries. Embedding retrieval runs locally and sends no query text to an external service.

Implementation references: [Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [generateContent](https://ai.google.dev/api/generate-content).

## Accounts, privacy and storage

Students register with a name, email address and password, and provisioned school usernames remain supported. The SQLite database stores password hashes and session token hashes. The student API checks the signed-in account before returning private reports or saved work. Links and session snapshots live in the SQLite history database. The server binds to localhost by default. Provisioned accounts reuse an existing canonical learning space when available, so prior saved work stays accessible after sign-in.

To provision newly imported students, export a fresh private CSV:

```powershell
python -m scripts.provision_students tmp/student-logins.csv
```

The command creates credentials only for students who lack an account and refuses to overwrite an existing export. Use `--resume` with the same path if provisioning is interrupted. Keep the CSV private and give each student only their own row.

Learner codes used by the older diagnostic flow provide local lookup, not authentication. This development app is not a multi-user deployment. Responses and reports are saved in `diagnostic/history.sqlite3`.

## Evaluation and reproducibility

These are development measurements, not independently reviewed learner results. Retrieval labels are page-plus-substring proxies, and citation validity is not factual faithfulness. Human assessment of mathematical correctness, terminology, helpfulness and learning improvement remains unmeasured until a reviewer completes the worksheets and a learner study is run.

**Diagnostic selection pilot.**
- `python -m diagnostic.pilot` reproduces the frozen synthetic pilot comparison (20 cases, `reports/pilot_cases.json`). The output records the case and bank SHA-256 hashes. Do not tune against frozen pilot cases; use a new case version for a later independent study.
- `python -m diagnostic.pilot_final` reproduces the current selection comparison on the separately frozen twenty-case set `reports/pilot_final_v3_cases.json`. Read `pilot_final_v3_report.md` for the results table, per-case comparisons, metric definitions and limitations. Item-level results and provenance are in `pilot_final_v3_results.csv` and `pilot_final_v3_summary.json`. No student database is written. Development fixtures live in `tests/test_pilot_final.py`.
- Paired fixed versus graph-guided results, metrics and limitations are in `pilot_results.csv`, `pilot_summary.json` and `pilot_error_analysis.md`.
- An independent reviewer should complete `pilot_final_v3_blind_review.csv` before consulting `pilot_final_v3_draft_expectations.csv` or any method output. The runner does not overwrite the reviewer file. Version 2 of the new pilot is invalid because of Hindi transport corruption (see `pilot_final_v2_INVALID.md`); version 3 corrects the encoding without tuning labels.

**Retrieval.**
- `python -m diagnostic.evaluate_chunking` gives a development comparison of chunking variants.
- `python -m diagnostic.evaluate_retrieval_k --ks 1 2 3 5 10` truncates the same complete ranking at each k. Tables and case-level data are in `reports/rag_k_comparison.md`, `rag_k_comparison.csv`, `rag_k_case_results.csv` and `rag_k_comparison.json` (which includes ranked excerpts for audit). This does not change the chatbot's live retrieval depth or rerun generation. Recall excludes zero-evidence cases and is limited to concept-scoped pages.
- `python -m diagnostic.evaluate_rag --generation-cases 2` evaluates twelve bilingual retrieval cases, the 24-case mapping set, synthetic learner-evidence policies, and two live generation requests (one per language). Use up to twelve generation cases, or omit the flag to skip generation. It uses a temporary learner database and does not add test performances to student histories.
  - Outputs: `reports/rag_results.md` (report-ready table and metric definitions), `rag_metrics.json` (configuration, hashes and summary), `rag_retrieval_results.csv`, `rag_generation_results.csv` and `rag_personalisation_results.csv`. Timestamped `rag_human_review_*.csv` worksheets preserve previous reviews.
  - Automated checks: Hit@1/2, MRR@2, Precision@2, mapping accuracy, precision and recall, false-mapping rate, structural citation coverage and validity, exact evidence spans, generation and fallback rates, cache-aware latency, and personalisation policy checks. Generated and excerpt modes are reported separately.
- Development tuning is not an independently validated optimum.

**Concept mapping.** `python -m diagnostic.evaluate_mapping` reproduces the separate 24-case v2 holdout. Results and limits are in `reports/semantic_mapping_results_v2.json`. Do not tune the mapper to these held-out examples; use a new version for a later independent benchmark.

**Authoring utilities.** `python -m diagnostic.build_bank` and `python -m diagnostic.prepare_review` overwrite draft artifacts. They are not normal startup steps, and they must not be run after a human review without first preserving the completed records.

### Phase 2 workflow: adaptive checks, explanations, feedback and scenario drafts

Chat asks one diagnostic question at a time. `diagnostic/tutor_selection.py` considers
all bank-covered incoming prerequisites, prioritises confirmation of one valid or
unclear observation, and selects a fresh item within a three-question budget.
The separately frozen diagnostic/pilot engine is unchanged. Existing batch sessions
can finish, but new chats use the adaptive path. Every selection saves its candidate
ranking, item/concept ID, reason and remaining budget in `book_chat_tutor_events`.
The question card offers a readable selection explanation. Selection logs are also
included in saved chat message payloads; learner reset removes these events.

Run `python -m diagnostic.audit_prerequisites` to export graph/bank coverage and
candidate rankings. Complete `reports/prerequisite_reference_review.json` with
independent important-prerequisite labels, reviewer and APPROVED status, then run
`python -m diagnostic.audit_prerequisites --references reports/prerequisite_reference_review.json`
to identify misses at ranks 3 and 5. The audit does not fabricate reference labels
or claim recall while review is pending.

`diagnostic/bilingual_glossary_v2.json` stores canonical terms and paired definition
drafts under shared concept IDs, including review fields. Automated checks preserve
numbers and recognised units; generation checks arithmetic chains and explicit
right/straight angle-measure assertions. These checks do not prove semantic equivalence
or entailment. Related-only textbook activities are labelled insufficient for a direct
explanation; unavailable foundation passages are explicitly identified. The cloud
receives only a public teaching mode and concept names, never the underlying answers,
scores, learner IDs or imported records.

After an explanation, choose **Simpler explanation**, **Show another example**,
**I still don’t understand**, or **Explain the terms**. Actions are logged and select
different teaching instructions. Right-versus-straight angle confusion has targeted
diagram questions, a short cited explanation in either language, and a new rotated
transfer diagram. Template feedback works without an LLM; other topics retain the
labelled extract fallback when generation is unavailable. Follow-up answers are saved
as separate evidence with item snapshots and content identities. Repeated attempts
on identical generated content count once. This evidence can guide later tutoring;
it never rewrites earlier diagnostic reports or establishes mastery from one answer.

`reports/scenarios_v1/cases.json` contains **60 synthetic scenario drafts / 120 language
variants**: 20 scenarios per chapter and 12 per profile (gap, no apparent gap,
calculation slip, language confusion, insufficient evidence). Thirty are development
cases and thirty are final candidates. Both languages and all profiles of a concept
family stay in the same split. Every case has draft expectations, reasons, actual
textbook passages (including related/unavailable labels), and frozen potential
responses for every bank item. A response oracle releases only requested answers.

Independent reviewers should use `reports/scenarios_v1/blind_review.csv` before
viewing the draft labels or system outputs. Complete reviewer, date, decision,
profile, gap-concept IDs as a JSON list, expected result, rationale, and translation/
passage checks. `python -m diagnostic.review_scenarios` reports readiness;
`python -m diagnostic.review_scenarios --final` fails until review is complete and
the frozen cases and settings still match. Reviewer labels stay separate from author
expectations. Neither AI review nor automated parity is counted as independent approval.

`python -m diagnostic.scenario_replay` runs only the development variants and saves
question selections and responses; it never evaluates final candidates or claims
diagnostic accuracy. Preparation commands refuse to overwrite frozen packs or completed
reviews. Later changes require a new scenario/configuration version. The final comparison
study remains separate from this functional replay.

### Local LoRA, QLoRA and full fine-tuning comparison

The local experiment uses **Qwen/Qwen3-0.6B**, not the hosted Gemini model. Its
base revision and file hashes are recorded in `reports/finetuning_v2/base_manifest.json`.
Results are in `reports/finetuning_v2/comparison.md` and `comparison.json`, with
per-method training/evaluation JSON and raw responses. Model weights and adapters
stay in ignored `.dist/finetuning/`; the live application's provider is unchanged.

Measured results on the nine model-generation development cases:

| Method | Strict response checks passed | Validation loss | Training seconds | Peak allocated GiB |
| --- | ---: | ---: | ---: | ---: |
| Base model | 0/9 | 0.901 | — | — |
| LoRA | 4/9 | 0.380 | 213.8 | 2.525 |
| QLoRA | 6/9 | 0.402 | 60.2 | 2.539 |
| Full FT | 2/9 | 0.526 | 174.5 | 4.738 |

Strict checks include raw JSON, citation IDs, exact evidence spans, language,
terminology and supported arithmetic/angle assertions. These are not mathematical
accuracy ratings. The report also includes a uniformly applied Markdown-fence
normalization diagnostic, language-specific counts, and observed failures. Both
adapter models gave an incorrect Hindi right-angle measure in R06; the guard
rejected those outputs. QLoRA had the most strict passes and LoRA the lowest loss
in this small run; no human-reviewed quality winner has been established.

The controlled arms are an untrained base, LoRA (rank 8, alpha 16), QLoRA (NF4,
double quantization, BF16 compute), and full FT (all model parameters updated in
BF16). All training arms use AdamW8bit, learning rate 0.0001, one epoch, seed 42,
micro-batch 1 and accumulation 4. The 8-bit **optimizer** lets full FT fit the 6 GB
GPU; full FT does not quantize the model weights or restrict updates to adapters.
All four arms are evaluated in BF16; QLoRA's saved adapter is loaded onto the same
unquantized base for this evaluation, so inference precision is controlled.

The frozen development corpus uses existing glossary drafts plus real textbook
passages. Training/validation/test concept families are separate; English/Hindi
pairs stay together. The shared 768-token training budget keeps 72 training examples
(36 per language) and four validation examples. Twelve existing RAG development
cases supply nine model calls and three deterministic calculation/abstention cases.
Retrieval, synthetic diagnostic observations and all input prompts are frozen once,
then reused byte-for-byte across model arms. The final scenario set is not used.

This is a small generator-only pilot with draft targets and one seed, not a final
diagnostic comparison or a learning-gain study. A lower validation loss or more
responses passing citation/evidence/arithmetic checks does not establish better
mathematical explanations. Bilingual correctness, claim support and difficulty
alignment require the shuffled `blind_quality_review.csv`; keep `blind_review_key.json`
separate until scoring is complete. English/Hindi summaries and response latency
are recorded separately. The earlier `finetuning_v1` run is a preserved 512-token
hardware/coverage feasibility check; use v2 for the comparison.

Training is isolated from the application's Python environment. For a fresh run,
use fresh report/checkpoint/base directories; preparation refuses to overwrite
existing experimental datasets, checkpoints or review sheets:

```powershell
python -m venv .dist/finetune-venv
& .dist/finetune-venv/Scripts/python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
& .dist/finetune-venv/Scripts/python.exe -m pip install -r requirements-finetune.txt
# Use a new run directory; do not overwrite the saved v2 comparison.
# Run data preparation using the application's environment (local retrieval runtime required).
python -c "from diagnostic.finetune_data import prepare; prepare('reports/finetuning_v3')"
$ftArgs = @('--root','reports/finetuning_v3','--base','.dist/finetuning/v3/base','--checkpoints','.dist/finetuning/v3/checkpoints')
& .dist/finetune-venv/Scripts/python.exe scripts/finetune_compare.py download @ftArgs
& .dist/finetune-venv/Scripts/python.exe scripts/finetune_compare.py encode @ftArgs
foreach ($method in 'full','lora','qlora') {
  & .dist/finetune-venv/Scripts/python.exe scripts/finetune_compare.py train --method $method @ftArgs
}
foreach ($method in 'baseline','lora','qlora','full') {
  & .dist/finetune-venv/Scripts/python.exe scripts/finetune_compare.py evaluate --method $method @ftArgs
}
& .dist/finetune-venv/Scripts/python.exe scripts/finetune_compare.py report @ftArgs
```

The exact installed dependency versions are in `reports/finetuning_v2/environment.txt`.
See the [Qwen model card](https://huggingface.co/Qwen/Qwen3-0.6B),
[PEFT quantization guide](https://huggingface.co/docs/peft/en/developer_guides/quantization)
and [bitsandbytes installation guide](https://huggingface.co/docs/bitsandbytes/installation).

## Real learner study (not yet completed)

Open http://127.0.0.1:8000/study for the separate, optional development-study flow. The organiser must arrange participants, permissions and independent teacher review. Each pseudonymous participant code receives one persisted random assignment to fixed or graph-guided selection, with empty initial history and at most three questions. Export through http://127.0.0.1:8000/api/study/export. Review the protocol and fill the independent gold labels before running the analyser:

```powershell
python -m diagnostic.learner_study reviewed_export.json
```

The collector never manufactures learner responses. Educational usefulness and learning gains remain unestablished until real, reviewed evidence is collected. This local research flow is not an authenticated multi-user service. See `reports/real_learner_study_protocol.md` and `reports/completion_audit_v2.md`.

## Repository layout

- `server.py`: local JSON API backed by the Python diagnostic engine.
- `src/Learner.jsx`: guided learner interaction, saved checks and printable report.
- `diagnostic/engine.py`: English/Hindi concept mapping, direct prerequisite retrieval, reproducible selection, scoring and report rules, and SQLite persistence.
- `diagnostic/chat_router.py`: Gemini intent planner with deterministic fallback.
- `diagnostic/tutor_bank.py`: eight original chat-only numeric probes.
- `diagnostic/question_bank_v2.json`: active 432-item draft bank; `question_bank.json` preserves the original 30 items for frozen historical protocols.
- `diagnostic/textbook_catalog.json`: file hashes, page counts and verified locations.
- `reports/question_bank.csv`: spreadsheet-friendly review copy of the bank.
- `reports/review_checklist.csv`: the final question and rule review and the independent pilot expectation review. All human review records start as pending.
- `assets/textbooks/en`, `assets/textbooks/hi`: extracted textbook chapter files.
- `tests/`: development checks, separate from the frozen pilot case files.

## Limitations

- The question bank (including the 432 draft items), decision rules, pilot expectations and the chat-only probes are provisional and await independent human review.
- The user attested review of the active v2 positive graph file. Independent negative-pair labels and teacher-rated direction/bilingual accuracy are not supplied.
- The pilots are synthetic development observations. They do not establish diagnostic validity or superiority in real learners.
- Retrieval metrics use proxy relevance (page plus substring matching). Citation checks verify structure and quoted evidence, not factual entailment.
- Fluent generated explanations are not yet quality-validated. In earlier live English and Hindi checks, the small local Ollama model fell back to excerpts.
- The personalization data come from an English-language dataset that is not drawn from NCERT learners.
- Learner codes are identifiers, not secure authentication, and the server is a development server bound to localhost.
- No real-learner study has been completed, so no learning gain is claimed.


## Student study workflows

The chat UI requests an understanding check before teaching a new supported topic
(`check_first: true` on `/api/chat/message`). An explicit request to explain without
questions, or the question card's skip button, proceeds to teaching. Short follow-ups
on the active topic do not automatically restart the check.

Question-card submissions use a structured, question-scoped answer. Grading is saved
on the original assistant card and restored when reopening the chat; an answer such
as `A` does not create a user chat bubble or a separate practice-feedback message.
Initial check answers may lead to the next check or the personalized explanation.
Previously submitted or mismatched question IDs are rejected.

Chat resolves short follow-ups against the active thread. Natural requests such as
"I didn't understand", "samajh nahi aaya", and "समझ नहीं आया" change the teaching
approach and example instead of grading the text as a practice answer. The composer
remains available during learning checks. Place-value follow-ups retain the original
numeric example locally and can unpack multiplication into repeated addition.

Recent dialogue is bounded to eight messages for local inference. Conversation
history is not sent to the external model; only the existing current-question,
public-topic/source and teaching-request payload is used there. Consequently the
cloud model does not have unrestricted multi-turn dialogue memory. Local authored
teaching cards and bilingual curriculum templates cover all 144 active concept labels
when direct textbook support is available. Topics without suitable direct support
abstain rather than inventing a lesson. These cards and generated
examples await teacher review. Regression checks establish behaviour, not educational
effectiveness or a measured improvement in answer accuracy.

Mock exams offer chapters 1–10 individually or together. Papers progress from easy
to difficult and prioritize concepts from the student's previous mistakes. Difficulty
levels are template-based and still need teacher review; they are not calibrated
psychometric scores. Saved exams keep their original questions and deadlines.

Students can upload a text PDF or UTF-8 TXT past paper (5 MiB, at most 30 PDF pages)
to estimate supported question-format patterns. New questions follow supported patterns;
exact past-paper wording, diagrams and marking schemes are not reproduced. Scanned PDFs need
text extraction first. Only a learner-owned pattern profile is saved, not the raw file.
Starting an exam requests browser fullscreen, with a focused layout when fullscreen
is unavailable. Students can leave fullscreen normally.

The header language selector controls the study features and concept labels.
Chat uses the full workspace. Revision collects wrong answers from practice,
submitted exams, diagnostics and chat checks, including unanswered exam questions.
It supports graded retries and scheduled reviews, with chapter practice available
when the notebook is empty.

### Phase 2 evaluation with the reviewed v2 graph

Run the development evaluation with:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_phase2_v2.py
```

Open `reports/phase2_evaluation_v2/report.html` for the nine-test results, separate
English/Hindi metrics, retrieval at k=1/2/3/5, three diagnostic selection methods,
offline explanation contexts, five complete bilingual chat demonstrations and the
paragraph-by-paragraph audit of the supplied workflow document. JSON logs, hashes,
failure examples and blind review files sit beside the report. The evaluator uses
temporary synthetic learner databases and disables external generation.

The user confirmed `prerequisite_edges_v2.csv` as the reviewed positive graph
reference; its existing review flags are preserved. Unlabelled pairs are not
independently reviewed negatives. The 60 new paired scenarios are development
drafts, not reviewed learner gold. Final-candidate cases in `reports/scenarios_v1`
remain untouched. Semantic explanation/translation ratings and a live-model
three-arm comparison are pending; do not describe structural checks or synthetic
agreement as final learner accuracy or learning gains.

### Active curriculum rebuild and latest checks

```powershell
python -m diagnostic.extraction --export
python -m diagnostic.upgrade_curriculum
python -m diagnostic.build_curriculum_bank
```

The active v2 glossary and bank cover all 144 concepts. New definitions and items
remain draft teacher-review material; original bank IDs, wording and keys are retained.
`reports/curriculum_v2/source_audit.json` records bilingual locations and term anchors;
location matching is not semantic entailment. Older textbook audits retain their
original smaller graph scope.

The 22 November 2026 local predeployment run is recorded in
`reports/deployment_check_2026_11_22/summary.json`: production build passed,
170 regression tests passed with one optional PDFium test skipped, all ten-chapter,
study and inline-chat browser checks passed, and 21 accessibility screens had no
serious/critical violations. Real Gemini answer generation passed in English and Hindi.
Tests used isolated synthetic learner databases. Hosting configuration remains separate;
local model assets are gitignored and must be provisioned when deploying.

The explicit AI content-review rubric, claim-level evidence and synthetic diagnosed-focus
reviews are in `reports/phase2_evaluation_v2/rag_answer_quality_ai_review.html` and JSON.
These are provisional assistant ratings, not independent human validation. The consolidated
previous/latest results PDF is `output/pdf/Athena_Results_Previous_vs_Latest.pdf`.
