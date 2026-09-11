# What the published `model.sig` bundles bind, and to whom

**Measured:** 2026-09-10, over the 45,000 most downloaded models on `huggingface.co`, swept with
`GET /api/models?sort=downloads&limit=1000&expand[]=siblings` (45 pages). Recording under
`docs/eval/signatures/recorded/` (198 interactions), results in
`docs/eval/signatures/results.json`, script `scripts/measure_signatures.py`. Cryptographic
verification in `docs/eval/signatures/tools/verify_bundles.py`, run separately with
sigstore-python 4.5.0; its output is `docs/eval/signatures/verification.json`. Every figure below
replays offline from those files, and `tests/unit/test_signatures_measurement.py` pins them.

## What was measured

DEC-021 detects an OMS bundle and reports it `unverifiable`, never `valid`, on the argument that
presence establishes that somebody signed something and not that the signature verifies, that it
covers the files in front of you, or that the identity it binds is the publisher's. Those are three
separate gaps, and each was measured on every bundle the sweep found.

`whence` itself is unchanged by this page: it still reports every one of these bundles
`unverifiable` (`detection: unverifiable=64` in the results), because it still has no identity
policy to verify against. What follows is what such a policy would face.

## Coverage first

| | Models |
|---|---:|
| Swept | 45,000 |
| Carrying `model.sig` | 64 |
| Publishing namespaces | 5 (`ibm-granite` 56, `cyankiwi` 3, `unsloth` 3, `huihui-ai` 1, `openai` 1) |

DEC-021's figure of 63 was measured on 2026-09-03; one model was signed or entered the head in the
week between. The rate is still about 1 in 700.

## Gap one: does the signature verify

| | Bundles |
|---|---:|
| Parse as a Sigstore bundle and verify (certificate chain, Rekor inclusion proof, DSSE signature) | **63** |
| Refused by sigstore-python | 1 |

The refused bundle, `ibm-granite/granite-timeseries-patchtst-fm-r2`, carries its certificate in the
deprecated `x509CertificateChain` field of a v0.3 bundle rather than in `certificate`; the library
reports "expected certificate in bundle". It also signs a `digicert-root.pem` the repository no
longer holds. Whether an older client accepts it was not tested. All 64 bundles carry the predicate
`https://model_signing/signature/v1.0` and the v0.3 media type.

Verification here is bundle-only. Nothing was downloaded, so nothing establishes that the signed
digests match the files the registry serves today. That is the third gap.

## Gap two: whose identity it binds

The signing identity is the certificate's subject alternative name and its OIDC issuer:

| Signer | Issuer | Bundles |
|---|---|---:|
| `Granite-sign@ibm.com` | `https://sigstore.verify.ibm.com/oauth2` | 48 |
| `Granite-verify@ibm.com` | same | 13 |
| `Granite.Preview@ibm.com` | same | 1 |
| an individual's e-mail at `openai.com` | `https://github.com/login/oauth` | 1 |
| none readable | — | 1 |

Matched against the publishing namespace under the rule stated in the script (the e-mail domain's
second-level label must be one of the namespace's tokens):

| Identity | Bundles |
|---|---:|
| `matches` | 56 |
| `does-not-match` | **7** |
| `undeterminable` | 1 |

**The seven are IBM's signature under someone else's namespace**: three `cyankiwi/*-AWQ-INT4`
requantisations, three `unsloth/*` re-uploads, and one `huihui-ai/*-abliterated` modification of an
`unsloth` copy. Every one verifies cryptographically. Every one binds `ibm.com`. None of the three
publishing namespaces is IBM. This is the class DEC-021 named and could not count: a signature that
is valid, and is not the publisher's.

Three of the seven are byte-identical to another bundle in the sweep, so the mechanism is visible:
the `model.sig` was copied along with the model. `cyankiwi/granite-4.1-3b-AWQ-INT4` carries
`ibm-granite/granite-4.1-3b`'s bundle, `huihui-ai/Huihui-granite-4.1-3b-abliterated` carries
`unsloth/granite-4.1-3b`'s, and `cyankiwi/granite-4.1-8b-AWQ-INT4` carries `unsloth/granite-4.1-8b`'s
— a copy of a copy. The other four share no bundle in the sweep; the likeliest reading is that the
upstream re-signed after the copy was taken, and it is a reading, not a measurement.

The rule's weakness is on the other side. `openai/privacy-filter` is signed by a named individual
through GitHub's OIDC issuer, and the rule calls that a match because the e-mail domain is
`openai.com`. A policy that accepts a namespace's employees is a policy, and this page is not
proposing one.

## Gap three: which files it covers

Name coverage, from the bundle's `predicate.resources[]` against the repository's current file
list, with `model.sig` and git paths excluded (the signer skips them by default):

| | Models |
|---|---:|
| Every present file signed and every signed file present | 53 |
| Present files the bundle does not name | 9 |
| Signed files the repository no longer holds | 6 |

Four cases carry the finding:

- **`openai/privacy-filter`**: 4 files signed, 23 present. The bundle's subject is the
  `original/` directory and it names that directory's four files; the repository adds top-level
  copies of three of them, thirteen ONNX files, the tokenizer and its configuration, and the
  README, none signed. The
  signed weights are in the repository; the weights a default loader picks up are not the signed
  ones.
- **`ibm-granite/granite-speech-4.1-2b-nar`**: the bundle names `configuration_nle.py`,
  `modeling_nle.py`, and six more; the repository holds `configuration_granite_speech_nar.py` and
  its siblings instead. The files were renamed after signing, on the publisher's own repository, and
  the signature is stale.
- **`cyankiwi/granite-4.1-3b-AWQ-INT4`**: the copied IBM bundle names two sharded safetensors
  and an index; the repository holds a single `model.safetensors`. Here the copy is visible by names
  alone.
- **`cyankiwi/granite-4.1-30b-AWQ-INT4`**: 22 files signed, 16 present, twelve shards named and
  four held. Same shape.

The case name coverage cannot see is the important one. `cyankiwi/granite-4.1-3b-AWQ-INT4`'s
bundle names twelve files and the repository holds twelve files with those names — so a check that
compared names would pass a requantisation against the original's signature. Only the digests can
separate them, and checking digests means downloading the weights, which is the boundary DEC-005
keeps this tool on the near side of.

## What this changes

Nothing in the tool, and one sentence in how DEC-021 is read. "A present bundle is `unverifiable`"
was argued from what presence fails to establish. It is now measured: of 64 published bundles, 7
verify and bind an identity that is not the publisher's, 9 leave present files unsigned, 6 name
files that are gone, and 1 does not parse in the current reference verifier. The verdict a tool
would report by trusting presence is wrong for at least 7 of 64, and the identity policy DEC-021
defers has its first real inputs: an issuer and subject to accept, per namespace, and a copy to
refuse.
