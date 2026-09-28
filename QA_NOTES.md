# UI and functionality review — 28 September 2026

## GitHub publication verification

A clean Linux CI run passed **64 backend tests and 16 frontend tests**, plus frontend lint and the production build. This includes real MiniLM embedding, FAISS retrieval, and disk-cache tests, confirming the native-model failures below are specific to the restricted Windows environment. The previously inconsistent unknown-fact case also passed a targeted live accuracy recheck after the final guard. The full benchmark remains documented as 15/16 from its latest complete comparison.

- [Verified CI run](https://github.com/TanmayVyavahare/Infosys-AI-Response-evaluator/actions/runs/36461226724)
- [CI verification record](quality_review/ci-verification.json)
- [Focused live accuracy result](quality_review/final-accuracy-check.json)

The following sections preserve the earlier local findings and test counts.

## Follow-up evaluation-quality audit

The follow-up request tested 16 synthetic scenarios against Groq and inspected the full reports. The baseline met 10 of 16 behavior expectations; the latest completed comparison met 15 of 16. Changes address partial evidence, incomplete answers, justified abstention, evidence conflicts, claim classifications, and misleading confidence. The remaining inconsistent unknown-fact classification led to a final verbatim contradiction-evidence guard. Its regression tests pass; live verification of that last guard is pending because Groq exhausted its daily token quota. See [the detailed quality report](quality_review/REPORT.md) for exact observations, raw reports, limitations, and reproduction commands.

Final focused verification: 41 backend regression tests and 16 frontend tests passed; frontend lint and production build passed. The local embedding restriction described below remains. The earlier verification counts below document the first UI review, before this quality follow-up.

The updated app runs at http://127.0.0.1:5173 with the backend at http://127.0.0.1:8000.

## Changes

- Restored spacing that an unlayered global CSS reset had overridden. Improved mobile sizing, contrast, keyboard labels, help dialog focus/Escape behavior, reduced-motion support, and report focus.
- Single and batch modes retain independent drafts and results within the current page session. Cancel aborts the browser request and rejects late results; the server may finish work already received.
- Optional evidence is grouped under a disclosure. Source text can be pasted or uploaded, with inline file validation and read-error messages.
- CSV imports validate type, size, quotes, unique headers, column counts, and required values. Up to 50 responses per batch; no incomplete rows are silently dropped. Reference-answer columns are no longer mistaken for AI-response columns.
- Results use stable report IDs, correctly copy zero scores, handle clipboard errors, identify unavailable checks, and show real evidence. Removed hardcoded filenames, similarity scores, and invented stage timings.
- Groq credentials remain exclusively in ignored backend/.env. The configured model is openai/gpt-oss-20b, confirmed available through the authenticated Groq model listing. The previous llama-3.3-70b-versatile model returned HTTP 404. No credentials are included in this document or tracked source.
- Backend configuration loads from a stable path. Groq calls have a timeout and bounded retries. Batch concurrency is limited to three responses at a time, and the API validates batch size.
- Short source excerpts are evaluated in full without vector retrieval. Failed long-document retrieval produces a user-visible warning. Factual accuracy is unavailable without a reference or source, even when an LLM is configured.
- Explicitly requesting local-only evaluation no longer instantiates a live provider. Added regression tests and compatible dependency constraints.

## Verified

- Frontend production build and lint: passed.
- Frontend regression suite: 13 passed (request cancellation, stale-response rejection, unmount cleanup, mode preservation, API error messages, CSV parsing/validation, report copying, export payload, print dispatch).
- Backend provider and workflow regression tests: 9 passed.
- Complete backend suite: 16 passed, 14 failed because Windows Application Control prevents the local embedding stack from loading sklearn.utils.murmurhash. These failures are not being marked as successes or skipped.
- Live Groq authentication and generation: passed.
- Browser single review with reference and short source: all four metrics evaluated with Groq; HTTP 200, approximately 2.3 seconds in the observed run.
- Browser batch demo: three responses completed; aggregate results and individual inspection worked.
- Browser copy report: success feedback verified.
- Desktop and 375-pixel mobile layouts inspected; mobile page overflow fixed. Help dialog opens, focuses its close control, and dismisses with Escape.
- Frontend dependency audit after compatible updates: zero reported vulnerabilities.

## Remaining limitations

Long-document semantic retrieval and local fallback scoring do not work on this machine until the embedding dependency is permitted by its device policy. The exact observed import error is: `DLL load failed while importing murmurhash: An Application Control policy has blocked this file.` Device security settings were not changed. Ask the device administrator to review the approved Python/ML installation, or verify these workflows on an approved machine.

The in-app browser did not deliver a download-completion event, so saving the JSON to disk was not confirmed there. The JSON payload and download dispatch are covered by regression tests. Browser print dispatch is tested; a saved PDF's layout was not visually verified.

## Local environment

The original backend/venv referenced a Python installation that no longer exists. A fresh, ignored backend/venv-new environment was created with the project's dependencies and pytest. To restart from the project root in PowerShell:

```powershell
& backend/venv-new/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm.cmd run dev --prefix frontend -- --host 127.0.0.1
```

Run those commands in separate terminals. Credentials are loaded from backend/.env. Re-run tests after resolving the device-policy limitation:

```powershell
& backend/venv-new/Scripts/python.exe -m pytest backend/tests -q
npm.cmd test --prefix frontend
```


## Fallback reliability follow-up (2026-09-28)

- Removed invented capitalized-name and extra-reference requirements. The Washington question produces two requirements.
- Added reference-aware relevance/coverage estimates and retained parent-question context for pronoun-only subquestions.
- Removed semantic-similarity fact certification. When AI review fails, accuracy/source support are unscored and claims remain unverifiable.
- Added provider-failure warnings and a provisional Local Estimate verdict. Copy/JSON/print reports retain the limitations.
- Full local suite: 91 backend tests (including actual MiniLM/FAISS) and 17 frontend tests passed; frontend lint and production build passed.
- The real embedding model loaded successfully in the approved process environment. Cached model loading now avoids repeated network metadata checks at startup.
- Live Washington completeness returned 1.0. A subsequent diverse 12-case live audit stopped because Groq exhausted its daily token allowance; incomplete reports are retained in quality_review/demo-audit.json and are not evidence of a completed benchmark.
