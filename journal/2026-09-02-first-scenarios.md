# 2026-09-02 — The first two scenarios, and the two holes they found

Authored `declared-base` and `prose-only-base` against real registry state rather than invented
fixtures. Both recorded and replaying offline.

## Grounding them in real artifacts was worth the effort

The original plan was to construct fixtures. Querying the registry instead produced better
scenarios than I would have designed, because the awkward cases are already out there.

`declared-base` was chosen as the easy one and turned out to contain three complications, all real:
the first-hop base is gated, so metadata and revision are readable while weights are not — a clean
split between resolution and verification; the second-hop base name 307-redirects, so the declared
name and the resolved name differ; and **no edge in it is `verified`**. Every lineage claim is a
bare name in card metadata with no revision attached.

That last point is the one worth carrying forward. It generalises: almost nothing on this registry
pins its base by digest, so `verified-by-digest` is expected to be rare in practice and phase one
will emit `unverifiable` for essentially every `derives-from` edge. That sounds like a weak result
and is actually the contribution — the transcription tools this replaces imply verification they
never performed.

`prose-only-base` came out sharper than intended. `mistralai/Mistral-7B-Instruct-v0.2` declares no
`base_model` in frontmatter; its README says in prose that it is a fine-tune of "Mistral-7B-v0.2",
unqualified; and the obvious qualification answers **401, not 404**. Unauthenticated, that response
cannot distinguish "no such repository" from "exists and you may not see it". A clean 404 would have
been a worse test — here the honest answer is genuinely unavailable rather than merely negative.

It also ships a decoy for free: the frontmatter carries `new_version:` pointing at v0.3, which is a
successor pointer that a naive resolver reads as ancestry with the arrow reversed. And v0.1 exists,
one character from the name in the prose, as the nearest-version trap.

So the negative set for that scenario carries more weight than the positive one, which holds a
single `requires-package` edge. Three plausible shortcuts to a confident answer, all wrong. The
subtlest is concluding the repository does not exist on the strength of a 401 — recorded as a
negative *assertion* rather than an edge, because a run can emit a perfect edge list and still fail
by saying that in prose.

## Two holes in the data model, both found by authoring rather than by reading

This is the argument for writing truth sets before code, and it paid immediately.

**DEC-011.** `Edge` had one `target` field, so the second-hop redirect had nowhere to record what
the author actually wrote. Following a registry-issued 307 is resolution rather than inference, so
DEC-010 permits it — but discarding the declared name removes the evidence a reader needs to notice
a rename, and a rename is one of the ways a name stops meaning what it meant. Added `declared_as`,
populated only when it differs from `target`; populating it unconditionally would make a rename
indistinguishable from a direct hit.

**DEC-012.** `prose-only-base` requires a sentence from a model card to reach the output, because
without the quoted prose an `unresolvable` edge is an assertion with nothing behind it and the
refusal cannot be audited. But a model card is content published by anyone with an account. The two
requirements are only compatible if the excerpt is treated as data at every point: bounded,
delimited where rendered with delimiters inside it neutralized, never in a log record, never parsed
for meaning. Also added `excerpt_truncated`, because a silently shortened quote is a misquote.

Neither hole was visible from the design documents. Both were unavoidable the moment a real
artifact had to be described.

## Open next

- A third scenario, `deleted-namespace`, is the direct test of DEC-002 and is the one with real
  external stakes. It needs an artifact whose declared base's owning account no longer exists.
  Finding a stable example is the work; a live one may have to be reconstructed from a recording
  rather than captured fresh.
- ~~DEC-003 still does not say which CycloneDX extension points carry provenance class, verdict,
  and now `declared_as`.~~ Settled the same day as DEC-013; see the following journal entry.
- Whether a redirected reference deserves a weaker verdict than a direct hit is still open
  (recorded in `declared-base/scenario.md`). Leaning yes, but not on the strength of one example.
