# 2026-09-03 — Pinning the schemas, and applying the argument to myself

The smallest item on the list and the one most worth doing, because the repository was doing the
thing it exists to criticise.

## The problem, stated by the file itself

`schema/README.md` shipped in the first commit saying, of the vendored CycloneDX schemas:

> **Not pinned to a commit.** The retrieval is dated but not digest-pinned, which is precisely the
> weakness this project exists to point out in other people's dependency records.

Which is an honest admission and not a defence. A tool whose argument is *a name is an assertion,
a digest is a fact* cannot record its own dependencies by branch name and date. I had written the
criticism into the file rather than fixing it.

## What the pin is

All three blob ids matched upstream `master` exactly at commit `595d98f` (2026-09-02), so the
vendored copies were byte-identical to what the branch pointed at. `PINNED.yaml` now records, per
file, the **git blob id**, the **SHA-256**, and the size, plus the source commit.

Both digests rather than one. The blob id is content-addressed and is the value GitHub reports, so a
pin can be checked against the API without downloading anything — but git's object id is SHA-1
based, and SHA-1 is not collision resistant. Either alone is a weaker claim than both together.

The pin is by **content**, not by commit. A commit says where the bytes were found; a blob id says
what they are. Recording both means the reference survives a force-push, a branch rename, or a
repository move, none of which a `master` URL survives.

## The part that made it worth more than an afternoon

`scripts/verify_pins.py` emits **the project's own three verdicts**: `verified`, `contradicted`,
`unverifiable`. `PINNED.yaml` is a claim about what this repository contains; recomputing the
digests is what turns it into a finding. That is DEC-001 applied to the repository instead of to a
model.

The mapping falls out cleanly and the edge cases are the interesting part:

- Digests match → `verified`.
- Digests differ → `contradicted`, with the specific mismatches named.
- **A recorded file is missing → `unverifiable`, not `contradicted`.** Absence of the artifact is
  not evidence that the recorded digest is wrong. This is the same restraint `deleted-namespace`
  demands about a deleted base, reached from a completely different direction.
- **Upstream unreachable → `unverifiable`, and the exit code is untouched.** DEC-014: a transient
  condition produces no verdict. A network blip must not turn a green run red, or people learn to
  ignore the check.

Tested all three negative paths rather than trusting them. Tampering one byte produces
`contradicted` with the size and both digests reported. Removing a file produces `unverifiable`.
Running `--online` behind a dead proxy produces `unverifiable` for upstream and **exit 0**. A
verifier that has only ever returned `verified` has not been tested, it has been observed.

## What this is really for

It is a demonstration, and a cheap one — three files, one script, an afternoon. But the argument
`whence` makes to a stranger is *your dependency record says things it has not checked*, and the
first question a fair reader asks is whether the repository making that argument checks its own.
Now it does, by the same rules, emitting the same vocabulary, with the same treatment of absence
and the same treatment of transient failure.

DEC-016's open question is the honest limit: `uv.lock` already pins, but nothing emits a verdict
about it in this shape. Worth doing once there are runtime dependencies to lock.

## Open next

- `deleted-namespace`: still needs link-header pagination and an authenticated token. Now the only
  `planned` scenario and the last open item on this repository's list.
- `tearline` and `attestrun` remain unscaffolded. `attestrun` is where the three-valued verdict
  vocabulary eventually moves; this session is the second place it has been implemented by hand,
  which is the usual signal that extraction is close. Not yet — two uses, and the rule is to wait
  for the third.
