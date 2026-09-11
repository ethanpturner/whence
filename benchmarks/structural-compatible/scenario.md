# structural-compatible

**What this measures.** Phase two's first increment: a true declared derivation whose base has a
compatible transformer body, and the verdict that must *not* follow from that.

**Subject.** `Qwen/Qwen2.5-7B-Instruct`, which declares `Qwen/Qwen2.5-7B` as its base in card
metadata, resolved one hop with `check_structure: true`. Chosen because the derivation is documented
by the publishing organization and both configurations are public, so the check reaches a real
comparison rather than `unverifiable` for want of a file.

## Why the passing case is the scenario

The structural check compares five transformer-body fields — `hidden_size`, `num_hidden_layers`,
`num_attention_heads`, `num_key_value_heads`, `intermediate_size` — and a difference contradicts a
`derives-from` declaration (DEC-020). Here they agree. The recording holds both `config.json`
fetches, including the registry's content redirect on each, because the seam does not follow
redirects itself (DEC-017) and the check takes the hop.

**Agreement establishes nothing further, and `expected-absent.yaml` forbids `verified` for it.**
Every fine-tune of Qwen2.5-7B carries this exact body, so a compatible configuration narrows the
field to "one of many" rather than "this one". The temptation to overclaim is strongest at the
moment the check has just succeeded, and this scenario exists to grade that moment. The verdict
stays `unverifiable`, the edge's provenance stays `asserted-by-card`, and
`expected-unresolvable.yaml` names the derivation itself as the thing still open.

`expected-absent.yaml` also forbids `contradicted`, because the bodies agree and nothing here is
evidence against the declaration.

## Why there is no `structural-mismatch` scenario

The check was scoped by measurement against 45 real declared fine-tunes, and the sample contained
no mistaken declaration, so the contradiction path had no real instance to capture (DEC-020). It is
covered by unit tests with synthetic configurations, and that substitution is stated rather than
hidden. The scenario was renamed from `structural-mismatch` when no mismatch was found. The first
labelled negatives the check has been run against are the `lineagebench` pairs, measured in
`docs/eval/lineagebench.md`; that measurement is not a scenario, because its pairs are the
dataset's and not a resolution of a target.

The recording also carries `Qwen/Qwen2.5-0.5B`'s metadata and configuration, captured in the same
session. It is not on the scored graph.

## Pass condition

Recall of the one expected edge with relation `derives-from`, provenance `asserted-by-card`, and
verdict `unverifiable`; zero edges from `expected-absent.yaml` — in particular no `verified` and no
`contradicted` on the declared edge; and the unresolvable entry for the derivation itself honoured.
