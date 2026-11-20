# Limitations

The local app is runnable: source snapshotting, FastAPI health/readiness,
the React connection page and development/combined serving are implemented.

Source snapshotting hashes the 13 core CSVs and two templates; it does not
profile, normalize or reconcile contents. Remaining calculation modules are
placeholders. No savings, totals, findings, packages or completed exports exist.
Calculation endpoints return HTTP 503 `not_ready`.

Snapshot metadata loads once at startup. Restart the backend after refreshing
the manifest. No source files are read during health requests.

Dependencies are verified on Python 3.14.6 and Node 22.14.0 on Windows. Other
environments, production hosting and approval workflows have not been verified.
