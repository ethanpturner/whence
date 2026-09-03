"""DEC-014: response class comes from the status code, never from the body's prose."""

from __future__ import annotations

import pytest

from whence.domain import ResolutionClass
from whence.registry import Response, classify


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (200, ResolutionClass.CONCLUSIVE),
        (404, ResolutionClass.CONCLUSIVE),
        (307, ResolutionClass.CONCLUSIVE),
        (401, ResolutionClass.INCONCLUSIVE),
        (403, ResolutionClass.INCONCLUSIVE),
        (429, ResolutionClass.TRANSIENT),
        (500, ResolutionClass.TRANSIENT),
        (503, ResolutionClass.TRANSIENT),
        (0, ResolutionClass.TRANSIENT),
    ],
)
def test_classification(status: int, expected: ResolutionClass) -> None:
    assert classify(status) is expected


def test_misleading_body_does_not_change_the_class() -> None:
    """withdrawn-base captures a 401 reading "Invalid username or password" for an unauthenticated
    request. Believing the prose would abort the run or retry; the status is what decides."""
    response = Response(status=401, body={"error": "Invalid username or password."})
    assert response.resolution is ResolutionClass.INCONCLUSIVE
