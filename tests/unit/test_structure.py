"""The structural check, including the contradiction path.

Benchmark scenarios use real captures; these use synthetic configs, because the contradiction path
has to be tested and 45 real declared fine-tunes produced no instance of it. That absence is a
finding about the corpus, not a reason to leave the branch unexercised.
"""

from __future__ import annotations

from typing import Any

from whence.domain import ArtifactRef, Relation, Verdict
from whence.registry import Response
from whence.structure import check


def ref(slug: str) -> ArtifactRef:
    namespace, name = slug.split("/")
    return ArtifactRef(host="huggingface.co", namespace=namespace, name=name, pinned=False)


class _Configs:
    def __init__(self, **configs: dict[str, Any]) -> None:
        self._configs = configs

    def get(self, path: str) -> Response:
        for slug, config in self._configs.items():
            if path.startswith(f"/{slug.replace('__', '/')}/"):
                return Response(status=200, body=config)
        return Response(status=404, body=None)


BODY = {
    "hidden_size": 3584,
    "num_hidden_layers": 28,
    "num_attention_heads": 28,
    "num_key_value_heads": 4,
    "intermediate_size": 18944,
}


def test_a_compatible_body_is_still_unverifiable() -> None:
    """Every fine-tune of a base has its body. Agreement is necessary, not sufficient."""
    registry = _Configs(a__child=dict(BODY), b__base=dict(BODY))
    result = check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM)
    assert result.verdict is Verdict.UNVERIFIABLE


def test_a_differing_body_contradicts() -> None:
    registry = _Configs(a__child=dict(BODY), b__base={**BODY, "hidden_size": 896})
    result = check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM)
    assert result.verdict is Verdict.CONTRADICTED
    assert result.differing_fields == ("hidden_size",)


def test_a_changed_task_head_is_not_a_contradiction() -> None:
    """Measured: `architectures` and `vocab_size` differ on ordinary fine-tunes -- a reranker built
    on a masked-LM base reports a different class, and added tokens change the vocabulary. Including
    them flagged 9 of 35 real declared fine-tunes (DEC-020)."""
    registry = _Configs(
        a__child={**BODY, "architectures": ["XForSequenceClassification"], "vocab_size": 151_700},
        b__base={**BODY, "architectures": ["XForMaskedLM"], "vocab_size": 151_643},
    )
    assert (
        check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM).verdict
        is Verdict.UNVERIFIABLE
    )


def test_an_absent_field_is_not_a_difference() -> None:
    """Composite configs nest their dimensions, so a top-level lookup finds nothing. Treating that
    as a difference reports `contradicted` over file layout."""
    registry = _Configs(a__child=dict(BODY), b__base={"architectures": ["Composite"]})
    assert (
        check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM).verdict
        is Verdict.UNVERIFIABLE
    )


def test_quantization_is_out_of_scope() -> None:
    registry = _Configs(a__child=dict(BODY), b__base={**BODY, "hidden_size": 1})
    assert (
        check(registry, ref("a/child"), ref("b/base"), Relation.QUANTIZED_FROM).verdict
        is Verdict.UNVERIFIABLE
    )


def test_nested_dimensions_are_found(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Composite and multimodal configurations nest the text model's dimensions. Reading only the
    top level left 13 of 45 sampled real pairs uncomparable; reading `text_config` leaves 2."""
    registry = _Configs(
        a__child={"architectures": ["Composite"], "text_config": dict(BODY)},
        b__base=dict(BODY),
    )
    assert (
        check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM).verdict
        is Verdict.UNVERIFIABLE
    )

    mismatched = _Configs(
        a__child={"architectures": ["Composite"], "text_config": {**BODY, "hidden_size": 896}},
        b__base=dict(BODY),
    )
    result = check(mismatched, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM)
    assert result.verdict is Verdict.CONTRADICTED
    assert "read from text_config/top" in result.detail


def test_levels_are_not_merged(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A composite model's top-level dimensions may describe a vision tower rather than the text
    model. Merging across levels would compare different components while looking like a match."""
    registry = _Configs(
        # Two top-level fields, so the top level wins and `text_config` is never consulted.
        a__child={"hidden_size": 1152, "num_hidden_layers": 27, "text_config": dict(BODY)},
        b__base=dict(BODY),
    )
    result = check(registry, ref("a/child"), ref("b/base"), Relation.DERIVES_FROM)
    assert result.verdict is Verdict.CONTRADICTED
