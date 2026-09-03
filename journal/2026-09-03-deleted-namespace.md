# 2026-09-03 — deleted-namespace: a null result, and the failure the sweep caused

Authored `deleted-namespace`. Registered `planned`, not `recorded`, because the capture could not be
made honestly.

## The sweep, and what it found by not finding anything

The plan was to locate a real artifact whose declared base is gone. Harvested `base_model:` tags
across the top 4,000 models by download — 730 unique base references — and checked them.
**490 resolved before the registry throttled the source address. None returned 404.**

The null result is the useful part. Among heavily-downloaded models, declared bases overwhelmingly
still resolve, which lines up with Unit 42's namespace-reuse work concerning orphaned, low-traffic
namespaces rather than popular ones. **A sample drawn by popularity is the wrong instrument for
finding this case.** Completing the search needs an authenticated token and a sampling frame drawn
from the tail.

So the scenario is authored and uncaptured, and the recording will not be fabricated. A hand-written
404 body would test the tool against an invented response shape, and the shapes are exactly the part
most likely to be wrong — this registry answers 401 in several places where an author would
reasonably write 404, which is the whole subject of `prose-only-base`. Writing the fixture by hand
would encode my guess about the registry as the benchmark's ground truth.

`microsoft/WizardLM-2-7B` returning 401 is a verified real datapoint from the same sweep and is
worth its own scenario — Microsoft withdrew the WizardLM-2 models and several published models
declare them as base — but it is a *withdrawn* base under a live namespace, not a freed one. Noted
as `withdrawn-base`, not folded into this scenario.

## The scenario's actual content, which I had wrong at first

My first instinct for a deleted base was `contradicted`. That is wrong, and noticing why sharpened
the scenario considerably.

**Deletion does not contradict lineage.** The derivation may well have happened; the base was
deleted afterwards. Nothing about a repository's present absence bears on whether a training run
consumed it a year ago. The verdict is `unverifiable`.

What deletion establishes is a property of the *reference*: the name is free, anyone can register
it, and a pipeline resolving by name fetches whatever later occupies it. That is the finding, and it
belongs on the component, not in the verdict.

So the scenario pulls in two directions at once — restraint about the relationship, alarm about the
reference — and grades both. The likelier failure is not over-claiming but **omission**: dropping
unreachable nodes is the natural implementation, and it erases the exposure entirely. Added an
`omissions` section to `expected-absent.yaml` for that, since invention's mirror image needed
somewhere to be scored.

## DEC-014, which the sweep caused rather than informed

Once throttled, every request returned 429 — including `Qwen/Qwen2.5-7B` and every other plainly
live repository. **A resolver reading any non-200 as absence would have reported roughly 180 live
models as deleted.** I ran that resolver by hand and briefly believed the output.

That is worse than the 401 ambiguity, on two counts. It is transient, so a tool that caches the
conclusion poisons its own output permanently on the strength of a condition that cleared in
minutes. And it is a different *category*: `unverifiable` is a claim about what the evidence
supports, whereas a rate limit is a fact about the client. Recording "I did not get to look" as "the
evidence does not settle this" is DEC-001's error displaced one level up.

So responses now split three ways. Conclusive and inconclusive may produce a verdict; transient
produces nothing at all — no edge, no verdict, no composition — marks the run partial, names the
unreached references, and exits non-zero.

This is the second time a decision made about the domain model failed to hold automatically at a
boundary. DEC-013 was the serialization boundary; this is the network boundary. The pattern is
worth naming: **DEC-001 has to be re-applied at every edge of the system, and each edge offers its
own way to collapse the third state.** The next boundary is the CLI's exit codes and output
formatting, and I expect the same thing there.

## Open next

- Complete the base-reference sweep with a token, sampled from the download tail rather than the
  head, and capture `deleted-namespace` from a real instance.
- `withdrawn-base` from `microsoft/WizardLM-2-7B` — grounded already, capturable as soon as the
  throttle clears.
- A `transient-failure` scenario for DEC-014 itself. It is the easiest of all of them to capture
  honestly, since a 429 is reproducible on demand.
- The upstream CycloneDX report now has three scenarios' worth of experience behind it, which was
  the threshold set in the last entry. Worth writing.
