# whence

**Status: retired, 2026-09-11.** Development has stopped. The code runs, the eleven recorded
scenarios replay offline, and the four measurement pages under `docs/eval/` are reproducible from
the recordings committed beside them. No new features are planned and issues will not be worked.
The reasoning is DEC-032 in `docs/architecture/decision-log.md`, and the rest of this file is the
postmortem.

## What it did

`whence` resolved the dependency graph of a published machine-learning model and recorded, for every
edge, whether the relationship was **claimed** by the publisher or **established** by something.

Nodes pinned to a revision digest rather than a name, because a name is an assertion about the
present and a digest is a fact. Every edge carried a provenance class. Every verdict was one of
three — `verified`, `contradicted`, `unverifiable` — and an edge that could not be resolved was
`unverifiable`, never reported as absent. Output was a CycloneDX 1.7 ML-BOM.

It resolved from card metadata, followed redirects while recording what a name was declared as,
classified dangling namespaces, detected OpenSSF Model Signing bundles without claiming they were
valid, compared five transformer-body fields against a declared base as a check that could only
refute, and read an external weight-fingerprint verdict as evidence under a mapping the evidence
file declared.

```
uv run whence resolve nvidia/Llama-3.1-Nemotron-70B-Instruct-HF \
    --scenario benchmarks/declared-base --bom
uv run whence evaluate          # eleven recorded scenarios, scored against their truth sets, offline
```

## What it measured

Four pages, each replaying offline from recordings captured live and committed beside the results.

### The structural check, against a labelled dataset

[`docs/eval/lineagebench.md`](docs/eval/lineagebench.md). DEC-020's five-field body comparison can
only contradict a claim. Its false-positive rate had been measured at 0 over 33 comparable real
declared fine-tunes; its detection rate had not, because no mistaken declaration had been found in
the wild.

Run against `lineagebench` (15 suspects, 8 candidate parents, 13 documented derivations, 107
constructed negatives):

| Pool | n | Contradicted | Compatible | Configuration unavailable |
|---|---:|---:|---:|---:|
| Positive | 13 | **0** | 7 | 6 |
| Negative | 107 | **28** | 2 | 77 |
| Limitation cases | 2 | 1 | 1 | 0 |

**0 contradictions over the 7 comparable positives**, bringing the check to no false contradiction
over 40 comparable real derivations. **28 contradictions over the 30 negatives it could reach.**
Seven of the 23 models are gated and answer 401 without credentials, which accounts for 77 of the
107 negatives and 6 of the 13 positives; a pair the check could not read is reported apart from a
pair it read and missed.

The two negatives it did not contradict are the case DEC-020 said it could not separate, now
observed rather than argued: a Llama-3-8B fine-tune against the two Mistral-7B bases, identical on
all five fields — hidden size 4096, 32 layers, 32 heads, 8 key-value heads, intermediate size 14336.

### Weight fingerprints as evidence

[`docs/eval/fingerprints.md`](docs/eval/fingerprints.md). The first end-to-end run of the DEC-029
evidence path, with modelDNA 0.1.0 and Cisco Model Provenance Kit 1.1.0 run as separate processes.

modelDNA over the 39 pairs the structural check could compare: **7 of 7 comparable positives
returned a positive class** at p ≥ 0.9796, and **30 of 30 negatives returned an abstaining class**.
Applied to fifteen resolutions, its verdicts **moved five declared edges from `unverifiable` to
`verified`**, **created one edge** that no card declared (a verified grandparent beside two asserted
hops), abstained on 28, and **attached to nothing once** — a real verdict about an artifact the
depth-2 resolution never reached, reported as unattached rather than used to extend the graph.

The Cisco kit established nothing, and the reason is the finding. Its `Confirmed Match` is not a
weight verdict: the kit sets the pipeline score to 1.0 or 0.9 when an architecture or family *hash*
matches, **before any weight is compared** (`core/lookup.py`, MFI tiers 1 and 2). That is a metadata
match, which DEC-020 already treats as necessary and not sufficient, so the evidence file maps it to
`abstains`. On one suspect it returned a high-confidence match to an unrelated architecture.

### The 2024 census, re-checked

[`docs/eval/census.md`](docs/eval/census.md). Stalnaker et al. found 2,501 base-model declarations
pointing at identifiers the registry did not serve. Two years later, **1,166 of those names are
still dead, and none answers 404** — every one answers 401, which does not distinguish a deleted
repository from a private one.

Behind them sit **516 namespaces**:

| State | Namespaces | Names | Declarations |
|---|---:|---:|---:|
| `held` | 434 | 1,000 | 1,821 |
| `held-empty` | 25 | 32 | 43 |
| **`free`** | **57** | **134** | **258** |

**134 declared base names, carrying 258 declarations from models that still exist, point into 57
namespaces nobody holds** and anyone may register. One is declared as a base by 25 models. The rate
is **about 1 in 9**, against **1 in 220** across all base references in the download-ranked head.
A dead reference is an order of magnitude more likely than a live one to be re-registrable, which
is now measured rather than argued. The classifier produced no `unknown` over 516 namespaces it had
never seen.

### What the published signatures bind

[`docs/eval/signatures.md`](docs/eval/signatures.md). Of the **45,000** most downloaded models,
**64 carry a `model.sig`** — about 1 in 700.

| Gap | Result |
|---|---|
| Does the signature verify | **63 of 64** parse and verify; 1 carries its certificate in a deprecated field |
| Whose identity it binds | 56 `matches`, **7 `does-not-match`**, 1 `undeterminable` |
| Which files it covers | 53 complete, **9** leave present files unsigned, **6** name files the repository no longer holds |

**The seven that verify and bind the wrong publisher are the finding.** All seven carry IBM's
signing identity under namespaces that are not IBM's — three requantisations, three re-uploads, one
modification of a re-upload. Every one verifies cryptographically. Three are byte-identical to
another bundle in the sweep, so the mechanism is visible: the bundle travelled with the model when
it was copied. A tool reporting `valid` on presence would be wrong about at least seven of 64, and
wrong in the direction that matters — a valid signature from a publisher you trust, over bytes that
publisher never signed.

One case name coverage cannot see is worse: a requantisation whose copied bundle names twelve files
and whose repository holds twelve files with those names. Only the digests separate them, and
checking digests means downloading weights, which is the boundary DEC-005 kept this tool on the near
side of.

## Why `unverifiable` was the correct answer, and why it made the tool unadoptable

From card metadata alone, almost every edge is `unverifiable`. Cards name a base and stop; scarcely
anything on the registry pins a base by digest. So the strongest thing resolution establishes is
that the named artifact exists and can be pinned — not that the derivation happened. Reporting such
an edge as verified would assert a check nobody performed, and that is the error the whole project
was built to refuse.

The answer was right and it was also the product. A tool whose principal output is "nobody has
established this" gives an operator nothing to act on. The three-valued verdict survives as an input
to someone else's decision and dies as a deliverable, and `whence` shipped it as the deliverable.

That is not an argument for reporting `verified` where nothing was verified. It is an argument that
the honest verdict needed a consumer, and no consumer existed.

## What changed in 2026

The central question — did this artifact come from the one it names — became answerable by reading
weights. modelDNA and Cisco's Model Provenance Kit both shipped with published measurements.
`docs/eval/fingerprints.md` measures them, and modelDNA in particular does the thing `whence` was
designed around being unable to do.

DEC-029 admits that evidence, and admitting it was right. It also settles what `whence` is: not the
layer that answers the question.

Meanwhile the consuming half of the ecosystem did not arrive. No tool was found that reads an AI-BOM
to make a decision. The CycloneDX reference generator for this artifact class has been unmaintained
since 2024 and the schema is being rewritten for 2.0. `sigstore/model-transparency` has three usages
across GitHub code search and no release since 2025-10. SLSA has no track for models.

## What remains unduplicated, and why that was not enough

Three things in this repository were not found elsewhere:

- **Claimed-versus-established bookkeeping per edge.** A card's assertion and a verifier's verdict
  kept as two records rather than collapsed into one.
- **Namespace-transfer detection.** Following a redirect and recording what a name was declared as,
  so a base that now resolves into an organization controlled by someone else is visible.
- **`free` / `held-empty` / `held` classification** of the namespace behind a dead reference, which
  separates a dead end from a hijack opportunity.

Each is real. None justified a tool. The namespace hazard's remedy is one line in a loader — pin by
revision digest — and a check for it belongs inside a dependency scanner someone already runs. The
bookkeeping is a schema decision, not a product. The measurement of each is the contribution, and
the measurements are above.

## If you have this problem today

- **Pin by revision digest, not by name.** Every loader in this ecosystem accepts a revision. A name
  is re-registrable; the census measures how often. This is the single change that removes the
  hazard this project was built around.
- **To establish that an artifact derives from another, read the weights.** modelDNA and Cisco's
  Model Provenance Kit are the shipped options; `docs/eval/fingerprints.md` is an independent
  measurement of both, including the Cisco scoring behaviour that is easy to misread.
- **Do not treat a present signature as a valid one, or a valid one as the publisher's.**
  `docs/eval/signatures.md` gives the rates for all three gaps.
- **Do not treat a card's `base_model` as verified provenance.** It is a claim, and 2,501 of them
  pointed nowhere as of 2024, of which 1,166 still do.

## Scope and lineage

`docs/architecture/project-scope.md` holds the scope and non-goals;
`docs/architecture/decision-log.md` holds thirty-two decisions and the reasoning behind each, ending
with the retirement.

The claimed-versus-verified distinction is inherited from [`trace`](https://github.com/ethanpturner/trace),
recorded there as DEC-009: a finding means evidence supports a weakness, a documentation gap means
it could not be determined whether a control exists, and collapsing the two is the failure that work
exists to avoid. `whence` applied the rule to provenance.
[`tearline`](https://github.com/ethanpturner/tearline) applies it to retrieval entitlements and
[`attestrun`](https://github.com/ethanpturner/attestrun) to evaluation results.
