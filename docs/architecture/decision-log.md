# Decision log

**Document version:** 0.1
**Status:** Proposed
**Last updated:** 2026-09-02

Every entry is Accepted or Rejected. Nothing is Proposed: an undecided question belongs in the
scope document or an issue, not here. Violating an accepted decision is a design change requiring
a new entry, not an implementation detail.

Numbering starts at DEC-001 and is local to this repository. Where a decision inherits reasoning
from prior work, the lineage is cited in the entry rather than by continuing another project's
numbering.

---

## DEC-001 — A verdict is three-valued, never boolean

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Every claim `whence` evaluates resolves to one of `verified`, `contradicted`, or
`unverifiable`. There is no boolean verdict anywhere in the domain model, and no default that
collapses the third value into either of the first two.

**Why.** An edge the tool could not resolve is not an edge that does not exist. Reporting it as
absent converts a limit of the instrument into a statement about the world. This is the same
failure the Trace project records as DEC-009, where collapsing a Finding into a DocumentationGap
was identified as the specific error that work exists to avoid; the reasoning transfers directly
from controls to provenance.

**Alternatives considered.** A boolean plus a confidence score. Rejected: a consumer reads a
low-confidence `false` as `false`, and the third state disappears at the first integration.

**Tradeoffs.** Every consumer must handle three cases. That cost is deliberate.

---

## DEC-002 — Every node is pinned to a revision digest, never a name

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** A node in the emitted graph is identified by `(host, namespace, name, revision
digest)`. A node whose digest could not be obtained is emitted with the digest field absent and
the node marked `unverifiable`; it is never emitted as though the name identified it.

**Why.** Unit 42's Model Namespace Reuse (September 2025) demonstrated that a freed Hugging Face
namespace can be re-registered by anyone, and that orphaned namespaces were reachable through
Google Vertex AI Model Garden and Azure AI Foundry. A name-pinned dependency resolves to whatever
currently occupies the name. Name-based pinning is not provenance, and a BOM that records names is
recording assertions.

**Tradeoffs.** Digests make BOMs verbose and churn on every upstream release. Correct.

---

## DEC-003 — Output is CycloneDX ML-BOM; `whence` defines no BOM format

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** The emitted artifact is CycloneDX, currently 1.7 (ECMA-424). Provenance class and
verdict are carried in defined extension points, not by forking the schema.

**Why.** The value is in what the graph contains, not in how it serializes. A bespoke format would
make the output unconsumable by every existing SBOM tool and would put this project in competition
with a standard rather than on top of one. SPDX 3.0's Dataset profile was considered and is
insufficient for the purpose: it defines a single `DatasetPackage` class describing a corpus in
aggregate, with no per-component construct.

**Tradeoffs.** Extension points constrain what can be expressed. Where CycloneDX cannot carry
something, that is a finding to report upstream, not a reason to fork.

---

## DEC-004 — Every edge carries a provenance class

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Each edge is labelled with exactly one of `asserted-by-card`, `asserted-by-config`,
`verified-by-digest`, `verified-by-weights`, or `unresolvable`. The class is a required field. An
edge cannot be emitted without one.

**Why.** This is the mechanism that makes DEC-001 observable rather than aspirational. A consumer
must be able to see, per edge, whether a human wrote it down or the tool established it. A BOM
whose edges are uniformly trustworthy-looking is exactly the artifact this project exists to
replace.

**Open questions.** Whether `verified-by-signature` warrants a separate class from
`verified-by-digest` once OMS consumption is implemented.

---

## DEC-005 — Weight-level lineage verification is a later phase, and its claim is bounded

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** The first phase resolves and records; it does not compare weights. When weight-level
verification is added, the claim it supports is **detection of undeclared or mistaken lineage**,
and that bound is stated in the tool's own output, not only in documentation.

**Why.** The published methods — weight-space fingerprints, spectral signatures, black-box
provenance testing — are validated against models whose authors were not trying to hide anything.
An adversary who perturbs weights to defeat a similarity signature is a different threat model, and
a tool that quietly implies coverage of it is overclaiming. Quantized, merged, and heavily
continued-pretrained models are expected to be the hard cases, and where the method cannot separate
them the honest output is `unverifiable`.

**Alternatives considered.** Shipping weight comparison in phase one. Rejected: it is the part with
research risk, and gating the useful part behind it delays everything.

---

## DEC-006 — `whence` never executes model code

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** The tool does not call any framework load function, does not deserialize pickle, and
does not honour `trust_remote_code`. It reads repository metadata and, for formats that permit it,
structural headers only. Resolution that would require executing the artifact returns
`unverifiable`.

**Why.** A provenance tool that must run the artifact to describe it is a remote code execution
sink pointed at exactly the population most likely to be hostile. The record is unambiguous:
CVE-2025-32434 made `torch.load(weights_only=True)` itself exploitable across all PyTorch up to
2.5.1; CVE-2025-1550 did the same for Keras `safe_mode=True`; and CVE-2026-4372 achieved arbitrary
code execution through `transformers` config deserialization **with `trust_remote_code=False`**.
Every documented safe-loading flag in this ecosystem has been bypassed. The only defensible
position is not to load.

**Tradeoffs.** Some relationships are only discoverable by loading. Those resolve `unverifiable`,
which is the correct answer under DEC-001.

---

## DEC-007 — Traversal is depth-bounded and cycle-safe, and exceeding the bound is reported

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Graph traversal carries an explicit depth and node-count ceiling. Reaching a ceiling
stops that branch and emits an `unresolvable` edge naming what was not followed. It never silently
truncates and never omits.

**Why.** A merge lineage can be deep and cyclic. A traversal that stops quietly produces a BOM that
looks complete and is not, which is worse than one that says where it stopped.

---

## DEC-008 — Truth sets are authored, and are never supplied to the tool

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Every benchmark scenario separates `input/` from `expected/`. Nothing under
`expected/` is readable by the tool during a run. Truth sets are hand-authored, including the
negative set of relationships that genuinely do not exist.

**Why.** A benchmark that hands the system its own answer key measures nothing. The negative set is
load-bearing here specifically: without it, a tool that invents plausible edges scores well.

---

## DEC-009 — Live resolution is recorded, and the test suite replays offline

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Network interactions are captured to fixtures and replayed. The default test run
makes no network call and requires no credential. Live capture is an explicit, separately marked
operation.

**Why.** A test suite that depends on the live state of a public registry is measuring the registry.
Recorded fixtures also make the namespace-reuse and advisory-replay scenarios reproducible, which is
the point of the actionability axis in the evaluation plan.

---

## DEC-010 — The tool reports what it resolved, never what it inferred

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** No heuristic completion. If a card names a base model in prose but the reference
cannot be resolved to a concrete repository and digest, the edge is `unresolvable` with the prose
recorded as evidence. The tool does not guess which repository was meant.

**Why.** Guessing is how a transcription tool becomes indistinguishable from a verification tool.
The prose is evidence of a claim; it is not resolution of one.

---

## DEC-011 — An edge records the name it was declared under as well as the reference it resolved to

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** `Edge` carries an optional `declared_as` field holding the reference exactly as the
source material wrote it, whenever that differs from the reference the edge resolved to. Both
survive into the emitted BOM.

**Why.** Authoring the `declared-base` truth set surfaced a case the data model could not express.
`meta-llama/Llama-3.1-70B-Instruct` declares its base as `meta-llama/Meta-Llama-3.1-70B`; the
registry answers with a 307 to `meta-llama/Llama-3.1-70B`. Following a redirect the registry itself
issued is resolution rather than inference, so DEC-010 permits it — but the two names are different
strings, and an edge with a single `target` field silently discards what the author actually wrote.

A rename is also how a name stops meaning what it meant, which is the same mechanism DEC-002 is
concerned with. Discarding the declared name removes the evidence a reader would need to notice.

**Alternatives considered.** Recording the redirect only in run logs. Rejected: the BOM is the
artifact that gets consumed, and a fact that matters only when someone reads the logs is a fact
that will not be read.

**Tradeoffs.** Consumers that ignore `declared_as` see the resolved name and are no worse off than
before. Consumers that read it can detect renames.

---

## DEC-012 — Evidence excerpts are untrusted data, bounded, and never enter a log record

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** `Evidence.excerpt` may carry text taken from registry-hosted material. It is bounded
in length, retained for the emitted report only, and never interpolated into a log record. Where it
is rendered, it is delimited and any delimiter occurring inside it is neutralized. It is never
parsed for meaning, and nothing in it can change how the tool behaves.

**Why.** The `prose-only-base` scenario requires a sentence from a model card to reach the output —
without the quoted prose, an `unresolvable` edge is an assertion with nothing behind it, and a
reader cannot audit the tool's refusal to resolve. But a model card is attacker-controlled content
published by anyone with an account. The two requirements are compatible only if the excerpt is
treated as data at every point.

The distinction being drawn is between the report, where an excerpt is the evidence a human is
being asked to weigh, and a log record, where the same string is indistinguishable from prose the
tool emitted about itself.

**Tradeoffs.** Bounding the excerpt can cut a sentence mid-claim. A truncated excerpt is marked as
truncated rather than silently shortened.

---

## DEC-013 — The CycloneDX mapping: topology in `dependencies`, meaning in `declarations`

**Date:** 2026-09-02
**Status:** Accepted

**Decision.** Nodes map to `components[]` identified by purl, with the revision digest as the purl
version. Edge topology maps to `dependencies[]`. Edge semantics — relation, provenance class,
verdict, and `declared_as` — map to one `declarations.claims[]` entry per edge, with typed values
carried in `declarations.evidence[].data[]` under `whence:`-namespaced keys. Incompleteness maps to
`compositions[].aggregate`. The full mapping is `cyclonedx-mapping.md`; the worked example is
`examples/declared-base.cdx.json` and it validates against the vendored 1.7 schema.

**Why the split.** A CycloneDX `dependency` has exactly `ref`, `dependsOn`, and `provides`. It has
no `bom-ref` and no `properties`, so an edge can be neither addressed nor annotated. The part of
the format that models relationships cannot carry anything about them. Topology and meaning
therefore live in different structures and are joined by predicate.

**Rejected: carrying the verdict in `declarations.attestations[].map[].conformance.score`.** That
field is a number from 0 to 1 and is the obvious-looking home. Using it would force `unverifiable`
onto the same axis as `verified` and `contradicted`, and a consumer reading `0.0` would read "not
derived" where the truth is "not determined". This is the boolean-plus-confidence design DEC-001
already rejected in the domain model, arriving through the serialization layer; it is refused in
both places. The verdict stays a discrete token.

**Rejected: defining a `whence` BOM format, or extending the schema.** DEC-003 settled this. The
two costs the mapping incurs — a string-based claim-to-edge join, and relation kind being invisible
in `dependencies` — are recorded in `cyclonedx-mapping.md` §7 as findings to report upstream. A
`bom-ref` or a `properties` array on `dependency` would remove both.

**Tradeoffs.** A consumer that reads only `dependencies` gets a usable transitive closure and none
of the provenance. That is an acceptable failure mode: it degrades to what every other AI-BOM
already provides, rather than to something misleading.

**Open questions.** Whether `whence:` should become registered CycloneDX taxonomy rather than a
local namespace.

---

## DEC-014 — A transient resolution failure produces no verdict

**Date:** 2026-09-03
**Status:** Accepted

**Decision.** Registry responses fall into three classes and only two of them can produce a
verdict.

| Class | Responses | Result |
|---|---|---|
| Conclusive | 200; 404 | a resolution result, and a node marked reachable or not |
| Inconclusive | 401; 403 | `unverifiable`, and `compositions.aggregate: unknown` |
| Transient | 429; 5xx; timeout; connection error | **no verdict, no edge, no composition** |

A transient failure marks the run **partial**, names the references that were not reached, and
exits non-zero. A partial run may still emit a BOM, but the BOM must carry the partial marker, and
a partial run's output is never treated as a resolution of the references it could not reach.

**Why.** `unverifiable` is a claim about what the evidence supports. A rate limit is a fact about
the client. Recording "I did not get to look" as "the evidence does not settle this" is the same
category error DEC-001 exists to prevent, displaced one level up — and it is worse than the errors
DEC-001 addresses, because a transient condition clears. A tool that caches the conclusion poisons
its own output permanently on the strength of a condition that lasted minutes.

This is not hypothetical. While searching for a `deleted-namespace` candidate the registry
throttled the source address, after which every request returned 429 — including
`Qwen/Qwen2.5-7B` and every other plainly live repository. A resolver reading any non-200 as
absence would have reported roughly 180 live models as deleted.

**Alternatives considered.** Emitting `unverifiable` with a note naming the cause. Rejected: the
note is prose and the verdict is the field consumers read, so the note is what gets dropped. Also
considered retrying transparently until the class resolves, which hides a condition the caller
needs to know about and makes run duration unbounded.

**Tradeoffs.** A caller who wants a best-effort partial graph must opt into it and handle the
marker. That is the correct default for a provenance tool: a partial answer presented as a whole
one is the failure mode the project exists to avoid.

**Open questions.** Whether 404 belongs in Conclusive without qualification. This registry is known
to answer 401 in some situations where absence would be the intuitive response, so a 404 is
recorded as *absence reported by the registry* rather than as non-existence. That wording holds
for now; a registry that masks 404 as 200 would break it.

---

## DEC-015 — The relation vocabulary follows the registry's declared qualifier

**Date:** 2026-09-03
**Status:** Accepted

**Decision.** `Relation` gains `quantized-from` and `merged-from`. Where source metadata declares a
derivation qualifier, the edge records the qualified relation. Where the declaration is bare, the
edge records `derives-from` and the kind stays unspecified — it is never assumed to be
fine-tuning.

**Why.** The original vocabulary had one term for all derivation, and derivation kinds are not
interchangeable. Two samples, counting **distinct `base_model:` references**:

| Relation | Top 4,000 by download (n=1,603) | 1,000 most recently modified (n=186) |
|---|---:|---:|
| `quantized` | 1,030 (64.3%) | 63 (33.9%) |
| `finetune` | 507 (31.6%) | 84 (45.2%) |
| `adapter` | 39 (2.4%) | 27 (14.5%) |
| `merge` | 27 (1.7%) | 12 (6.5%) |

All four kinds occur in numbers too large to treat as edge cases, and **every reference in both
samples carries a qualifier — zero were bare.** The registry always states the derivation kind, so
a single generic relation discards information that is always present.

Note that the mix is sample-dependent: quantization dominates by download-weighted popularity,
where GGUF republications of popular models are overrepresented, while fine-tuning leads among
recently-modified models. That instability is itself an argument for recording the qualifier rather
than assuming a default — no default is safe across slices of the same registry.

**Correction (2026-09-03).** This entry originally cited "3,206 tags ... with the remainder bare"
and called quantization the most common derivation in the ecosystem without qualification. Both
were wrong. The 3,206 figure double-counted: the registry emits a bare tag *and* a qualified tag
for every reference, so the distinct-reference count is 1,603 and the table above sums to it. And
the ecosystem-wide claim did not survive a second sample. The decision is unchanged; its evidence
is corrected. The error was in the first commit's message, which cannot be amended, so it is
recorded here.

The consequence is not cosmetic. DEC-005 anticipates that quantized, merged, and heavily
continued-pretrained models are where weight-level comparison performs worst. An edge that carries
its qualifier tells phase two in advance which of its results are unreliable; a flattened edge
presents every derivation as equally checkable.

**On the bare case.** A `base_model:` declaration with no qualifier says a base exists and does not
say how it was used. Recording `derives-from` with the kind unspecified is what the source
supports. Inferring fine-tuning because it is the common case is exactly the inference DEC-010
forbids, and the sampling above shows it would be wrong most of the time in one slice and a
minority of the time in another.

The rule is retained as **defensive rather than load-bearing**: no bare-only reference was observed
on this registry in either sample. It covers other registries, older metadata, and the possibility
that this registry's tagging changes. A rule that never fires here is cheap; discovering the need
for it at runtime is not.

**Alternatives considered.** Making `Relation` an open vocabulary normalized like `NodeKind`.
Rejected: relation kind drives phase-two method selection, so an unrecognized relation must fail
loudly rather than normalize to something plausible. The enum stays closed and grows by decision.

**Tradeoffs.** A registry that invents a qualifier the enum lacks stops the run. That is the
intended behaviour — see above — but it means the enum needs revisiting as the ecosystem's
vocabulary moves.

---

## DEC-016 — The repository's own dependencies are pinned by content and verified by its own rules

**Date:** 2026-09-03
**Status:** Accepted

**Decision.** Vendored third-party files are pinned in `schema/PINNED.yaml` by git blob id, SHA-256,
and size, alongside the source commit. `scripts/verify_pins.py` recomputes those digests and emits
`verified`, `contradicted`, or `unverifiable` per file. Both digests are recorded rather than one:
git's object id is SHA-1 based and SHA-1 is not collision resistant, so either alone is a weaker
claim than both together.

**Why.** The schemas were originally retrieved from the `master` branch and recorded with a date.
That is a reference by name to a moving target — exactly the pattern DEC-002 rejects in a model's
dependency record — and `schema/README.md` said so in its first version while doing it anyway. A
provenance tool whose own dependency record is unpinned is not in a position to make the argument.

The verifier applies the project's rules to the project. `PINNED.yaml` is a claim; recomputing the
digests is what turns it into a finding, which is the claimed-versus-verified distinction the tool
is designed to make about model lineage (DEC-001). A missing file is `unverifiable` rather than
`contradicted`, because absence of the artifact is not evidence that the recorded digest is wrong.
And the `--online` upstream check is advisory: a network failure reports `unverifiable` and leaves
the exit code alone, per DEC-014's rule that a transient condition produces no verdict.

**Alternatives considered.** A git submodule. Rejected: it pins, but it makes the offline guarantee
depend on submodule initialisation, and the vendored set is three files that change rarely.
Recording only SHA-256 was also considered; the blob id is kept because it is the value GitHub
reports, so a pin can be checked against the API without downloading the file.

**Tradeoffs.** Updating a vendored file is now three steps rather than one. That is the intended
friction: an unnoticed change to a schema the mapping document claims conformance against is
precisely what the pin exists to catch.

**Open questions.** Whether the same treatment should extend to `uv.lock` once there are runtime
dependencies to lock. The lock file already pins; what it lacks is a verdict-emitting check in the
same shape as this one.
