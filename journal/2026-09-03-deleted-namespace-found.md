# 2026-09-03 — Finding the case, and the false positive it prevented

`deleted-namespace` is `recorded`. It also exposed a bug that would have accused real people of
abandoning names they still hold.

## Found, at a rate that explains the earlier miss

45,000 models by download rank: 11,189 base references across 3,323 namespaces, 1,573 never seen as
a live author, 444 checkable before the source address was throttled, 15 with no public models —
and exactly **one** with neither an organization nor a user. `AvelonLabs`.

The earlier 22,000-model sweep found none, which is why the scenario sat at `status: unobserved`
for a day. That status was right at the time and the conclusion drawn from it was too strong: rare
in the download-ranked head is not absent.

## The premise was wrong

I authored the scenario assuming a deleted repository 404s. It does not. `AvelonLabs`'s base returns
**401** — the same status as `withdrawn-base`, with the *same body text*, `{"error":"Invalid
username or password."}`.

So the two scenarios are indistinguishable at the model endpoint, character for character.
Everything separating a dead end from a hijack opportunity is in the namespace lookups.

That is a much better justification for the extra request than the one I originally wrote, which
amounted to thoroughness. It is not thoroughness; it is the only signal there is.

## The bug it prevented

The same sweep surfaced `360kaUser`: organization **404**, user **200**. A namespace here may be
owned by an organization or by a person, and my `_namespace_state` consulted only the organization
endpoint.

Every user-owned namespace would have been reported `free` and flagged `reregistrable-reference`.
That is an invented hijack finding against a live owner who has done nothing — the most damaging
false positive this tool can produce, because it accuses somebody of releasing a name they still
hold, and it would have fired on personal accounts constantly.

Fixed, with the user endpoint consulted only when the organization lookup is negative, so a held
organization costs nothing. Pinned by a test, because the check is one request and its absence is
invisible until it fires against someone real.

Worth noting how it was found: not by review, and not by the six scenarios, all of which happen to
use organization-owned namespaces. It came from looking at the *rejects* of a search for something
else.

## What the corpus now covers

Four shapes that look alike at the model endpoint and mean different things:

| | base status | namespace | meaning |
|---|---|---|---|
| `withdrawn-base` | 401 | held | dead end |
| `deleted-namespace` | 401 | **free** | hijack opportunity |
| `transferred-namespace` | 307 | held, empty | silently serves another owner's bytes |
| `prose-only-base` | 401 | — | reference cannot be constructed at all |

Only the last is `unresolvable` provenance (DEC-018). The middle two differ solely in the namespace
lookups. Any tool that treats a non-200 as one condition collapses all four.

## Open next

- The 1,129 namespaces throttled out of this sweep remain unchecked. A token would finish it, and
  the interesting question is the *rate* — one free namespace in 444 checked is a base rate worth
  reporting, and the denominator is currently too small to state.
