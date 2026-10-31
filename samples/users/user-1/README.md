# User 1 sample data

This folder contains fictional study material and activity for the no-account demo.

- `demo-notes.md`: source notes used for the uploaded-material example.
- `nlm-v1.json`: reviewed Newton’s Laws sample pack, including lessons, questions and cards.
- `workspace.json`: validated sample source pack, quiz answers, authored practice sessions and card review history.

Dashboard and Insights derive their scores and heatmaps from `workspace.json`; no presentation-only scores are injected. Internal `My learning` learner keys preserve the existing data contract; the UI identifies this demo as User 1. New browser sessions get independent state.

Rebuild with `python scripts/build_demo.py`. This invokes local domain functions with fixed fictional dates, makes no provider request, and never reads `.local/study.json`. UUIDs are newly generated on rebuild. No real student information is included.

## Current Physics showcase

`physics/showcase.json` is the default UI dataset. It explicitly records synthetic provenance,
eight JEE Physics chapters, 88 computed question variants, and six fictional student profiles.
The adjacent Markdown files are readable chapter notes with worked examples. Rebuild with
`python scripts/build_physics_showcase.py`. Historical `workspace.json` remains as a validated
legacy fixture for the original study application; it is not the current dashboard data source.

Physics interaction is session-only. New first answers update the same data used by student
insights and the teacher report. Hinted retries do not overwrite those first answers. The new
practice engine begins with five items and inserts same-concept checks up to fifteen total.

Current extension: three attempts per quiz question, with non-revealing concept/approach support
before the last attempt; a maximum of 15 questions; 24 concept/relation/pitfall flip cards with
mnemonics; class-wide teacher heatmaps, confusion patterns and ranked intervention plans before
the roster. Individual reports also include scoped plans. The authored bank has 11 variants per
chapter. Plans use transparent error/affected-student/recency weights and prefer unseen exit checks.

Current support protocol: three attempts per item, up to 15 total questions, 24 recall cards and
class/individual teaching plans. `physics_teaching.py` contains authored mnemonics, approaches
and counterstrategies. Fixture version 2 adds support-stage flags and 11 question variants per
chapter; existing personal checkpoint schemas are unchanged.
