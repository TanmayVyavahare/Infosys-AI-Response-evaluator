# Evaluation quality review — 28 September 2026

## Assessment

The original grading was not reliable enough to accept at face value. Six of the 16 synthetic cases exposed rubric or reporting problems. The latest completed comparison meets the defined expectations for **15 of 16 cases**, up from **10 of 16** in the baseline. These are behavior checks on a small synthetic set, not a measured general accuracy rate.

The remaining case in that full comparison was inconsistent classification of an unknown launch year. A final guard now requires an actual, verbatim contradictory passage before accepting an `INCORRECT` factual verdict. Its validation/retry behavior passes deterministic tests. A subsequent **focused live accuracy recheck passed**, returning `UNVERIFIABLE` with a null accuracy score. The full 16-case comparison was not rerun after that change because of quota limits, so 15/16 remains the honest full-comparison figure.

For publication readiness, **64 backend tests and 16 frontend tests passed on a clean Linux GitHub runner**, including real MiniLM embeddings, FAISS search and disk-cache reuse. Frontend lint and the production build also passed. [Verified CI run](https://github.com/TanmayVyavahare/Infosys-AI-Response-evaluator/actions/runs/36461226724); [machine-readable record](ci-verification.json).

## What was tested

All examples use fictional plans, products, or organizations with explicitly supplied facts, so no external factual lookup is needed. The 16 baseline cases cover correct and incorrect numbers, an irrelevant answer, missing requirements, negation, paraphrasing, approximation, unit conversion, an unsupported addition, an unknown fact, no evidence, appropriate abstention, an unnecessarily detailed reference, instructions embedded in an answer/source, and conflicting evidence.

The same 16 inputs were rerun after the initial fixes. Six affected/control cases were then rechecked after separating relevance, completeness and accuracy more strictly. Two further cases (an unspecified headquarters and an explicitly wrong date) are defined in the runner but were not reached after quota exhaustion.

## Before and latest completed results

Scores below are out of 100. A high available-check score does not mean unsupported facts are verified.

| Case | Before: verdict (score) | Latest completed: verdict (score) | Review |
|---|---|---|---|
| correct | Excellent (100.0) | Excellent (100.0) | Meets expectation |
| wrong numbers | Critical Hallucination (22.5) | Factually Unreliable (22.5) | Meets expectation |
| off topic | Off-Topic (0.0) | Off-Topic (0.0) | Meets expectation |
| incomplete | Acceptable (69.0) | Incomplete (54.0) | Meets expectation |
| negation | Critical Hallucination (22.5) | Factually Unreliable (22.5) | Meets expectation |
| paraphrase | Excellent (97.5) | Excellent (100.0) | Meets expectation |
| approximation | Excellent (100.0) | Excellent (100.0) | Meets expectation |
| unit conversion | Excellent (100.0) | Excellent (100.0) | Meets expectation |
| unsupported extra | Excellent (85.8) | Limited Evidence (86.7) | Meets expectation |
| unknown fact | Critical Hallucination (22.5) | Factually Unreliable (22.5) | Focused accuracy recheck later passed; full rerun pending |
| no evidence | Excellent (100.0) | Limited Evidence (100.0) | Meets expectation |
| appropriate abstention | Good (80.0) | Excellent (100.0) | Meets expectation |
| reference extra detail | Excellent (100.0) | Excellent (100.0) | Meets expectation |
| answer injection | Critical Hallucination (22.5) | Factually Unreliable (22.5) | Meets expectation |
| source injection | Critical Hallucination (22.5) | Factually Unreliable (22.5) | Meets expectation |
| conflicting evidence | Critical Hallucination (28.5) | Conflicting Evidence (64.3) | Meets expectation |

## Findings and changes

1. **No evidence received “Excellent, 100.”** It now receives `Limited Evidence`, shows two of four checks scored, and labels the number as an available-check score. Missing factual/source checks remain N/A. Partial scores use an amber gauge, with the verdict above the score on narrow screens.
2. **An unsupported free-laptop claim still received “Excellent.”** Reports now distinguish `UNVERIFIABLE` factual claims from `UNSUPPORTED` source claims and explicit contradictions. Accuracy is calculated only over verifiable claims, and the report discloses the fraction of claims verified. Partial evidence prevents an unconditional positive verdict.
3. **Answering one of four requests was scored inconsistently and labeled “Acceptable.”** Completeness is now derived from the requirement list: covered = 1, partial = 0.5, missing = 0. This case correctly gets 25% completeness and an `Incomplete` verdict. Missing details do not reduce topical relevance in the latest recheck.
4. **A justified “the source does not say” answer received zero completeness.** Completeness now receives source context and recognizes justified abstention for an unanswerable source-only question. This case reached 100% completeness in both subsequent completed runs.
5. **Conflicting reference/source facts were called a hallucination.** They now produce `Conflicting Evidence` with the conflicting claim retained and an explicit warning to resolve the sources.
6. **An unknown year was treated as false.** One rerun correctly treated it as unverifiable, but a later recheck regressed. The final prompt explicitly separates missing evidence from contradictory evidence, and the backend rejects an `INCORRECT` claim without a real source/reference quote. A later targeted live check returned `UNVERIFIABLE`; [the saved result](final-accuracy-check.json) explicitly records that this was an accuracy-only recheck, not a new four-metric benchmark run.

Additional safeguards reject malformed/non-finite scores, derive claim and coverage scores from their detail rows, remove invented confidence percentages, and preserve the provider error when local fallback is also unavailable. Groq retries respect the provider's requested delay within a bounded two-minute budget; daily quota waits longer than that fail promptly with an understandable message.

## Validation and evidence

Publication follow-up: **80/80 automated tests passed in Linux CI** (64 backend, including two new real-model/search integration tests; 16 frontend). The counts below describe the earlier Windows audit and remain as historical evidence.

- Frontend: **16 tests passed**; production build and lint passed.
- Backend provider/workflow/quality regressions: **41 tests passed** after the final changes, including absent contradiction quotes, retry to `UNVERIFIABLE`, daily quota handling, and preserving the failure reason.
- Final full backend suite: **48 passed, 14 failed**. The 14 failures exercise the locally blocked embedding/fallback stack; they were not skipped or counted as successes.
- Browser: submitted a no-evidence review through the UI, observed `Limited Evidence`, two checks scored, N/A factual/source scores, and the partial-assessment explanation. Screenshot: [limited-evidence-ui.png](limited-evidence-ui.png).
- Final live attempt: the first case had three unavailable checks because of quota exhaustion; its partial result is preserved in [contradiction-check.json](contradiction-check.json) and is **not** counted as a successful quality recheck.
- Groq explicitly returned HTTP 429 for **tokens per day**, with a limit of 200,000 and 198,505 already used in the diagnostic response. A tiny availability request could still succeed, but normal-size evaluations were blocked. No account or billing settings were changed.

Raw evidence: [baseline](before-paced.json), [first rerun](after.json), [six targeted rechecks](refinement.json), and [latest completed reports merged by case](latest-completed.json). Earlier runs used pacing and extra audit-only retries to obtain complete reports under short rate limits; the six targeted rechecks used the production provider's retry behavior. The current runner uses the production provider directly. LLM outputs may vary even at temperature zero.

## Remaining limitations and next verification

- The final `unknown_fact` accuracy-only recheck passed. Repeat the complete case, known incorrect facts, and the two additional cases when Groq quota is available. A verbatim quote check prevents invented citations; semantic interpretation of a real quote still depends on the model. This is not a proof of factual correctness.
- Windows Application Control blocks `sklearn.utils.murmurhash` on this machine. Long-document semantic retrieval and local fallback scoring remain unavailable until an approved dependency installation is available. Device protections were not altered.
- The claim checks are tested on short supplied sources. This audit does not establish robustness on arbitrary long documents, languages, domains, or sophisticated prompt injection.

Reproduce the completed comparison without API calls:

```powershell
& backend/venv-new/Scripts/python.exe quality_review/check_audit.py quality_review/after.json quality_review/refinement.json
```

This intentionally exits with one failed case; the unresolved live verification is not hidden. To run the pending live cases after quota is available:

```powershell
& backend/venv-new/Scripts/python.exe quality_review/run_live_audit.py quality_review/guard-recheck.json unknown_fact wrong_numbers negation answer_injection source_injection unknown_location wrong_date
```
