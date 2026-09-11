# The dead references, two years on

**Measured:** 2026-09-10, against the 1,377 base-model names Stalnaker et al. (arXiv 2502.04484)
found unresolvable in July 2024. Recording under `docs/eval/census/recorded/` (2,229 interactions,
bodies projected to the fields read — see the manifest header), results in
`docs/eval/census/results.json`, script `scripts/measure_census.py`, source list in
`docs/eval/census/dataset/dead_declared.json`. Every figure below replays offline, and
`tests/unit/test_census_measurement.py` pins the replay to the published file.

## What the census is

Stalnaker et al. mined 760,460 models and resolved every `base_model` declaration against the
registry. 2,501 declarations, made by 2,300-odd models, pointed at identifiers the registry did not
serve — their paper says 1,371 unique; the replication package's cleaned data yields 1,377 distinct
declared strings, the difference being case and whitespace variants of the same name. That is the
only external census of broken lineage declarations, and `whence`'s namespace classifier
(DEC-017: `free`, `held-empty`, `held`, `unknown`) is a question that census could not ask: of the
names that are dead, how many sit in a namespace nobody holds, so that anyone could register it and
answer the 25 models still declaring it?

The paper's own base rate for `whence` to compare against is the 2026-09-03 sweep: 7 of 1,573
base-reference namespaces free, about 1 in 220, measured over *all* base references in the 45,000
most downloaded models. The census is a different population — references already known to be
broken — and the two figures are stated together, not reconciled.

## Coverage first

| | Names |
|---|---:|
| Declared names in the census | 1,377 |
| Not `owner/name` (bare names such as `BioLinkBERT-large`) | 180 |
| Well-formed, requested | 1,197 |

The 180 bare names carry 307 declarations and are `unresolvable` provenance here (DEC-018): the
reference cannot be constructed, so no request is made and nothing is guessed about which
repository the author meant. Every well-formed name was reached; the run is not partial, and no
request was throttled — pacing at under a hundred requests a minute stayed inside the anonymous
limit.

## What the registry says today

| Class | Names | Declarations | Meaning |
|---|---:|---:|---|
| `inconclusive` (401) | 1,166 | 2,122 | absent or private; the registry does not say which |
| `resolves` (200) | 26 | 40 | the name serves a repository again |
| `redirects` | 5 | 32 | the registry forwards the name elsewhere |
| `malformed` | 180 | 307 | no namespace; unresolvable without a request |

**No name answered 404.** All 1,166 dead names answer 401 with the body `deleted-namespace` and
`withdrawn-base` record — "Invalid username or password" for a request that carried no credentials.
The paper classified these as dead by the same signal. Two years later the registry still does not
distinguish a deleted repository from a private one at the model endpoint, which is why the
namespace lookups are the only thing that separates a dead end from a hijack opportunity.

Of the 26 that resolve, two were created after the census (`createdAt` later than July 2024) —
`TroyDoesAI/BlackSheep` on 2024-08-11 and `llm-book/Swallow-7b-hf-oasst1-21k-ja` on 2024-08-04 —
both under the same namespace that declared them. Whether the same party re-created them is not
something the registry states. The other 24 resolve with creation dates before the census; the
paper's miner did not reach them, or they were private then and public now.

Of the 5 redirects, one crosses a namespace: `freecs/ArtificialThinker-Phi2` now forwards to
`gr0010/ArtificialThinker-Phi2`. Under DEC-017 that edge carries `whence:redirect:
cross-namespace`.

## The namespaces behind the dead names

The 1,166 still-dead names sit in 516 namespaces:

| Namespace state | Namespaces | Names | Declarations | Meaning |
|---|---:|---:|---:|---|
| `held` | 434 | 1,000 | 1,821 | an organization or user holds the name: a dead end, not re-registrable |
| `held-empty` | 25 | 32 | 43 | held, with no public models — the `transferred-namespace` shape |
| **`free`** | **57** | **134** | **258** | neither an organization nor a user holds it; anyone may register it |

**134 declared base-model names, carrying 258 declarations from models that still exist, point
into 57 namespaces nobody holds.** The largest: `KT-AI/midm-bitext-S-7B-inst-v1`, declared by 25
models, whose namespace `KT-AI` answers 404 at both the organization and the user endpoint;
`heyllm234/sn6_models` and `ckpts_SFT/…` at 15 each; `andite/anything-v4.0` at 7; and 19 names
under `models/`, a namespace that is also free. Each of these is the `deleted-namespace` scenario
in the wild: a pipeline resolving the dependency by name would fetch whatever a registrant of that
namespace chose to serve, with no error.

As a rate: 57 of 516 namespaces behind dead names are free, about 1 in 9, against 1 in 220 across
all base-reference namespaces. A dead reference is far more likely than a live one to sit in a
free namespace, which is what one would expect — a namespace with no owner has nothing to keep its
repositories alive — and it is now a measured expectation rather than an argued one.

The 25 `held-empty` namespaces include `OpenAI` (capitalised) and `CohereForAI`, which redirect to
their current organizations. Those are renames, and the name still resolves for anyone who asks
the organization endpoint; the model under the old name does not.

## What this changes

Nothing in the tool. The classifier ran over 516 namespaces it had never seen and produced the
three states DEC-017 defines with no `unknown`, which is a coverage statement about the classifier
as much as a finding about the registry. What the page adds is the first count of re-registrable
base references from a population somebody else chose: 134 names, 258 declarations, 57
namespaces, all replayable.

The 675 self-referential declarations in the same census are the subject of DEC-031 and
`benchmarks/self-declared-base`; 64 of them appear in the 45,000 most downloaded models
(`docs/eval/census/dataset/self_referential_top45k.json`).
