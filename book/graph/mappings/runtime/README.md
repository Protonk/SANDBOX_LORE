# Runtime probes

Runtime probe outputs live here once the `runtime-checks` experiment runs.

Current / expected artifacts:
- Probe expectation matrices and (when possible) allow/deny traces or logs keyed to the profiles under test.
- Summaries tying runtime observations back to decoder expectations: which Operations and Filters we believe should be allowed/denied, and what the live Seatbelt enforcement actually does.

Role in the substrate:
- Most mappings in this tree are static views of compiled PolicyGraphs. Runtime artifacts add the enforcement layer: they show how the stacked **Policy Stack Evaluation Order**, sandbox extensions, and adjacent controls (TCC, SIP, hardened runtime) interact with Seatbelt’s decisions for specific operations.
- These traces are used as end-to-end checks that our graph-level reasoning is faithful to what macOS actually enforces on this host.
