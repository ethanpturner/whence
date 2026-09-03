# Benchmarks

Scenario layout and the truth-set rules are specified in
`docs/architecture/evaluation-plan.md`. Two things matter most and are repeated here because
they are the ones easiest to violate by accident:

**Nothing under a scenario's `expected/` is supplied to the tool during a run.** If it were, the
benchmark would measure nothing.

**The three expected files are not interchangeable.** `expected-graph.yaml` holds edges that exist
and should be found. `expected-absent.yaml` holds relationships that do not exist, and scores
invention. `expected-unresolvable.yaml` holds edges that exist but cannot be established from
available metadata — a tool that confidently resolves one of these is wrong even though the edge
is real.

`scenarios.yaml` is the authoritative list. A scenario directory that is not registered there is
not part of the benchmark set.
