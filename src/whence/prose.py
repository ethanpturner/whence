"""Reading a derivation claim out of a model card's prose (DEC-010, DEC-012).

A card that declares no `base_model` may still say plainly, in English, what it was built from.
`prose-only-base` is the case: the frontmatter carries no lineage field at all, and the first line
of the body says the model is "an instruct fine-tuned version of the Mistral-7B-v0.2".

**Finding that sentence is not resolving it.** What this module produces is a claim with a quotation
behind it, always `unverifiable`, whose target is the name exactly as written -- unqualified, with
no namespace invented for it. Qualifying "Mistral-7B-v0.2" with the obvious owner yields a
repository the registry answers 401 for, and 401 without credentials does not distinguish "no such
repository" from "exists and you may not see it". The guess would probably be right. It would still
be a guess, and `expected-absent.yaml` scores it as invention.

**A model card is attacker-controlled content** published by anyone with an account. So the excerpt
is treated as data at every point (DEC-012): bounded, marked when truncated, never parsed for
meaning beyond the name it yields, and never interpolated into a log record -- in a log line the
same string is indistinguishable from prose the tool emitted about itself.

The pattern is deliberately narrow. Precision matters more than recall here: a missed claim leaves
a card with no lineage edge, which is the honest state of a card that says nothing machine-readable,
while a wrong one puts a fabricated ancestor in a BOM. `scripts/measure_prose.py` reports what the
pattern does against a live sample.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The most an excerpt may carry into the report (DEC-012). Long enough for the sentence that makes
#: the claim, short enough that a card cannot push a wall of text through a BOM into a reader's
#: terminal. A longer sentence is cut and marked, never silently shortened.
EXCERPT_LIMIT = 320

#: Verbs that state a derivation, with the relation each implies. `merged` is absent on purpose: a
#: merge names several parents and a sentence naming one of them is not the lineage.
_RELATIONS = {
    "fine-tuned": "derives-from",
    "finetuned": "derives-from",
    "fine tuned": "derives-from",
    "quantized": "quantized-from",
    "quantised": "quantized-from",
    "distilled": "distilled-from",
}

#: A model name as a card writes one. The shape is what separates a name from a noun, and getting
#: it wrong is not a near miss: the first version of this pattern asked only for four alphanumeric
#: characters, and against 91 published cards it produced ten claims, all ten of them naming an
#: English word -- "this", "specialized", "Alibaba". A name must therefore either be qualified
#: (`owner/name`) or carry a digit somewhere inside it, which is what model names in practice do
#: and what prose in practice does not.
_QUALIFIED = r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]{2,}"
_VERSIONED = r"[A-Za-z][A-Za-z0-9._-]*[0-9][A-Za-z0-9._-]*"
_NAME = rf"(?:{_QUALIFIED}|{_VERSIONED})"

#: "<verb> version of the <name>", "<verb> from <name>", "a <verb> of <name>". The verb and the
#: name must be close together: allowing arbitrary distance between them is how a scanner starts
#: attributing a name from one clause to a verb in another.
_PATTERN = re.compile(
    r"\b(?P<verb>fine[- ]?tuned|finetuned|quantq?i[sz]ed|distilled)\b"
    r"(?:\s+\w+){0,3}?\s+(?:of|from)\s+(?:the\s+)?"
    r"(?P<name>" + _NAME + r")",
    re.IGNORECASE,
)


#: Numeric formats and quantization schemes. "Quantized from FP16" names a **dtype**, not an
#: artifact: it says what precision the weights were in, and every model has a precision. Measured
#: against 1,091 published cards this was the only remaining false-positive class in the claims the
#: tool would actually emit -- one in twelve -- and it is systematic rather than incidental, since
#: describing the source precision is the normal way to write a quantization card.
_FORMAT_TOKEN = re.compile(
    r"""^(?:
        (?:f|fp|bf|int|uint|nf|mx)\d{1,2}        # fp16, bf16, int8, nf4, f32
      | i?q\d(?:_[a-z0-9]+)*                     # q4_k_m, q8_0, iq3_m
      | e\dm\d                                  # e4m3, e5m2
      | (?:awq|gptq|gguf|ggml|exl\d|safetensors)
    )$""",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class ProseClaim:
    """A derivation a card states in words, and the sentence that states it."""

    #: The name exactly as the card wrote it. Never qualified, never corrected.
    name: str
    relation: str
    #: 1-based line in the raw README, so a reader can go and look.
    line: int
    excerpt: str
    truncated: bool


def _normalise_verb(verb: str) -> str:
    lowered = verb.lower().replace("_", "-")
    if lowered.startswith(("quant", "quantq")):
        return "quantized"
    if lowered.startswith(("fine", "finet")):
        return "fine-tuned"
    return lowered


def _sentence_around(line: str, start: int, end: int) -> str:
    """The claim's sentence, or as much of the line as the bound allows."""
    left = max((line.rfind(mark, 0, start) for mark in (". ", "! ", "? ")), default=-1)
    begin = 0 if left < 0 else left + 2
    right = min(
        (pos for pos in (line.find(mark, end) for mark in (". ", ".", "!", "?")) if pos != -1),
        default=-1,
    )
    finish = len(line) if right < 0 else right + 1
    return line[begin:finish].strip()


def _is_table_row(line: str) -> bool:
    """A markdown table row. Skipped, and this is the single largest source of wrong claims.

    Measured against published cards, every false positive that survived the name shape came from
    one: a quantization file inventory saying a build was "re-quantized from F16" (a precision
    format, not a model), and a model-family table saying that a *sibling* was "fine-tuned from"
    this card's own model -- a true sentence whose arrow points the other way.

    The rule behind it: a card states its own lineage in prose, and a table is a list about several
    things. Attributing a table's sentence to the card's subject is the mistake, not the format.
    """
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def find_claims(readme: str, *, subject: str | None = None) -> list[ProseClaim]:
    """Every derivation claim the pattern recognises, in document order.

    Frontmatter is skipped: a `base_model` there is a structured declaration handled elsewhere, and
    a `new_version` there is a successor pointer whose arrow runs the other way -- reading it as
    ancestry emits the edge reversed, which `expected-absent.yaml` names as a specific failure.

    `subject` is the card's own model, when known. A claim naming it is dropped: nothing is its own
    ancestor, and a card that mentions itself in a derivation sentence is describing something else.
    """
    lines = readme.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                start = index + 1
                break

    claims: list[ProseClaim] = []
    in_code = False
    # Scanned by paragraph, not by line. A card's sentence is a sentence wherever its author's
    # editor happened to wrap, and a line-based scan silently misses every claim that spans two --
    # a failure that looks exactly like a card saying nothing.
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        first = paragraph[0][0]
        text = " ".join(line for _, line in paragraph)
        for match in _PATTERN.finditer(text):
            name = match.group("name").rstrip("._-,;:)")
            # "Quantized from FP16" names the precision the weights were in, which every model has.
            # It is not an artifact and cannot be a node.
            if _FORMAT_TOKEN.match(name):
                continue
            if subject is not None and name.lower() in {
                subject.lower(),
                subject.split("/")[-1].lower(),
            }:
                continue
            # The line the match starts on, so a reader can go and look at the right place rather
            # than at the top of the paragraph.
            consumed = 0
            line_no = first
            for offset, line in paragraph:
                if consumed + len(line) >= match.start():
                    line_no = offset
                    break
                consumed += len(line) + 1
            sentence = _sentence_around(text, match.start(), match.end())
            truncated = len(sentence) > EXCERPT_LIMIT
            claims.append(
                ProseClaim(
                    name=name,
                    relation=_RELATIONS.get(_normalise_verb(match.group("verb")), "derives-from"),
                    line=line_no + 1,
                    excerpt=sentence[:EXCERPT_LIMIT] + ("\u2026" if truncated else ""),
                    truncated=truncated,
                )
            )
        paragraph.clear()

    for offset, line in enumerate(lines[start:], start=start):
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            continue
        # A fenced block is code, not a claim about lineage. A comment inside one saying "fine-tuned
        # from foo" is a sample, and treating it as a declaration puts an example in a BOM.
        if in_code or _is_table_row(line):
            flush()
            continue
        if not stripped:
            flush()
            continue
        paragraph.append((offset, stripped))
    flush()
    return claims
