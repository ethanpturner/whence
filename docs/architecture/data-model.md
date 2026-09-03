# Data model

**Document version:** 0.1
**Status:** Proposed
**Last updated:** 2026-09-02

This document is authoritative for field names, types, and enumerations. Code conforms to it; it
does not describe code. A conformance test is intended to parse the tables below and compare them
to the implementation in both directions, so that a rename here without a corresponding change in
code fails, and so does a field the document never sanctioned.

Every object is designed to be immutable and to forbid unknown fields, so that an invented field
fails validation rather than passing downstream stripped and looking valid.

## 1. Registry

| Object | Section | Status |
|---|---|---|
| `ArtifactRef` | 2 | IMPLEMENTED — `domain.py` |
| `Node` | 3 | IMPLEMENTED — `domain.py` |
| `Edge` | 4 | IMPLEMENTED — `domain.py` |
| `Evidence` | 5 | IMPLEMENTED — `domain.py` |
| `ResolutionReport` | 6 | IMPLEMENTED — `domain.py` |

When an object is implemented, its row is flipped and the implementing model named in the same
change, or it ships unguarded. **This table was stale for every object at once**, which is what
happens when the rule has no test behind it — see the conformance-test note above.

## 2. `ArtifactRef`

Identifies a published artifact. A reference without a `revision` is a name, not an identity, and
carries `pinned = false`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `host` | str | yes | Registry host, normalized. |
| `namespace` | str | yes | Owner or organization segment. |
| `name` | str | yes | Artifact name segment. |
| `revision` | str \| None | no | Commit or content digest. Absent means unpinned. |
| `pinned` | bool | yes | `True` only when `revision` is present. Never inferred from the name. |

## 3. `Node`

A resolved artifact in the graph.

| Field | Type | Required | Notes |
|---|---|---|---|
| `ref` | `ArtifactRef` | yes | |
| `kind` | `NodeKind` | yes | See section 7. Open vocabulary. |
| `verdict` | `Verdict` | yes | See section 7. |
| `signature` | `SignatureState` | yes | See section 7. Absent signature is `unsigned`, never `invalid`. |
| `reachable` | bool | yes | Whether the artifact resolved at capture time. |
| `notes` | tuple[str, ...] | yes | Prose for a human. May be empty. Never carries excerpt content from an untrusted card. |
| `properties` | tuple[tuple[str, str], ...] | yes | Structured facts for the BOM. Separate from `notes` on purpose: these were once derived by splitting a note on `": "`, which emitted a property literally named `whence:no version declared`. |

## 4. `Edge`

A relationship between two nodes. The provenance class is required; an edge cannot exist without
one.

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | `ArtifactRef` | yes | |
| `target` | `ArtifactRef` | yes | The reference the edge resolved to. |
| `declared_as` | `ArtifactRef` \| None | no | The reference as the source material wrote it, when it differs from `target` — a registry rename or redirect. Both survive into the BOM (DEC-011). |
| `relation` | `Relation` | yes | See section 7. |
| `provenance` | `ProvenanceClass` | yes | See section 7. The DEC-004 field. |
| `verdict` | `Verdict` | yes | |
| `evidence` | tuple[`Evidence`, ...] | yes | May be empty only when `provenance` is `unresolvable`. |

## 5. `Evidence`

What supports an edge. Evidence references source material by locator and digest; it does not
inline untrusted text into logs or reports.

| Field | Type | Required | Notes |
|---|---|---|---|
| `locator` | str | yes | Where the assertion was found, e.g. a file path within a repository. |
| `content_digest` | str | yes | Digest of the material as captured. |
| `excerpt` | str \| None | no | Bounded excerpt, retained for the report only (DEC-012). |
| `excerpt_truncated` | bool | yes | Whether the excerpt was cut by the length bound. A truncated excerpt is marked, never silently shortened. |

## 6. `ResolutionReport`

The result of one run.

| Field | Type | Required | Notes |
|---|---|---|---|
| `root` | `ArtifactRef` | yes | What was asked about. |
| `nodes` | tuple[`Node`, ...] | yes | |
| `edges` | tuple[`Edge`, ...] | yes | |
| `ceilings_hit` | tuple[str, ...] | yes | Named per DEC-007. Empty when traversal completed. |
| `transient_failures` | tuple[str, ...] | yes | References not reached because resolution failed transiently (DEC-014). Empty on a complete run. |
| `inconclusive` | tuple[str, ...] | yes | References resolved and not settled — a 401 or 403. Maps to `compositions.aggregate: unknown`. Distinct from a ceiling (a stop the tool chose) and from a transient failure (no verdict at all). |
| `partial` | bool | yes | `True` when `transient_failures` is non-empty. A partial run's output is never a resolution of the references it could not reach. |
| `captured_at` | datetime | yes | |

## 7. Enumerations

**`Verdict`** — closed. `verified`, `contradicted`, `unverifiable`. There is no fourth value and no
boolean anywhere in this model (DEC-001).

**`ProvenanceClass`** — closed. `asserted-by-card`, `asserted-by-config`, `verified-by-digest`,
`verified-by-weights`, `unresolvable` (DEC-004).

**`SignatureState`** — closed. `unsigned`, `valid`, `invalid`, `unverifiable`. An artifact carrying
no signature is `unsigned`; it is never `invalid`, and the distinction is not cosmetic.

**`ResolutionClass`** — closed. `conclusive`, `inconclusive`, `transient` (DEC-014). Only the
first two may produce a verdict; a `transient` outcome produces no edge, no verdict, and no
composition, and sets `ResolutionReport.partial`.

**`Relation`** — closed (DEC-015). `derives-from`, `quantized-from`, `merged-from`, `adapts`,
`tokenized-by`, `trained-on`, `requires-package`.

Where source metadata declares a derivation qualifier, the qualified relation is recorded. Where the
declaration is bare, `derives-from` is recorded with the kind unspecified — never assumed to be
fine-tuning. The enum is closed rather than open like `NodeKind`, because relation kind drives
phase-two method selection: an unrecognized relation must stop the run rather than normalize to
something plausible.

**`NodeKind`** — open vocabulary, normalized to one spelling. Illustrative values: `model`,
`dataset`, `adapter`, `tokenizer`, `package`. A registry that names a kind this document does not
list is normalized, not rejected — the closed alternative would fail on the first novel artifact
type, and provenance for an unfamiliar kind is still provenance.

## 8. Rules that are not fields

- Where absence would read as a negative answer, the value is stated explicitly. A missing
  signature is `unsigned`. A missing digest sets `pinned = false`. Neither is `None` standing in
  for a conclusion.
- Timestamps come from a single module-level clock function, never from a direct call, so that
  recorded fixtures replay deterministically.
- An edge with `provenance = unresolvable` must carry `verdict = unverifiable`. The converse does
  not hold: an edge may be resolvable and still unverifiable.
- `Evidence.excerpt` is untrusted data (DEC-012). It never enters a log record, it is delimited
  wherever it is rendered with any delimiter inside it neutralized, and it is never parsed for
  meaning. Nothing in an excerpt can change how the tool behaves.
- `declared_as` is populated only when it differs from `target`. Populating it with a copy of
  `target` would make a rename indistinguishable from a direct hit.
- **An unreachable node is never dropped.** A node whose target could not be resolved stays in the
  graph with `reachable = false`, because the dangling reference is the finding. Dropping it
  converts a supply-chain exposure into a silently smaller graph.
- **A node whose namespace is also absent carries the re-registrable flag.** Absence of the
  repository alone is not the hazard; a freed namespace is, because the account holder no longer
  controls the name (DEC-002).
- **An absent target never yields `contradicted`.** Deletion is evidence about the reference, not
  about the relationship. The derivation may have occurred before the deletion.
