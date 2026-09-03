# Project scope

**Document version:** 0.1
**Status:** Proposed
**Last updated:** 2026-09-02

## 1. Problem

Three things exist in the model supply chain today and none of them composes with the others.

**Signing attests bytes.** The OpenSSF Model Signing (OMS) specification is real and adopted —
NVIDIA has signed every model published to NGC since March 2025 — and the `model-signing` CLI
works. A verified signature proves the file has not been altered since the signer released it. It
says nothing about what the training run did or what the model derives from.

**BOM generation transcribes claims.** The OWASP AIBOM Generator emits CycloneDX from a Hugging
Face model card. What it reports is what the card asserts. There is no resolution of transitive
dependencies, no pinning, and no verification.

**Scanning inspects for known-bad bytes.** ModelScan, picklescan and their successors are
blocklists over serialized formats, and the 2026 literature has caught up with that: ShadowPickle
and SafePickle both exist because the deployed scanners "perform poorly due to a non-exhaustive
blacklist."

Nothing walks a model's actual dependency graph, pins every node to a digest, and records for each
edge whether the relationship was asserted or established.

## 2. What `whence` is designed to do

Given a reference to a published model, resolve its dependency graph and emit a CycloneDX ML-BOM
in which:

- every node carries a **revision digest**, not a name;
- every edge carries a **provenance class** saying how the relationship was established;
- every unresolved edge is marked `unverifiable` and named, rather than omitted.

The graph is designed to span base models (recursively), merge parents, adapters, tokenizers,
datasets, and the loader packages required to instantiate the model.

## 3. Non-goals

These are out of scope by decision, not by deferral.

- **`whence` does not load models and does not execute model code.** No `trust_remote_code`, no
  pickle deserialization, no framework `load` call. It reads metadata and, where a format permits
  it, structural headers. See DEC-007; this is a security property of the tool, not a limitation.
- **It is not a malware scanner.** It does not decide whether an artifact is malicious. ModelScan,
  picklescan and Fickling occupy that space and `whence` is designed to complement them by
  answering a different question.
- **It is not a signing format.** OMS exists and is adopted. `whence` is designed to consume
  signatures where they are present, never to define a competing scheme.
- **It does not resist an adversary actively laundering a model's lineage.** Weight-level
  verification, when it arrives, is scoped to detecting *undeclared or mistaken* lineage. An
  attacker who perturbs weights specifically to defeat a similarity signature is out of scope, and
  any claim the tool makes is bounded accordingly. See DEC-005.
- **It does not assess model quality, capability, bias, or safety.** Provenance only.
- **It is not a hosted service or a registry.** Local, single-user, offline-capable.

## 4. Intended users

An engineer who has been handed a model reference and needs to answer two questions before putting
it into a pipeline: what does this actually depend on, and how much of that am I taking on trust.

## 5. Success condition

The tool is successful if, on a corpus of published models, it recovers substantially more of the
true dependency graph than a model-card transcription does, and if the BOM it emits is sufficient
to answer "am I affected?" for a supply-chain advisory without going back to the network. Neither is measured yet;
`evaluation-plan.md` describes how they would be.

A run that resolves nothing and says so is a correct run. Coverage is not the objective; honest
coverage is.

**Neither criterion is measured yet.** The evaluation plan describes a gold graph, a head-to-head
against a transcription baseline, and an actionability replay; none is built. What runs is
per-scenario scoring against authored truth sets. An earlier version of this section said "Both are
measured", in the present indicative, which was the tense error this project's own working norms
warn about.
