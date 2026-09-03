"""Phase two, first increment: structural lineage checking.

A fine-tune inherits its base's architecture. If a model declares a base whose shape-defining
configuration differs, the declaration cannot be true, and that is determinable from a few hundred
bytes of metadata rather than gigabytes of weights.

**What this establishes, precisely.** A mismatch **contradicts** a `derives-from` claim. A match
establishes nothing further: every fine-tune of a given base has an identical configuration, so
agreement is a necessary condition and not a sufficient one, and the verdict stays `unverifiable`.
Reporting a match as `verified` would be the overclaiming this project exists to correct.

DEC-006 is not weakened. `config.json` is parsed as inert JSON and never handed to a framework; no
model code is executed and no weights are loaded. The distinction matters because the documented
remote-code paths on this registry run through a framework's *deserialization* of this file, not
through reading it.

Scope (DEC-020): applied only to `derives-from`. Quantized, merged, and adapter relations
legitimately alter or omit these fields, so a mismatch there is not evidence of anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from whence.domain import ArtifactRef, Relation, ResolutionClass, Verdict
from whence.registry import Registry

# Fields describing the transformer body, which a fine-tune cannot change without ceasing to be
# one. Deliberately narrow -- see DEC-020.
SHAPE_FIELDS = (
    "hidden_size",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "intermediate_size",
)

# Measured and excluded. `architectures` changes whenever a task head is swapped (a reranker built
# on a masked-LM base reports a different class), and `vocab_size` changes whenever tokens are
# added. Both are ordinary fine-tuning outcomes. Including them flagged 9 of 35 real declared
# fine-tunes; excluding them leaves 1. They are reported as context on a finding, never as one.
EXCLUDED_FIELDS = ("architectures", "vocab_size")

CHECKABLE = frozenset({Relation.DERIVES_FROM})


@dataclass(frozen=True)
class StructuralCheck:
    verdict: Verdict
    detail: str
    differing_fields: tuple[str, ...] = ()


def config_path(ref: ArtifactRef) -> str:
    return f"/{ref.slug}/resolve/main/config.json"


def _config(registry: Registry, ref: ArtifactRef) -> tuple[dict[str, Any] | None, ResolutionClass]:
    """Fetch and parse a config, following the registry's content redirect.

    File paths redirect to a cache location. The registry seam deliberately does not follow
    redirects -- the resolver needs to *see* a 307, since a cross-namespace one is a finding
    (DEC-017) -- so the hop is taken here, where it is bookkeeping rather than evidence.
    """
    response = registry.get(config_path(ref))
    hops = 0
    while response.redirected and hops < 3:
        response = registry.get(str(response.location))
        hops += 1
    if response.resolution is ResolutionClass.TRANSIENT:
        return None, response.resolution
    if response.status != 200 or not isinstance(response.body, dict):
        return None, response.resolution
    return response.body, response.resolution


def check(
    registry: Registry, source: ArtifactRef, target: ArtifactRef, relation: Relation
) -> StructuralCheck:
    if relation not in CHECKABLE:
        return StructuralCheck(
            Verdict.UNVERIFIABLE,
            f"not applicable to {relation.value}: the relation legitimately alters these fields",
        )

    source_config, source_class = _config(registry, source)
    target_config, target_class = _config(registry, target)
    if source_class is ResolutionClass.TRANSIENT or target_class is ResolutionClass.TRANSIENT:
        # DEC-014: a transient failure produces no verdict at all.
        return StructuralCheck(Verdict.UNVERIFIABLE, "configuration not reached; no verdict")
    if source_config is None or target_config is None:
        missing = source.slug if source_config is None else target.slug
        return StructuralCheck(
            Verdict.UNVERIFIABLE,
            f"configuration for {missing} is unavailable, so the shapes cannot be compared",
        )

    # Compare only fields present in BOTH configs. A field absent from one side is not a
    # differing value: composite and multimodal configs nest the text model's dimensions under a
    # sub-key, so a top-level lookup finds nothing. Treating that absence as a difference would
    # report `contradicted` because two publishers structure a file differently -- absence read as
    # a negative answer, which is the error this project exists to prevent (DEC-020).
    comparable = tuple(f for f in SHAPE_FIELDS if f in source_config and f in target_config)
    if len(comparable) < 2:
        return StructuralCheck(
            Verdict.UNVERIFIABLE,
            (
                f"the two configurations share too few comparable body fields "
                f"({len(comparable)}); one of them likely nests its dimensions under a sub-key, "
                f"and a top-level comparison would be measuring file layout rather than shape"
            ),
        )

    differing = tuple(f for f in comparable if source_config.get(f) != target_config.get(f))
    if differing:
        context = tuple(f for f in EXCLUDED_FIELDS if source_config.get(f) != target_config.get(f))
        note = (
            f" (also differs on {', '.join(context)}, which fine-tuning may change)"
            if context
            else ""
        )
        return StructuralCheck(
            Verdict.CONTRADICTED,
            (
                f"the declared base has a different transformer body ({', '.join(differing)}). A "
                f"fine-tune cannot change these, so this relationship is not the one declared"
                f"{note}. It does not follow that no relationship exists -- distillation and "
                f"re-architecting are real and are sometimes tagged as fine-tuning."
            ),
            differing,
        )
    return StructuralCheck(
        Verdict.UNVERIFIABLE,
        (
            "architecture is compatible with the declared base. This is a necessary condition and "
            "not a sufficient one: every fine-tune of this base has the same configuration, so "
            "agreement does not establish that this model is one of them."
        ),
    )
