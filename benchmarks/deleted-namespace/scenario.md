# deleted-namespace

**Status: authored, not recorded.** The truth sets are written; no capture exists. See "Why this is
not recorded yet".

**What this measures.** That a dangling lineage reference survives into the output, carries the
right verdict, and is flagged as re-registrable. It is the direct test of DEC-002.

## The distinction the scenario exists to enforce

A model declares a base. The base repository is gone and so is its owning namespace. The question
is what the tool should say, and the intuitive answer is wrong.

**Deletion does not contradict the lineage claim.** The derivation may well have happened; the base
was deleted afterwards. Nothing about a repository's present absence bears on whether a training
run consumed it a year ago. The verdict stays `unverifiable`.

What deletion *does* establish is a property of the reference: the name is free, so anyone can
register it, and any pipeline resolving that dependency by name will fetch whatever later occupies
it. That is the finding — and it is a fact about the reference, not a verdict on the relationship.

So the scenario demands two things at once that pull in opposite directions: **restraint** about the
lineage, and **alarm** about the reference. A tool that reports `contradicted` has over-claimed. A
tool that drops the unreachable node has erased the exposure. Both are graded, and the second is
the more likely failure because dropping unresolvable nodes is the natural implementation.

## The premise was not observed on this registry

**Read this before capturing.** A second, larger search found no instance of the case this scenario
describes, and found six of a related one.

Sampling 22,000 models by download rank gave 3,642 distinct base references across 1,182 namespaces.
423 of those namespaces never appeared as a live author; checking every one left 9 with no public
models. Of those 9:

| Outcome | Count |
|---|---|
| 307 redirect to a **different** namespace | 6 |
| 401 | 2 |
| 200 | 1 |
| **plain 404, name free — this scenario** | **0** |

This registry appears not to leave abandoned namespaces as 404s; it redirects them, usually across
ownership. See `../transferred-namespace/`, which is the shape that actually occurs, and DEC-017.

The scenario is **retained rather than deleted**, for three reasons. The behaviour it grades —
restraint about the lineage, alarm about the reference, and never dropping an unreachable node —
is correct regardless of which response produces it. Other registries have other deletion
semantics. And a redirect is a policy, not a guarantee: a name that redirects today can 404
tomorrow, and the sample above is the download-ranked head with a denominator of 9.

What changes is its status. It is no longer "waiting for a capture I expect to find" but "a case
this registry may not exhibit," and that should be stated rather than left as a stale `planned`
marker.

## Why this is not recorded yet

A sweep was run to find a real instance. `base_model:` tags were harvested from the top 4,000
models by download, yielding 730 unique base references, of which **490 were successfully checked
before the registry rate-limited the source address. Zero returned 404.**

That null result is worth keeping rather than discarding. Among heavily-downloaded models, declared
bases overwhelmingly still resolve — which is consistent with Unit 42's namespace-reuse work
concerning orphaned and low-traffic namespaces rather than popular ones. The scenario is real; it
does not live in the head of the download distribution, and a sample drawn by popularity is the
wrong instrument for finding it.

The remaining 240 references are unchecked. Completing the sweep needs an authenticated token and a
sampling frame drawn from the tail rather than the head.

**The recording will not be fabricated.** A hand-written 404 body would test the tool against an
invented response shape, and the shapes are precisely the part most likely to be wrong — this
registry returns 401 in several situations where an author would reasonably write 404, which is the
whole subject of `prose-only-base`.

## Selection criteria for the capture

1. A referring model that declares a base in structured card metadata.
2. The base repository returns 404 — not 401, which is a different scenario.
3. The base *namespace* also returns 404, so the name is genuinely free rather than merely emptied
   by an owner who still holds the account.
4. Preferably a referring model with non-trivial downloads, so the exposure is real rather than
   academic.

Criterion 3 is the one that makes this scenario distinct. A deleted repository under a live account
is not re-registrable by a third party; the account holder still owns the namespace. Only a freed
namespace creates the hijack.

## Near neighbours, and why they are separate scenarios

**`microsoft/WizardLM-2-7B` returns 401.** Microsoft withdrew the WizardLM-2 models and a number of
published models declare them as base. This is a verified real datapoint from the same sweep and is
worth its own scenario — *withdrawn-base* — but it is not this one. The namespace is alive, the name
is not re-registrable, and the response is 401 rather than 404.

**Transient throttling is a third case and it produced DEC-014.** See the following section.

## What the sweep accidentally proved

Once the source address was throttled, every request returned 429 — including `Qwen/Qwen2.5-7B` and
every other obviously-live repository. Roughly 180 live models would have been reported as deleted
by a resolver that read a non-200 as absence.

That is a worse failure than the 401 ambiguity in `prose-only-base`, because a throttle is
*transient*: a tool that caches the conclusion poisons its own output permanently on the strength of
a condition that cleared minutes later. It is also a different category from inconclusive evidence
— `unverifiable` is a statement about what the evidence supports, and a rate limit is a statement
about the client. Recorded as DEC-014.

## Pass condition

The edge present with verdict `unverifiable`; the base node present with `pinned: false`,
`reachable: false`, and both risk properties set; a `compositions` entry of `unknown` scoped to the
base; no `contradicted` verdict anywhere; and nothing from `expected-absent.yaml`, including its
omissions.
