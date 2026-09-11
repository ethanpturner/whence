# 2026-09-10 — Valid, and not the publisher's

Three measurements and one decision, all on the registry-integrity layer that DEC-029 said is the
tool's distinct contribution. Two years of a census re-checked, the 64 signed models verified, and
the most common malformed declaration on the registry given a scenario.

## The signatures

DEC-021 argued that a present `model.sig` establishes that somebody signed something and nothing
more, and reports it `unverifiable`. The argument had no numbers behind it. Now it does.

Of the 45,000 most downloaded models, 64 carry a bundle. 63 verify cryptographically under
sigstore-python: certificate chain, Rekor inclusion proof, DSSE signature, all good. The one that
does not carries its certificate in the deprecated `x509CertificateChain` field.

Then the identity. 62 of the 63 bind an `@ibm.com` signer through IBM's own OIDC issuer. Only 56
of the 64 models are published by `ibm-granite`. **Seven verified bundles sit under `cyankiwi`,
`unsloth`, and `huihui-ai`, and all seven bind IBM.** Three are byte-identical to another bundle in
the sweep, so the mechanism is not in doubt: the `model.sig` travelled with the model when it was
re-uploaded, requantised, or abliterated. A tool that reported `valid` on presence would have been
wrong about seven of 64, and wrong in the direction that matters — a valid signature from a
publisher you trust, on bytes that publisher never signed.

The case I did not expect was the one name-coverage cannot see. `cyankiwi/granite-4.1-3b-AWQ-INT4`
carries `ibm-granite/granite-4.1-3b`'s bundle, and its repository holds twelve files with exactly
the twelve names the bundle signs. A requantisation keeps the file names. Only the digests separate
them, and checking digests means downloading weights, which is the line DEC-005 keeps this tool
behind. So the measurement says precisely where the tool's reach ends: it can tell you the
signature is a copy when the copy is byte-identical to a bundle it has seen, and it cannot tell
you the weights are not the signed ones.

Two more shapes on the publishers' own repositories: `openai/privacy-filter` signs the
`original/` directory and ships thirteen unsigned ONNX exports and top-level copies beside it, so
the weights a default loader picks up are not the signed ones; `ibm-granite/granite-speech-4.1-2b-nar`
renamed eight files after signing and its bundle now names files the repository does not hold.
Stale on the publisher's own repository, valid all the same.

`whence` is unchanged by this. It still says `unverifiable` about every one of the 64, because it
still has no identity policy. What changed is that the policy DEC-021 deferred has inputs: an
issuer and a subject to accept per namespace, and a byte-identical copy to refuse.

## The self-cycle

Stalnaker et al. counted 675 models in 760,460 declaring themselves as their own base. The sweep
found 64 in the top 45,000. That is more than a freed namespace and more than a cross-namespace
redirect, and the resolver handled it by accident: the `expanded` set stopped the loop, but it
still spent a request re-listing the root and nothing marked the edge. The natural fix — drop the
edge as noise — is the wrong one, because it turns "this card's lineage field is unusable" into
"this card declares no lineage", and those are different statements.

DEC-031: record the edge from the node to itself, flag the node, make no request. Eleven scenarios
now; `self-declared-base` records `nmthien/vietnamese-gpt2`, one interaction, because the
self-reference is recognised before anything is asked.

## The census

Stalnaker et al. found 1,371 base-model identifiers dead in July 2024 (1,377 distinct declared
strings in their cleaned data). The replication package is on GitHub, the names are in it, and
`whence`'s namespace classifier is the question their census could not ask. So I ran it: 1,197
well-formed names, 2,229 registry interactions over forty minutes under the anonymous limit, none
throttled.

No name answers 404. All 1,166 still-dead names answer 401 — the registry has not started
distinguishing deleted from private at the model endpoint in two years, so the namespace lookups
are still the only signal. Behind those names: 434 namespaces held, 25 held and empty, and **57
free**. 134 names, 258 declarations from models that exist today, point into namespaces nobody
holds. `KT-AI/midm-bitext-S-7B-inst-v1` alone is declared by 25 models and `KT-AI` answers 404 at
both the organization and the user endpoint. That is `deleted-namespace` twenty-five times over,
and it was found by taking somebody else's list of broken things and asking one more question.

One in nine dead references sits in a free namespace, against one in 220 across all base
references. The two populations differ and the page says so. What I wanted from the census was a
denominator that was not mine, and that is what it gives.

The recording caught one bug of its own. Two dead names sit in namespaces that differ only in
case, `OpenAI` and `openai`, and the recorder named body files after the request path — so on a
case-insensitive filesystem the second listing overwrote the first, and the replay reported
`OpenAI` as `held` from `openai`'s models. The live numbers were right and the replay disagreed
with them by one namespace, which is exactly what the replay test exists to catch. File names now
carry a digest of the exact path.

Two of the 26 names that resolve again were created after the census, under the same namespace
that declared them. Whether the same person re-created them the registry does not say, and neither
does the page.

## What is open

- An identity policy for DEC-021, now that there is something to write it against. The seven
  copied bundles are the negative set it needs.
- The gated models in lineagebench (seven, 401 unauthenticated) and the census namespaces the
  anonymous budget did not reach. A token would finish both.
- `x509CertificateChain` bundles: whether an older verifier accepts them, and whether `whence`'s
  detector should name the deprecated field.
