# In-process contract - Phoenix Study
No custom REST API; browser connects to Streamlit on 127.0.0.1:8501.
Historical algebra operations are preserved in docs/LAB_API_CONTRACT.md and their existing modules.

## Source ingestion and pack generation (study.py)
extract_upload(filename, bytes) -> (text, chunks): PDF/TXT/MD, 10 MiB, PDF <=60 pages,
80-100,000 extracted characters. Encrypted, scanned/empty and malformed PDFs fail readably.
Chunk: {id, text, page: int|null, section}. IDs are local to a document; citations use these IDs.
add_document(state, title, filename, bytes, count=6, difficulty='mixed', use_ai=True, now=None)
-> (new_state, document_id, provenance_message). title <=100 chars, max20 documents, count3..10.
Normalised text hash deduplicates repeated uploads. No duplicate pack or progress loss.
Document fields: id, title, filename, text, chunks, summary, topics, questions, mode, created_at.
Question: id, prompt, topic, options[4 distinct strings], correct_index[0..3], difficulty,
hints[2], explanation, source_chunk_id, evidence_quote. Difficulty easy/medium/hard.
validate_pack verifies types, bounds, references and verbatim source quotes. It is not semantic proof.
build_pack falls back to local_pack after provider, schema or source-grounding failure.
Local mode creates missing-word questions from source statements; it is labelled extractive practice.

## Gemini boundary (ai_provider.py)
settings reads GEMINI_API_KEY or existing API_KEY from process environment / ignored .env.
Optional GEMINI_MODEL; default gemini-flash-lite-latest, verified by an actual generation call.
Secrets are repr-hidden, never stored in study state, never sent in query strings or user-visible errors.
_request uses fixed https://generativelanguage.googleapis.com/v1beta/ and x-goog-api-key header.
Generation posts models/{model}:generateContent with JSON response schema, timeout35s.
At most18 source excerpts /24,000 characters are sent; raw files are not uploaded to provider storage.
Generated content: summary, topics, questions, cards. Each item cites a provided chunk and verbatim quote.
ProviderError messages are sanitised. Missing key, quota, unavailable model, timeout, bad JSON or invalid
content uses local mode. No AI response can execute code or change scoring/scheduling logic.
User opts for AI via the sidebar toggle; building a pack then sends excerpts to Google.

## Quiz and feedback
start_quiz(state, document_id, count=5, adaptive=True, now=None) -> (state, quiz_id).
An existing unfinished quiz resumes. Unseen items come first, then weaker topic first-response rates.
Quiz: id, document_id, question_ids, completed, created_at. Max10 items; no foreign questions.
answer_question(state, quiz_id, question_id, selected_index, hint_count, token, now=None) -> state.
Answers follow quiz order; one per question/run. Duplicate token is a no-op; stale input is rejected.
Attempt: id, quiz_id, question_id, selected_index, correct, hint_count, answered_at.
Question keys determine grading; hints are generated once with the pack, not on each rerun.
Correctness, explanation and cited quote appear after answering. At most two hints are recorded.
topic_stats(state, optional document_id) uses only the first response per unique question.
Assistance is reported separately; repeated questions are labelled practice.
recommendations(state, now) returns due reviews, weak-topic practice and unfinished/new quiz actions.

## Revision and persistence
Card: id, front, back, topic, source_chunk_id, evidence_quote, document_id, due_at, step, review_count.
grade_card(state, card_id, rating, token, now=None) -> state. Only due cards are writable.
Again -> +10min/reset; Hard -> +1 day; Good ->1/3/7/14 days; Easy skips a step, max14 days.
Review: id, card_id, rating, reviewed_at. Duplicate review tokens do not reschedule twice.
All dates are timezone-aware ISO8601. The clock is injected in core tests.
State schema_version=2: documents, quizzes, attempts, cards, reviews; no credentials or lab state.
export_state -> JSON including extracted notes. import_state validates all references and grading,
closed field sets, unique IDs, timestamps and review counts; max8 MiB.
load_state/save_state use ignored .local/study.json, validating before atomic replacement.
No login or multiuser isolation: one local student workspace. Tests disable persistence or use temp paths.
DomainError(code, message) reports invalid_input/content/progress/transition; UI preserves current data.

## Main UI boundary
app.py dispatches study_app.py by default. workspace_view='Lab' opens lab_app.py with a back button.
Main navigation: Dashboard, Library, Quiz, Revision, Insights. Lab maintains its separate session/export.
A study backup does not include the lab's evidence, and the UI labels the exports separately.
