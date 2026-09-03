# Not captured

No recording exists for this scenario. Capturing it requires a real artifact whose declared base
repository returns 404 *and* whose declared base namespace also returns 404, and no such instance
was found in the sample that could be checked (see `../scenario.md`).

The recording must not be fabricated. A hand-written 404 body would test the tool against an
invented response shape, and the shapes are the part most likely to be wrong — the registry
returns 401 in several situations where a naive author would write 404, which is the entire
subject of the sibling `prose-only-base` scenario.

When a candidate is found, capture the repository response, the namespace response, and the
referring model's metadata, then flip `status` to `recorded` in `benchmarks/scenarios.yaml`.
