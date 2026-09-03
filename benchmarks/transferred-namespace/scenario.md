# transferred-namespace

**What this measures.** That a declared reference which redirects across an ownership boundary is
resolved, flagged, and reported *with the name its author wrote* — not silently replaced by whatever
the redirect lands on.

**Subject.** `Comfy-Org/stable-diffusion-v1-5-archive` at revision
`9cfd069101959ca3828bf9c04a4419870832b74f`, 13,752,170 downloads at capture. It declares
`runwayml/stable-diffusion-v1-5` as its base.

## What the registry actually does

| Request | Result |
|---|---|
| `runwayml/stable-diffusion-v1-5` | **307** → `stable-diffusion-v1-5/stable-diffusion-v1-5` |
| the redirect target | 200, sha `451f4fe…`, org created **2024-08-30** |
| `runwayml` organization | **200** — the shell exists |
| `?author=runwayml` | `[]` — zero public models |
| `runwayml` as a *user* | 404 |
| a file under the old path | **200, served from the new namespace** at `451f4fe…` |

So the reference is not broken. It resolves, quietly, into a namespace controlled by a different
party, and content fetches follow it with no error and no warning. A pipeline pinning this base by
name gets bytes from an organization the original publisher does not control.

That last row is the one that matters. This is not a metadata curiosity; it is a live content
substitution path affecting a base declared by many models, the largest of which alone has 13.7M
downloads.

## Why this scenario replaced the one I was looking for

I went looking for `deleted-namespace` — a base whose repository and owning namespace both 404,
leaving the name free to re-register. The search found something else.

Sampling 22,000 models by download rank yielded 3,642 distinct base references across 1,182
namespaces. Of those, 423 namespaces never appeared as a live author in the sample; checking all of
them left **9 with no public models**. Not one was a free name:

| Outcome | Count |
|---|---|
| 307 redirect to a **different** namespace | **6** |
| 401 | 2 |
| 200 | 1 |
| plain 404, name free | **0** |

`deepreinforce-ai` → `ornith-ai`. `UsefulSensors` → `moonshine-ai`. `rednote-hilab` → `dots-studio`.
`osmapi/MiniMax-M2-THRIFT` → `lemuralabs/MiniMax-M2-Pruned-25`, which changed the model name as well
as the owner. And `runwayml` → `stable-diffusion-v1-5`.

**This registry does not leave abandoned namespaces as 404s. It redirects them, usually across
ownership.** The hazard is real and it is not the shape I had assumed: not "the name is free for an
attacker to claim" but "the name has already been transferred and every resolver follows it
silently."

The sample is the download-ranked head and 9 empty namespaces is a small denominator, so this is
evidence about a slice, not a law. It is enough to say the scenario I authored describes a case I
could not find, while this one describes six.

## The rule this breaks

`declared-base` established, and DEC-011 recorded, that following a registry-issued 307 is
*resolution* rather than inference. That was reasoned from
`meta-llama/Meta-Llama-3.1-70B` → `meta-llama/Llama-3.1-70B` — a rename **inside one namespace**,
where the owner is unchanged and the redirect genuinely is bookkeeping.

Six of the nine redirects observed here cross ownership. Applying the same rule to them means the
tool records a derivation from an artifact the author never named, published by an organization that
in this case did not exist when the declaration was made. The rule was correct and
under-qualified; DEC-017 splits it.

## Pass condition

The base edge present with `declared_as: runwayml/stable-diffusion-v1-5` **and** target
`stable-diffusion-v1-5/stable-diffusion-v1-5`, verdict `unverifiable`, carrying
`whence:redirect: cross-namespace` and `whence:risk: ownership-boundary-crossed`; the old reference
recorded as `held-empty` and **not** flagged re-registrable; a `compositions` entry of `unknown`
scoped to the declared name; and no `verified` verdict anywhere.
