The point of building a concept inventory and a validation plan is straightforward: every important idea about the sandbox needs something concrete under it. For each “operation,” “filter,” “policy graph,” or “extension,” we want to be able to say what artifacts and behaviors show that we understand it correctly on current macOS. That is why we bothered to group concepts and sketch validation modes at all—static ingestion to see how profiles are really encoded; microprofiles and probes to see how decisions are really made; vocabulary surveys to see how names and IDs really line up; lifecycle scenarios to see when and how policies really apply.

Once we take that stance—“a concept is only as good as the evidence that constrains it”—a problem appears. We are not just challenged by ignorance; hallucinating something false about the sandbox can be more troublesome than admitting we do not know. A clean-looking test, table, or diagram built on the wrong mental model will happily “confirm” that model. If you quietly assume that the SBPL text you see is the whole policy, or that each syscall matches one operation, or that layers simply intersect as “most restrictive wins,” you can design validation that seems careful and still leads you away from how the system actually behaves.

For that reason, we try to make likely wrong models explicit before we start leaning on the inventory as a lever. The next examples walk through a small set of “fair” misconceptions—plausible, technically informed ways to be wrong about profiles, operations, filters, layers, and extensions—and show the kinds of errors they produce. Each one looks sensible in isolation, lines up with how other systems work, and can be reinforced by partial evidence—yet they will assuredly lead you astray.

### SBPL Profile

**Misconception**

“An SBPL profile is *the* policy for a process: if I read the profile text, I see the full effective sandbox.”

This treats the SBPL file (or snippet) as a self-contained, complete description of the sandbox, ignoring that:

* The effective policy can be a composition of multiple profiles (system base profile, app/container profile, service-specific overlays).
* Some behavior comes from implicit or generated rules (e.g., containerization, platform defaults), not explicitly written SBPL.

**Resulting error**

You might confidently claim:

> “If operation X is allowed in this SBPL, the process can always perform X.”

Then you design a probe that:

* Runs under a containerized app profile that is layered on top of the SBPL you’re looking at, or
* Picks a system service whose effective policy has extra hidden constraints.

Your probe reports “denied,” and you incorrectly attribute that denial to a failure in your understanding of the SBPL syntax, rather than to stacked profiles and implicit rules you never accounted for.

---

### Operation

**Misconception**

“Each syscall maps to exactly one sandbox ‘operation’, and those names are just thin labels over syscalls.”

This flattens the abstraction:

* Operations can be broader than a single syscall (e.g., multiple syscalls hitting the same operation).
* A single syscall can trigger multiple operations, or an operation can be consulted in contexts that don’t look like a single obvious syscall boundary.
* Operations sometimes correspond to higher-level notions (e.g., `file-read-data`, `mach-lookup`) rather than raw kernel entry points.

**Resulting error**

You assume:

> “If `open(2)` fails due to the sandbox, that means the `file-read-data` operation is denied.”

Then you:

* Design probes and documentation that equate “open denied” ⇔ “operation A denied,” and “open allowed” ⇔ “operation A allowed.”
* Use that equivalence to build a capabilities table.

Later you discover cases where:

* `open` fails for reasons tied to different operations (e.g., metadata-only access, path resolution, or a Mach-right precondition), or
* A different syscall hitting the same operation gives a different denial pattern.

Your whole mapping from “observed syscall outcomes” to “operation-level policy” ends up misleading, and you over- or under-estimate the scope of particular operations.

---

### Filter

**Misconception**

“Filters are simple ‘if-conditions’ that are checked once per rule; if the key/value matches, the rule fires, otherwise it’s ignored.”

This treats filters as a one-shot guard on a flat rule list, instead of:

* Nodes and edges in a graph where unmatched filters can route evaluation to other nodes.
* Something that can be evaluated in multiple stages, with default branches and combinations, not just “test and drop rule.”

**Resulting error**

You explain filters as:

> “Think of filters like `if (path == "/foo") then allow; else ignore this rule`.”

Then you:

* Try to “prove” that a certain dangerous path is unreachable because every rule with that path filter looks safely denying/allowing in isolation.
* Ignore how non-matching filters might send evaluation along a default edge that reaches a permissive decision for broader paths.

You miss an allow-path that emerges from graph structure (default edges, metafilters, fall-through) and state in your write-up:

> “Path /foo/bar is definitely denied in all cases,”

when in reality the graph structure allows it via a non-obvious route.

---

### Profile Layer / Policy Stack Evaluation Order

**Misconception**

“Multiple sandbox layers just combine as ‘most restrictive wins’ (a simple logical AND over allows/denies).”

This is an intuitive model, but:

* Real composition includes ordering, default paths, and sometimes explicit overrides.
* Some layers might introduce new operations/filters or default behavior that is not a pure subset of another.
* Extensions and dynamic changes can alter the stack in ways that do not look like a straightforward meet of policies.

**Resulting error**

You teach:

> “If any layer denies an operation, it’s denied overall; if all allow it, it’s allowed. Just think of layers as intersecting sets of permissions.”

Then you:

* Analyze a system profile + app profile + extension scenario under this AND model.
* Conclude that a certain sensitive operation is impossible because “layer B denies it.”

In practice, the effective evaluation order or an extension changes the decision path so that the deny in layer B is never reached (or is overridden). Your risk assessment or example explanation claims “this cannot happen,” when in fact it does under real evaluation order.

---

### Sandbox Extension

**Misconception**

“A sandbox extension is basically a ‘turn off sandbox here’ token; once you have one, the sandbox doesn’t really apply to that resource anymore.”

This conflates:

* Scoped, capability-like grants (often tied to a path or specific operation types) with a global disable.
* The idea that extensions can be time- or context-limited, or only affect certain operations, with a blanket exemption.

**Resulting error**

You describe extensions as:

> “If an app gets an extension for `/private/foo`, it can do anything there, sandbox be damned.”

On that basis you:

* Design probes that simply check “with extension present, can we read/write/delete everything under that path?” and treat any failure as “extension is broken” or “my understanding is wrong.”
* Overstate threat models in your teaching material (“leak one extension and the whole sandbox collapses”), ignoring narrower semantics.

You mischaracterize the scope of extensions (and thus both overestimate and misdescribe certain attacks), and you design validation that expects full removal of constraints, misinterpreting partial, correctly scoped behavior as surprising or inconsistent.

---

These misconceptions are especially dangerous because they give us a coherent but wrong model of the sandbox, and coherent wrong models are hard to dislodge. If you believe “the SBPL I’m looking at is the whole story,” you will design both attacks and defenses around that single text artifact. For a defender, that can mean auditing one app’s profile and concluding an operation is safely denied, without realizing that a system base profile, a container profile, or a per-service override is also in play. For an attacker, it can mean over-focusing on clever SBPL tricks in one layer while ignoring a weaker, more permissive layer that is actually controlling the decision path. In both cases, you are not just missing details—you are steering your entire project around the wrong object.

The syscall↔operation and “filters are simple if-statements” misconceptions push you toward fragile empirical work. If you assume each syscall perfectly corresponds to a single operation, and that filters gate rules in a flat, linear way, you will treat a small set of syscall tests as a complete map of sandbox behavior. That can produce an attractively clean spreadsheet or capability table that is quietly wrong: you infer that “operation `file-read-data` is always denied in scenario X” because a couple of `open()` calls failed, when in fact different code paths, slightly different arguments, or a different syscall hitting the same operation behave differently. Offensively, you may give up on a potential exploit avenue because your first probes suggested a stronger boundary than really exists. Defensively, you may stop probing too early, believing you have “full coverage” when you have only sampled a few points on a large decision surface.

The simplistic layer-composition model (“most restrictive wins”) is particularly insidious in threat modeling and mitigation design. If you think layers are just intersected sets of permissions, you will confidently say things like “even if this app’s profile is loose, the system profile will clamp it down,” or “if we bolt on one extra restrictive layer, the worst-case is the intersection of the two.” In reality, evaluation order, defaults, and overrides can produce effective policies that are less restrictive than any one layer viewed alone. That leads defenders to rely on “defense in depth” that is not actually there, and attackers to misjudge where conflicts or overrides will land. When you then add dynamic elements—sandbox extensions, per-launch choices, service-specific behavior—the mismatch between mental model and reality grows, but the AND-model still feels plausible enough that no one wants to rethink it.

Misunderstanding extensions amplifies these problems in both directions. If you believe extensions are effectively “turn off the sandbox here,” you will overreact when analyzing one leaked or overly broad extension, assuming catastrophic collapse of isolation where in practice there is a focused, though serious, degradation. That can cause defensive teams to misprioritize fixes, treating narrow but scary-sounding extension grants as existential while ignoring mundane, broad misconfigurations elsewhere. Conversely, you may design validation probes that expect extensions to grant omnipotence over a path; when they encounter real, scoped behavior, you mistakenly conclude that something is broken in your tests or that the system is “mysteriously inconsistent,” instead of recognizing that your mental model was too coarse. Attackers can also aim for unrealistic “one extension to rule them all” strategies and miss more modest but actually viable escalation paths.

All of these misconceptions share a pattern: they compress a layered, data-structure-heavy, evaluation-order-sensitive system into something almost like a static ACL with a few predicates. That compression makes the sandbox seem easy to reason about and tempting to summarize with a few diagrams, tables, or one-off probes. The errors are rarely obvious locally—an individual probe, a snippet of SBPL, a single profile dump can all behave in ways that appear to confirm the simplified model. The mismatches only become apparent when you look across layers, across variants of the same operation, or across lifecycle stages. A serious security project that does not explicitly guard against these specific misunderstandings will tend to build impressive-looking artifacts—diagrams, capability matrices, test suites—that are internally consistent but anchored in a distorted model, and that is exactly the kind of work that is hardest to debug later.
