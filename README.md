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

The public landing page has an animated 3D orbital sculpture that follows the device's reduced-motion setting. Students sign in with a provisioned username and password, or choose **Create account**. The account keeps textbook chat, topic practice and progress available across browsers on the same server.

- **My space** recommends what to review using recent practice and the mapped topics from the student's own earlier report.
- **My progress** lists saved practice results by topic and language.
- **Ask my book** answers English and Hindi questions with an answer-language selector, canonical bilingual terms, clickable PDF page citations and supporting excerpts. Conversations are saved per learner.
- **Practice** offers topic practice with exact answer keys.
- **Revision** brings scored mistakes from practice and mock exams into a notebook. Each entry includes the original response, a worked solution and a different question on the same concept. The daily plan shows up to five due entries at a time. A correct review is followed by reviews after one day and three days, and a third correct review completes the entry. A topic is marked understood when all its entries are complete. An incorrect retry returns the entry to the due list.
- **Mock exams** offer an 8-minute chapter paper or a 12-minute mixed paper in English or Hindi. Use **Save & next** or the question navigation to save answers. An unfinished paper can be resumed on the same account while its timer keeps running. The server closes the paper at its deadline and grades the saved answers. Full screen is available while taking the paper and viewing solutions.
- **Concept map** is an interactive 3D view of the prerequisite graph:
  - Drag a sphere to move and pin it; drag the background to orbit; scroll to zoom; right-drag to pan.
  - Select an idea and choose *Expand connections* (or double-click its label, or right-click its sphere). Expansion accumulates visible neighbours.
  - Collapse, hide, show all, pin/unpin and numerical X/Y/Z controls support exploration. *Save layout* keeps node positions in this browser, *Reset layout* clears them, and *Full screen* enlarges the map.
  - These actions customise the visual workspace only. They do not rewrite the source prerequisite graph or the diagnostic rules.
- **Reports.** Individual results can be printed or saved with the browser's **Save report as PDF** button. A 13-page bilingual diagnostic review pack is available at `output/pdf/Concept_Atlas_Diagnostic_Review.pdf`.

The question bank and pilot materials are developer files and are not learner navigation screens.

## Architecture

The system has four parts.

1. **Knowledge preparation (built once, offline).** Page-wise text extraction (English: PyMuPDF; Hindi: PDFium + PyMuPDF + lexicon repair), cleaned page text, a verified textbook catalogue, the prerequisite knowledge graph (proposed with gpt-oss-120b through the Groq API, then verified automatically), the diagnostic question bank, graph-based chunking with chunk metadata, a BM25 keyword index, a multilingual MiniLM encoder (ONNX Runtime, local CPU) and a vector store.
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
| Hindi names matching the book's terms | 75% | 96% |

Each concept has a stable identifier, an English name, a Hindi name and a chapter. Stable identifiers from the earlier graph were kept, so the question bank, textbook catalogue, concept mapping and saved learning records remain valid. Edges carry the reason given when they were proposed.

Every concept is checked automatically against both editions, and the graph is checked for cycles. The edges are language-model proposals that passed these checks. They have not been reviewed by teachers.

The graph loader accepts either `prerequisite_edges.csv` or the first sheet of `prerequisite_edges.xlsx`. It reads the workbook without modifying it and preserves bilingual strings and boolean metadata. The legacy Streamlit reader uses the same loader. Graph traversal in the diagnostic rules is limited to direct prerequisites, so cycles could never cause infinite traversal.

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

**Graph-based chunking** (active chunker `graph-metadata-page-v2`):
- Pages are split into sentence-like spans, and long spans are cut at word boundaries to a 650-character safety ceiling.
- Spans form a weighted graph with multilingual cosine-similarity edges at 0.48 or above. Edges may join non-adjacent sentences.
- Contiguous communities merge by the strongest mean cross-community edge weight, with missing edges counted as zero. Chunks preserve reading order and page boundaries.
- The threshold is a development heuristic, not an educationally validated setting.

**Candidate pages and search.** Candidate pages come from the catalogue for the mapped concept and language. Chunks are searched lexically (BM25) and semantically, and the lists are merged by reciprocal rank fusion. Query-to-chunk similarity retrieves up to two target chunks and one chunk for each of at most two direct prerequisites. Foundation retrieval uses its own concept query, so the target wording cannot dominate a foundation's evidence. Page embeddings are cached in memory. Search covers catalogued concept pages, not every page of every chapter.

**Ranking score.** Evidence cosine (75%), metadata-context cosine (15%) and language-specific concept-term coverage (10%). The context includes chapter, section, concept labels and language. Evidence excerpts remain exact.

**Chunk metadata.** Stable chunk IDs, chunk index and count, language and edition, chapter and section, PDF and printed page references, source hash and citation URL, the catalogue's support-relation label, character offsets in the normalized page text, and the knowledge-graph concept tags.

If embeddings are unavailable, responses explicitly record a page-excerpt fallback.

**Prerequisite ordering.** Prerequisites are ordered by possible difficulty in saved checks, then mapped earlier-report revision signals, bank coverage (concrete assessed foundations before broad chapter nodes), graph confidence, and concept ID. Evidence uses the latest three distinct question items per relevant concept in the current bank version. Two or more uniformly correct or incorrect answers use the existing conservative status rules, and mixed or limited answers remain insufficient. Unassessed concepts are never called weaknesses. Only the selected learner's history and linked report are used. The UI shows these inputs under **How this answer uses your learning**.

## Bilingual textbook chat

The chat accepts English, Hindi and Hinglish (Romanized Hindi with English maths terms). A query such as `mujhe number pattern nahi samjhta theek se` switches the response style to Hinglish. The selector offers English, Hindi and Hinglish, and later answers keep the active style. Response style is request-scoped so languages are not mixed across learners. Bank questions use local Romanized renderings with unchanged numbers, options and keys, and generated Hinglish explanations are prompted from English textbook excerpts. Source quotations keep their original language.

Normal concept explanations need at least three teaching sections, with headings, a worked example, a comparison or common mistake, and a complete practice question where the source permits. An explicit request for a brief answer can return a concise definition.

**Validation.** Generated paragraphs must cite supplied source IDs and include an exact supporting evidence span. A nonempty answer that fails validation is revised once. If the revised answer also fails, or generation is unavailable, the app returns clearly labelled textbook excerpts. Unclear topics require clarification, and missing sources produce an explicit unavailable message. These checks verify citation structure and quoted evidence; they do not prove factual entailment or mathematical correctness. Learner evidence is never a source for mathematical facts, and chat never changes assessment scores.

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
- `diagnostic/question_bank.json`: bilingual diagnostic items with IDs, keys, scoring rules, possible difficulties and provisional graph reference IDs.
- `diagnostic/textbook_catalog.json`: file hashes, page counts and verified locations.
- `reports/question_bank.csv`: spreadsheet-friendly review copy of the bank.
- `reports/review_checklist.csv`: the final question and rule review and the independent pilot expectation review. All human review records start as pending.
- `assets/textbooks/en`, `assets/textbooks/hi`: extracted textbook chapter files.
- `tests/`: development checks, separate from the frozen pilot case files.

## Limitations

- The question bank (including the 432 draft items), decision rules, pilot expectations and the chat-only probes are provisional and await independent human review.
- The prerequisite edges are language-model proposals that passed automatic checks. They have not been reviewed by teachers.
- The pilots are synthetic development observations. They do not establish diagnostic validity or superiority in real learners.
- Retrieval metrics use proxy relevance (page plus substring matching). Citation checks verify structure and quoted evidence, not factual entailment.
- Fluent generated explanations are not yet quality-validated. In earlier live English and Hindi checks, the small local Ollama model fell back to excerpts.
- The personalization data come from an English-language dataset that is not drawn from NCERT learners.
- Learner codes are identifiers, not secure authentication, and the server is a development server bound to localhost.
- No real-learner study has been completed, so no learning gain is claimed.
