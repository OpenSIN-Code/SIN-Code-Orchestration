# `verifier.py` — Task Verifier

What this file does: post-task verification hook that runs the Verification Oracle on task results.

## Dependencies

- Imported by: `orchestrator.py`, tests
- Imports: `oracle` (VerificationOracle)

## Public API

- `Verifier(oracle)` — verifier with a given oracle
- `verify(results)` → list[Verdict]

## Notes

Verification is optional and enabled by default in `Orchestrator(verifier=True)`.
