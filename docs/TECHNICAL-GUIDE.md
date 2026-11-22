# Technical guide

## Shape

Python's standard-library threaded HTTP server serves the local interface and JSON APIs. SQLite stores source-work state, separate fictional CRM/reply practice and versioned planning/delivery notes. HTML/CSS/JavaScript provide the five-destination workspace and named specialist tools.

```text
New fictional fixtures -> local source-work database
                                 |
                        read-only account context
                                 |
         Accounts / Sites / internal review views
                                 |
                  separate planning + delivery store
```

`bootstrap_demo.py` creates databases from the schema-only `demo-schema.json`, then authors new fictional records. It refuses any existing runtime database. No original row data or source cache is embedded in the schema file.

## Stores generated locally

- `gtm.db`: three invented sponsor/site-context fixtures and source-owned practice work.
- `crm-simulation.db`: separate fixed fictional pipeline examples.
- `replies-simulation.db`: local decisions for fixed fictional reply scenarios.
- `operations-local.db`: versioned planning, delivery checklist and manual captures.

All DBs and SQLite sidecars are gitignored and excluded from the source ZIP. Your own later edits are private runtime data, not repository content.

## Public-candidate differences

The larger private retained-data build is not copied wholesale. The candidate removes research collectors, downloaded caches, biography preparation tables and hardcoded company-specific sales premises. It uses a small neutral research landing page, invented fixtures and an explicit public-demo banner. `/api/run` rejects refresh requests. There is no external refresh capability in the distributed candidate.

This changes the candidate's demonstration coverage. Unknown-evidence states are exercised; evidence-qualified outbound drafting with real programme premises is not reproduced. Do not claim the private build's complete dataset or its 312-test verification applies to this candidate.

## Safety boundaries

Host/Origin checks and loopback binding are local safeguards, not authentication or a security audit. Version checks reject stale covered writes. A SQLite transaction is not a staff identity. Dirty-form warnings are not crash recovery or autosave. Review never creates sending authority. No network deployment is supported.

`local_release.py` is a local backup/restore helper. Do not use its local bundle command as a public release builder: it is designed to retain local data. Use the reviewed source manifest instead.

## Checks

Run `python3 -m unittest -v test_public_candidate`. The 14-test suite makes a clean temporary copy, bootstraps invented data and checks routes, source boundaries, a planning save/conflict and local protections. It uses port 8919. It is not a full migration of the original retained-fixture regression suite, load test, penetration test or accessibility audit.

The candidate was run on Linux with Python 3.10.12. Other environments remain unverified. Chrome is needed only to reproduce screenshots, not to run the app or included unit tests.
