# Zero-knowledge guide to the macOS sandbox (Seatbelt)

SANDBOX_LORE is a host-bound, local-first synthetic textbook about the macOS Seatbelt sandbox, produced through a “zero-knowledge” loop of proposal and verification across humans and software agents. Agents propose structure, mappings, and explanations; the project accepts them only when they can be tied back to a small set of witnesses such as decoded binaries, stable tables, canonical profile digests, or controlled runtime observations. The project treats “plausible explanation” as a failure mode and builds a model where definitions, diagrams, tools, and worked examples are anchored in concrete artifacts and repeatable runs that a reader can regenerate and inspect. Hopefully, this protects the work from a common failure mode in systems security writing where structural facts, runtime behavior, and surrounding controls blend into a single plausible story.

## End-to-end monitoring of a confounded, censored stack

On this host, Seatbelt mediates named Operations by evaluating compiled PolicyGraphs. SBPL is the source language used to express rules, but the system enforces compiled graph-based profiles. SANDBOX_LORE aims to make this lifecycle legible end to end: how operations and filters are named and identified on the host; how SBPL compiles into graph structure; how profiles stack and interact with dynamic mechanisms like sandbox extensions; and how the runtime reaches an allow/deny decision for a specific action. 

Seatbelt sits in a stack; many failures that look like “sandbox denials” are produced elsewhere or produced earlier in the lifecycle. SANDBOX_LORE keeps several invariants close to the surface because they repeatedly decide what can be concluded on this host.

Stage matters. There is a meaningful difference between compile, apply/attach, process exec/bootstrap, and operation checks. An `EPERM` at apply time is an environment gate rather than a policy decision, and it must be modeled separately from decision-stage allow/deny.

Path strings are not stable. Filesystem and VFS canonicalization can make path-based expectations fail even when the profile looks correct at the string level, and the project treats canonicalization as something to be tested rather than assumed.

Policy is layered. Effective outcomes are produced by a stack of profiles and extensions, and adjacent systems can dominate observed behavior. TCC, hardened runtime rules, and SIP/platform protections are treated as surrounding constraints that can impersonate “sandbox behavior” and must be accounted for in any behavioral case study.

## Where the project is today

The textbook is written “about a world,” macOS Sonoma 14.4.1 (23E224) on Apple Silicon with SIP enabled. All mappings, vocabulary, decoded structures, and behavioral summaries in this repo are intended to be true of that baseline unless explicitly promoted with additional host coverage.

We have a credible static atlas of Seatbelt. This atlas has a host-derived operation and filter vocabulary that functions as the naming and ID spine for further work. It can decode and summarize real compiled profile blobs in terms of headers, operation tables, node/tag layouts for a meaningful subset, and pooled literal/regex data. A curated set of canonical system profiles serves as structural anchors: they are extracted, fingerprinted, decoded, and cross-checked enough to support downstream mapping and guardrail tests. The tooling reflects that posture by treating profile byte work, decoding, digesting, and structural validation as core infrastructure rather than ad hoc scripts.

The frontier is semantic closure: tying structure to meaning to runtime behavior with a small number of strong, repeatable witnesses. Runtime evidence exists but covers a narrow slice of the operation space and a narrow set of profile shapes. Apply-time gating on this host blocks naïve validation for some platform-derived profiles and some attachment identities, which means “just run the real system profile and observe” is not universally available. End-to-end lifecycle stories are present as scaffolding and partial experiments: the shape of the pipeline from entitlements and app metadata through parameterized policy and compiled layers to observed decisions is clear, but it is not yet a broadly reliable, promoted story across many entitlements and services. Some compiled-node payload fields remain intentionally under-interpreted where stable semantic witnesses are missing, and the project prefers bounded unknowns over guessed decoders.

## Why this project exists

Seatbelt has many partial explanations in public: fragments of file formats, scattered reverse-engineering notes, and runtime anecdotes. SANDBOX_LORE is attempting to produce something different on purpose: a single inspectable account with enough internal wiring that it can notice when it stops being true. For security engineers, reverse-engineers, tool authors, and anyone who has to reason about macOS policy behavior under change, the value is a coherent model that can be diffed, regenerated, and extended rather than re-learned from scratch.

Because the model is expressed as both prose and machine-readable artifacts, it is also intended to be a substrate for tools and agents. The project’s long-term direction includes an API-shaped view of the textbook’s concepts so that automation can ask questions in the book’s terms and receive answers that are constrained by the host’s vocabulary, mappings, and witnesses.

A host-extension pipeline is the forward-looking path that turns this from a one-off atlas into a comparative one. If additional hosts can be added by running a defined extraction and validation pipeline, the result becomes a versioned picture of how Seatbelt changes across releases: which operations and filters appear or vanish, how canonical profiles evolve structurally, and where lifecycle behavior shifts. The repo’s method is also part of its point: it is an attempt to show that humans and agents can converge on a high-fidelity, reusable technical resource without trading away falsifiability.

## How to approach the repo

Start by adopting the project’s constraints: a fixed host baseline, a fixed vocabulary spine, and explicit evidence statuses. Read the substrate material to understand the project’s definitions and lifecycle model, then treat the concept inventory and witness artifacts as the source of truth about what is grounded versus what remains provisional on this host. When extending the work, prefer producing small boundary objects with clear stage labels and controls; that is the mechanism by which progress accumulates instead of resetting.