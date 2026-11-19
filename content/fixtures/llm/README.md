# Recorded LLM fixtures

Responses replayed by the LLM gateway in fixture mode (`LLM_MODE=fixture`). Fixture mode replaces
only the provider call; every other evaluation stage runs for real.

Rules (AGENTS.md rule 8, Implementation Plan 7.6, tech lead decision 6):

- Record fixtures from real model outputs. Never generate them with the model under test or write them by hand.
- Every fixture records its provenance: prompt version, model id, input hash, recording date, and who reviewed it.
- A person reviews every fixture before it is committed.

Layout: `developer/`, `ba/`, `qa/`, `uiux/`.
