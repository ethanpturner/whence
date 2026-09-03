# 2026-09-03 — Looking for a deleted namespace and finding six transferred ones

Went hunting for the last `planned` scenario. The case does not appear to exist on this registry,
and the thing that does exist instead is worse.

## The search

No HF token is available, so this had to be cheap. `skip` is deprecated, so pagination went through
the `links` header — 18 pages, 22,000 models, yielding 3,642 distinct base references across 1,182
namespaces.

Checking 1,182 namespaces unauthenticated would have throttled me again. The reduction that made it
work: **most of those namespaces are provably alive already**, because they appear as authors of
models in the same sample. Subtracting them left 423 to actually check, and the
`?author=` listing endpoint turned out not to throttle the way the per-model endpoint does. All 423
completed in under a minute.

**9 namespaces had no public models. None of the 9 was a free name.**

| Outcome | Count |
|---|---|
| 307 redirect to a **different** namespace | 6 |
| 401 | 2 |
| 200 | 1 |
| plain 404, name free — the scenario I was looking for | **0** |

`deepreinforce-ai` → `ornith-ai`. `UsefulSensors` → `moonshine-ai`. `rednote-hilab` →
`dots-studio`. `osmapi/MiniMax-M2-THRIFT` → `lemuralabs/MiniMax-M2-Pruned-25`, which changed the
model name as well as the owner. And `runwayml` → `stable-diffusion-v1-5`.

## What I actually found

`runwayml/stable-diffusion-v1-5` is about as high-profile as a base reference gets. It resolves —
307 into an organization created 2024-08-30 and controlled by someone else. The `runwayml`
organization shell still returns 200 and publishes zero models. And the part that makes it a
security finding rather than a metadata curiosity: **a file requested under the old path is served
from the new namespace at the new revision, with no error and no warning.** A pipeline pinning that
base by name gets bytes from an organization the original publisher does not control.

The largest model still declaring it has 13.7M downloads.

This is the DEC-002 hazard arriving through a mechanism DEC-002 did not anticipate, and it is worse
than the one I designed for. **A freed name that nobody has claimed yields a 404 and a broken
build. A transferred name yields bytes.** The failure is silent by construction.

## The rule it broke

`declared-base` established, and DEC-011 recorded, that following a registry-issued 307 is
resolution rather than inference. That was reasoned from exactly one example —
`meta-llama/Meta-Llama-3.1-70B` → `meta-llama/Llama-3.1-70B` — a rename **inside a single
namespace**, where the owner never changes and the redirect really is bookkeeping.

Generalising from it was wrong. Six of nine observed redirects cross ownership. Under the
unqualified rule, the tool follows them and records a derivation from an artifact the author never
named, published by an organization that in this case did not exist when the declaration was made.

DEC-017 splits the cases: within-namespace is a rename, cross-namespace is resolved but flagged, and
`declared_as` moves from *recorded* to **required** in both. I considered refusing to follow
cross-namespace redirects and rejected it — the redirect is factual, organizational renames are
common, and refusing would make the tool useless against six of nine real cases while telling the
user less than a flag does.

Note what generalised badly: not a measurement this time, but a *rule inferred from a single
instance*. DEC-011 was correct about its example and wrong about the population, which is the same
error as last session's ecosystem claim wearing different clothes.

## What happened to deleted-namespace

Retained, with status `unobserved` — a new value in the registry vocabulary, documented there rather
than smuggled in.

Deleting it was tempting and would have been wrong. The behaviour it grades — restraint about the
lineage, alarm about the reference, and never dropping an unreachable node — is correct wherever the
case occurs; other registries have other deletion semantics; and **a redirect is a policy, not a
guarantee.** A name that redirects today can 404 tomorrow. The sample is also the download-ranked
head with a denominator of 9, which is thin.

What changed is honesty about its status: it is no longer "waiting for a capture I expect to find"
but "a case this registry may not exhibit," and a stale `planned` marker would have implied the
former indefinitely.

## Open next

- Whether the cross-namespace flag should distinguish a target namespace that predates the
  declaration from one created after it. Here the target org was created 2024-08-30 and the
  distinction looks meaningful — but one example looking meaningful is precisely what produced
  DEC-011's over-generalisation, so it stays an open question until there is a second.
- The five other transferred cases are captured only as a table in two scenario documents. If the
  cross-namespace flag needs tuning, they are the obvious corpus and they are already identified.
- `tearline` and `attestrun` remain unscaffolded. This session implemented the three-valued verdict
  a third time, in `verify_pins.py`. That is the extraction signal.
