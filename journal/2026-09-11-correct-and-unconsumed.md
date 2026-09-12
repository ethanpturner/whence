# 2026-09-11 — Correct, and unconsumed

`whence` is retired. Not abandoned mid-defect and not deprecated in favour of a rewrite: retired
with every gate green, eleven scenarios replaying, and four measurement pages reproducible from
their recordings. DEC-032 is the entry; this is why it reads the way it does.

## Two findings, kept apart

The temptation in a retirement note is to write one narrative, and the honest version needs two.

The tool is correct. `docs/eval/lineagebench.md` finally measured the structural check's detection
rate, which had been the acknowledged hole since DEC-020: 28 contradictions over the 30 negatives it
could reach, and 0 false contradictions over the 7 comparable positives, bringing it to 0 over 40
comparable real derivations. `docs/eval/fingerprints.md` ran DEC-029's evidence path end to end and
every branch behaved as specified, including the branch nobody wants to exercise — a verdict about an
artifact outside the resolved graph, reported as unattached rather than used to extend it. Nothing in
the design failed.

The market is absent. That evidence is not in this repository and could never have been: it is the
absence of a consumer. No tool reads an AI-BOM to make a decision. The CycloneDX reference generator
for this artifact class has been unmaintained since 2024 with the schema mid-rewrite. The reference
implementation of the signing format this tool detects has three usages across GitHub code search
and no release since 2025-10. SLSA has no model track.

Writing those as one finding would say the tool failed, and it did not. Writing only the first would
be a project that limps on. The entry states them separately and the README does the same.

## The close call

Narrowing to the registry-integrity layer was the option I spent longest on, because
`docs/eval/census.md` is the strongest thing here. The classifier ran over 516 namespaces it had
never seen, behind names a 2024 census found dead, and produced 57 `free` with no `unknown`. 134
names carrying 258 declarations from live models point into namespaces anyone may register — 1 in 9,
against 1 in 220 across all base references.

That is a real hazard at a measured rate, and it is still not a product. The remedy is one line in a
loader: pin by revision digest. A check for the hazard belongs inside a dependency scanner somebody
already runs, not in a resolver they would have to adopt. The measurement is the contribution. A tool
wrapped around a rate is a wrapper.

## What the retirement is for

`unverifiable` was the right answer and it was also the thing that made the tool unadoptable, and
those are not in tension. From card metadata almost every edge is unverifiable, because cards name a
base and stop. Reporting such an edge as verified asserts a check nobody performed. But an operator
handed "nobody has established this" has nothing to act on. The three-valued verdict survives as an
input to someone else's decision and dies as a deliverable, and this tool shipped it as the
deliverable.

That is the sentence I want a reader to take, and it is why the code stays runnable rather than being
archived into a tarball. The four `docs/eval/` pages are the durable artifacts; the code is what
produced them, kept working for as long as it keeps working without effort. When a dependency
eventually moves and the build breaks, the recordings and the `results.json` files will still be
there, and they are the part that was worth writing down.

## Open

The identity-policy question DEC-021 deferred now has real inputs — seven bundles that verify and
bind a non-publisher identity — and no tool behind it. And the free-namespace rate is the one figure
here that moves on its own, with nothing watching it.
