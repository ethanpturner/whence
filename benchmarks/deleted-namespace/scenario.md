# deleted-namespace

**What this measures.** That a dangling lineage reference survives into the output, carries the
right verdict, and is flagged as re-registrable — and that the flag is not applied to references
that merely fail.

**Subject.** `bartowski/AvelonLabs_OpenClaude-1.7B-Merged-GGUF`, which declares
`AvelonLabs/OpenClaude-1.7B-Merged` as its quantization base. Neither an organization nor a user
holds `AvelonLabs`. The name is free.

## The premise I authored this on was wrong

The original version assumed a deleted repository returns 404. It does not:

| Request | `deleted-namespace` | `withdrawn-base` |
|---|---|---|
| declared base | **401** | **401** |
| body | `{"error":"Invalid username or password."}` | *identical* |
| owning organization | **404** | 200 |
| owning user | **404** | — |
| name is re-registrable | **yes** | no |

**The two are indistinguishable at the model endpoint, down to the body text.** Everything that
separates a dead end from a hijack opportunity is in the namespace lookups. That makes the extra
request load-bearing rather than tidy, which is a stronger justification than the one the scenario
was written with.

## The distinction the scenario enforces

Deletion does not contradict the lineage. The quantization may well have happened and the source
was removed afterwards; nothing about a namespace's present state bears on whether a derivation
occurred a year ago. The verdict stays `unverifiable`.

What deletion establishes is a property of the *reference*: the name is free, anyone may register
it, and a pipeline resolving by name fetches whatever later occupies it. That belongs on the node.

So the scenario demands restraint about the relationship and alarm about the reference, and grades
both. The likelier failure is **omission** — dropping unreachable nodes is the natural
implementation and erases the exposure entirely.

## What finding it exposed in the resolver

The sweep that found this subject also found `360kaUser`: organization 404, **user 200**. A
namespace here may be owned by an organization or a person, and the resolver was consulting only
the organization endpoint.

Every user-owned namespace would therefore have been reported as free — an invented hijack finding
against a live owner who had done nothing wrong. That is the most damaging false positive this tool
can produce, because it accuses somebody of having abandoned a name they still hold, and it would
have fired constantly.

Fixed, and the user endpoint is consulted only when the organization lookup is negative, so a held
organization costs no extra request.

## How it was found

45,000 models by download rank yielded 11,189 base references across 3,323 namespaces. 1,573 never
appeared as a live author; 444 were checkable before the registry throttled the source address, and
15 of those had no public models. Of the 15, exactly one — `AvelonLabs` — had neither an
organization nor a user.

The earlier 22,000-model sweep found none, which is why this scenario carried `status: unobserved`
for a day. It is rare in the download-ranked head, and it is not absent.

## Pass condition

The base edge present with relation `quantized-from`, provenance `asserted-by-card`, verdict
`unverifiable`; the base node unpinned, unreachable, `namespace-state: free`, carrying
`risk: reregistrable-reference`; both dataset edges recovered; no `contradicted` verdict; and
nothing from `expected-absent.yaml`, including its omissions.
