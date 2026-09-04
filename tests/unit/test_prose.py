"""Reading a derivation out of a card's prose, and refusing to read one that is not there.

The pattern is a heuristic over attacker-controlled English, so the tests that matter are the ones
about what it does **not** match. `scripts/measure_prose.py` supplies the numbers: against 91
published cards the first version produced ten claims and all ten named an ordinary English word.
Each of the failures it found is a test below.
"""

from __future__ import annotations

from whence.prose import EXCERPT_LIMIT, find_claims

CARD = """---
library_name: transformers
new_version: mistralai/Mistral-7B-Instruct-v0.3
---

# Model Card

The Mistral-7B-Instruct-v0.2 Large Language Model (LLM) is an instruct fine-tuned version of the
Mistral-7B-v0.2.
"""


def test_a_prose_derivation_is_found_with_its_sentence() -> None:
    claim = find_claims(CARD)[0]
    assert (claim.name, claim.relation) == ("Mistral-7B-v0.2", "derives-from")
    assert "instruct fine-tuned version" in claim.excerpt
    assert not claim.truncated


def test_the_name_is_never_qualified() -> None:
    """DEC-010. Qualifying "Mistral-7B-v0.2" with the obvious owner yields a repository the
    registry answers 401 for -- indistinguishable from absence without credentials. The guess
    would probably be right, and it would still be a guess."""
    assert "/" not in find_claims(CARD)[0].name


def test_an_english_word_is_not_a_model_name() -> None:
    """The measured failure. "this", "specialized" and "Alibaba" each produced a claim before the
    name shape required a digit or a qualifying namespace -- ten claims from 91 cards, all wrong."""
    for sentence in (
        "BERT is a transformers model pretrained and fine-tuned on this corpus.",
        "The model is fine-tuned from specialized datasets.",
        "It was quantized from Alibaba models.",
    ):
        assert find_claims(f"# Card\n\n{sentence}\n") == []


def test_a_table_row_is_not_the_card_s_own_lineage() -> None:
    """Every false positive that survived the name shape came from a markdown table: a quant
    inventory saying a build was "re-quantized from F16", and a model-family table saying a
    *sibling* was fine-tuned from this card's model -- true, with the arrow the other way."""
    table = (
        "# Card\n\n"
        "| file | note |\n|---|---|\n"
        "| `RVN-IQ3_M.gguf` | re-quantized from F16 with a fresh imatrix |\n"
        "| Qwen3-Omni-Captioner | a model fine-tuned from Qwen3-Omni-30B-A3B-Instruct |\n"
    )
    assert find_claims(table) == []


def test_a_code_block_is_a_sample_not_a_declaration() -> None:
    fenced = "# Card\n\n```python\n# fine-tuned from meta-llama/Llama-3.1-8B\nload()\n```\n"
    assert find_claims(fenced) == []


def test_nothing_is_its_own_ancestor() -> None:
    card = "# Card\n\nA model fine-tuned from Qwen3-Omni-30B-A3B-Instruct for captioning.\n"
    assert find_claims(card)
    assert find_claims(card, subject="Qwen/Qwen3-Omni-30B-A3B-Instruct") == []


def test_frontmatter_is_not_read_for_lineage() -> None:
    """`new_version` is a successor pointer -- the arrow runs the other way, and reading it as
    ancestry emits the edge reversed, which `expected-absent.yaml` names as a specific failure."""
    assert all("v0.3" not in c.name for c in find_claims(CARD))


def test_a_long_excerpt_is_cut_and_marked() -> None:
    """DEC-012: bounded, and marked when cut rather than silently shortened. A card is published
    by anyone with an account, and an unbounded excerpt is a wall of text pushed through a BOM."""
    filler = "x" * (EXCERPT_LIMIT * 2)
    card = f"# Card\n\n{filler} fine-tuned from Llama-3.1-8B and more text follows here.\n"
    claim = find_claims(card)[0]
    assert claim.truncated
    assert len(claim.excerpt) <= EXCERPT_LIMIT + 1
    assert claim.excerpt.endswith("…")


def test_the_relation_follows_the_verb() -> None:
    for verb, relation in (
        ("quantized", "quantized-from"),
        ("distilled", "distilled-from"),
        ("fine-tuned", "derives-from"),
    ):
        card = f"# Card\n\nThis model was {verb} from DeepSeek-R1 for speed.\n"
        assert find_claims(card)[0].relation == relation


def test_a_precision_format_is_not_an_ancestor() -> None:
    """Found at 1,091 cards: `--quantized-from--> FP16`. A dtype, not an artifact -- and every
    model has one, so the claim is empty as well as wrong. Systematic rather than incidental,
    because naming the source precision is how a quantization card is normally written."""
    for sentence in (
        "This model is quantized from FP16.",
        "Quantized from the BF16 weights published upstream.",
        "Requantizations of a Q5_K_M quant of a trending 70b model.",
        "Distilled from an E4M3 checkpoint.",
    ):
        assert find_claims(f"# Card\n\n{sentence}\n") == [], sentence
    # Still fires on a real name in the same sentence shape.
    assert find_claims("# Card\n\nQuantized from meta-llama/Llama-3.1-8B.\n")


def test_based_on_is_not_a_lineage_phrase() -> None:
    """Deliberately unmatched, and the measurement is why (DEC-023).

    `based on` / `built on` is the largest phrasing class the pattern misses -- 59 of 389 candidate
    cards. Accepting it took claims from 11 to 75 and most of the additions were wrong: datasets a
    model was fine-tuned *on*, models it was merely compared to, and bare version fragments.
    English uses "based on" for every relation a card has to another name.
    """
    for sentence in (
        "ChemLLM-7B-Chat is built based on InternLM-2 with a chemistry corpus.",
        "This model is based on the transformer architecture.",
        "gte-Qwen2-1.5B-instruct is built on Qwen2-1.5B.",
    ):
        assert find_claims(f"# Card\n\n{sentence}\n") == [], sentence


def test_a_family_sentence_still_produces_a_claim_and_that_is_recorded() -> None:
    """DEC-028, pinned so the limitation cannot be forgotten or silently changed.

    A card republished verbatim from upstream carries the upstream publisher's prose. Here the
    sentence describes a *set* of models, one of which this artifact is a quantization of -- so the
    claim is approximately true and specifically wrong. Three narrowings were measured and each
    cost more correct claims than it saved; the decision is to emit with the sentence attached.
    """
    card = (
        "# Card\n\nTo support the research community, we have open-sourced DeepSeek-R1-Zero, "
        "DeepSeek-R1, and six dense models distilled from DeepSeek-R1 based on Llama and Qwen.\n"
    )
    claims = find_claims(card, subject="LoneStriker/DeepSeek-R1-Distill-Llama-70B-8.0bpw-h8-exl2")
    assert [(c.name, c.relation) for c in claims] == [("DeepSeek-R1", "distilled-from")]
    # The sentence travels with it. It is the only thing that lets a reader see this is family
    # prose rather than a self-description, so its presence is the mitigation.
    assert "we have open-sourced" in claims[0].excerpt


def test_distilled_is_its_own_relation() -> None:
    """DEC-027. A student's weights are not derived from its teacher's, so no weight-level method
    can ever confirm a distillation -- where a fine-tune leaves a body to compare."""
    from whence.domain import Relation

    claim = find_claims("# Card\n\nThis model was distilled from DeepSeek-R1.\n")[0]
    assert Relation(claim.relation) is Relation.DISTILLED_FROM
