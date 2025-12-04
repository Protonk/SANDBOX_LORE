# Validation reports (Swift)

`validation_report.json` is written by the Swift generator to capture lightweight schema/ID checks (concept references in strategies, runtime expectations sanity).

Run via:
```
cd book/graph
swift run
```

If you add new validators in Swift, document them here and keep reports additive (non-fatal) so generation doesn’t block on partial data.
