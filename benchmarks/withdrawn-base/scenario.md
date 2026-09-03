# withdrawn-base

**What this measures.** That an inaccessible base is recorded as a dead end without being mistaken
for a hijack opportunity, a refuted derivation, or a problem with the tool's own credentials.

**Subject.** `MaziyarPanahi/WizardLM-2-7B-GGUF` at revision
`491e4644eb4874621cb7d00153a20e0bf7358fb8`, 157,179 downloads at capture. It declares
`microsoft/WizardLM-2-7B` as its base; Microsoft withdrew the WizardLM-2 models, and the repository
now answers 401.

## Why this exists alongside `deleted-namespace`

The two scenarios look alike and grade opposite behaviours. Both have an unreachable base. The
difference is who controls the name.

| | `deleted-namespace` | `withdrawn-base` |
|---|---|---|
| Base repository | absent | access denied |
| Owning namespace | absent — **free** | resolves — **held** |
| `whence:risk` | `reregistrable-reference` | **must not be set** |
| Could another caller resolve it? | No | Possibly, with credentials |

A tool that flags every unreachable node as re-registrable turns a real supply-chain signal into
noise, and the flag in `deleted-namespace` stops meaning anything. Distinguishing them costs one
extra request — resolve the namespace, not just the repository — and that request is the entire
difference between "this dependency is gone" and "anyone can become this dependency."

## The trap

The 401 body is `{"error":"Invalid username or password."}`.

That message describes a client credential problem. The situation is a withdrawn repository, and
the request carried no credentials to be invalid in the first place. A tool that believes the prose
does one of three things, all wrong: aborts the run as misconfigured; retries with backoff; or
classifies the response as transient under DEC-014 and marks the whole traversal partial.

The rule the scenario enforces: **response class is determined by the status code, not by the prose
in the body.** A registry's error strings are written for humans debugging their own scripts, and
they describe the most common cause rather than the actual one. Reading them as ground truth
imports the registry's guess about the caller into the tool's model of the world.

This is also why DEC-014's transient class is defined by status code and transport outcome rather
than by anything semantic.

## What it also caught

Selecting this subject surfaced a gap in the `Relation` enum. The registry declares the derivation
qualifier — `base_model:quantized:microsoft/WizardLM-2-7B` — and the vocabulary had no term for
quantization, so the relation would have flattened to `derives-from`.

That is not a rare corner. Across 3,206 `base_model:` tags harvested from the top 4,000 models by
download, **quantization is the most commonly declared derivation at 1,030, roughly twice
fine-tuning's 507**, with adapters at 39 and merges at 27. The most common real relation in this
ecosystem had no name in the model. Fixed in DEC-015.

It matters beyond bookkeeping: quantized lineage is the case weight-level comparison is expected to
handle worst (DEC-005), so an edge that records the qualifier tells phase two in advance where its
method is weak. Flattening throws that away.

## Pass condition

Both expected edges recovered with `quantized-from` on the first; the base node present, unpinned,
unreachable, `namespace-state: held`; **no** `whence:risk` property; no `contradicted` verdict; a
`compositions` entry of `unknown` scoped to the base; and no statement anywhere that the run failed
for credential reasons.
