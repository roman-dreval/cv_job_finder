# Requirements without the CV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the model copies an ad's requirements without seeing the CV; the program matches them with the CV, reads
spoken-language levels from the ad's own words and gives the verdict; a new CV only recounts.

**Architecture:** `llm` asks for facts of the ad alone (skills as strings); `grounding` matches strings with the CV
text and its technologies, checks languages against the ad, bands the share 80/20; the evaluation key no longer
contains the CV, so `worker`, `settings` and the windows recount instead of scoring again.

**Tech Stack:** Python 3.12, PySide6, pytest. **Spec:** `docs/superpowers/specs/2026-10-13-job-finder-design.md`,
section 23 (with 21 and 22).

## Global Constraints

- The values of section 23 exactly: up to 8 skills each; groups of similar technologies; 80 % / 20 %; bands 0.75 &
  must 0.7 → 8, 0.85 → 9, 0.95 → 10, under 3 must-haves → at most Worth a try 7; ≥ 0.5 Worth a try (7 at ≥ 0.6);
  Stretch 5 at ≥ 0.3, else 4.
- No CV text in the model's prompt or in the evaluation key.
- No lambdas holding `self` in new Qt code; texts of the app in English.

## Review Focus

1. An ad that mentions a language only as a benefit or a country ("v Německu", "native speakers in our lessons")
   must not require it — tests in Task 3.
2. "Python, Java or Go" with Python in the CV is ✓, "Python and Kafka" with only Python is ≈ — Task 2.
3. A CV edited in its own program during a pass: no restart, the next pass recounts — Task 5.
4. A job whose model answer lists 1–2 requirements never gets Strong fit — Task 4.
5. Old evaluations (dict skills with "match") still recount without errors — Task 2.

---

### Task 1: The model reads only the ad

**Files:** `job_finder/llm.py`, `job_finder/grounding.py` (`facts`), `job_finder/worker.py` (`cv_key` →
`scoring_key`, `_evaluate`); tests in `tests/test_llm.py`, `tests/test_grounding.py`, `tests/test_worker.py`.

- Produces: `llm.evaluate(job, rules, facts="") -> dict`; `llm.SCHEMA` must_have / nice_to_have = arrays of strings,
  maxItems 8; `llm.RULES` per section 23; `grounding.facts(job) -> str` (no CV split);
  `worker.scoring_key(s) -> str` = sha256 of `llm.fingerprint(s)`; `worker.read_cv(s) -> (text, key)`.
- Tests: the request's system message has no CV text; facts name the technologies without "in the CV"; the key
  is the same for two different CVs and changes with the model.

### Task 2: The program matches requirements with the CV

**Files:** `job_finder/grounding.py`, `job_finder/insights.py` (SQL aliases); `tests/test_grounding.py`.

- Produces: `grounding.match(skill: str, known: set[str], cv_text: str) -> str` ("yes" / "similar" / "no");
  `grounding.verdict(extraction, job, cv_text, s) -> dict` (known from `cv_technologies(cv_text)`, cached).
- Tests: alternatives, partial, similar group, phrase in one CV line, dropped items (generic work, soft, degree,
  language), "databases" is SQL, an old dict item keeps working.

### Task 3: Languages from the ad's words

**Files:** `job_finder/grounding.py` (`_language(extraction, ad, s)`); `tests/test_grounding.py`.

- Tests: "Fluent English (C1)" → C1; "plynulou češtinu" → B2, B1 passes; "Němčina – výhodou" not required;
  "v Německu" not German; "rodilými mluvčími … angličtiny" not native; Czech counts for Slovak; a language the ad
  never writes is dropped.

### Task 4: Bands 80 / 20 and few requirements

**Files:** `job_finder/grounding.py` (`verdict`), `tests/helpers.py` (`model_answer` shapes), tests.

- Tests: 3 of 4 must-haves with no nice-to-haves → Strong fit 8; all must-haves and 8 missing nice-to-haves → Strong
  fit 8; 2 must-haves all ✓ → Worth a try 7 "Only 2 requirements named…".

### Task 5: A new CV only recounts

**Files:** `job_finder/settings.py` (no SCORING_FIELDS; `CV_CHANGED` note), `job_finder/settings_window.py` (no
rescore question, no wizard note), `job_finder/window.py` (`open_settings`, `_search_changed`),
`job_finder/worker.py` (recount after a changed copy; no stop on an edited CV); tests.

- Tests: saving another CV asks nothing, recounts, starts no pass; an edited CV file → the next pass recounts and
  says so; editing the CV during a pass doesn't stop it.

### Task 6: Docs, version 1.5.0, the check on the real model

**Files:** `README.md`, `docs/how-it-works.ru.md`, `job_finder/config.py`.

- Re-run the sample and the list with the real code (GPU free), screenshots of the card, report before the merge.
