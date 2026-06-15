"""HTTP-level tests for the SymPy-backed /check-answer grading endpoint.

These exercise the full route (request validation → auth → answer_check →
response) through the ASGI stack, complementing the unit tests on
`answer_check.answers_equivalent`.
"""
import pytest


def _check(client, student, correct, answer_type=None):
    body = {"student_answer": student, "correct_answer": correct}
    if answer_type:
        body["answer_type"] = answer_type
    resp = client.post("/check-answer", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.parametrize(
    "student,correct,expected",
    [
        ("1/2", "0.5", True),
        (r"\frac{1}{2}", "1/2", True),
        (r"\sqrt{2}", "2", False),       # old client bug: false positive
        ("1/2", r"\frac{1}{2}", True),   # old client bug: false negative
        ("x=5", "5", True),
        ("2x=10", "x=5", True),
        ("(x+1)^2", "x^2+2x+1", True),
        ("4x+2", "2x+1", False),
    ],
)
def test_grading_verdicts(auth_client, student, correct, expected):
    result = _check(auth_client, student, correct)
    assert result["is_correct"] is expected
    assert result["correct_answer"] == correct


def test_requires_auth():
    """Without the dependency override the endpoint must reject anonymous calls."""
    from fastapi.testclient import TestClient
    from api import app

    resp = TestClient(app).post(
        "/check-answer",
        json={"student_answer": "1/2", "correct_answer": "0.5"},
    )
    assert resp.status_code in (401, 403)


def test_empty_answer_is_incorrect(auth_client):
    assert _check(auth_client, "", "5")["is_correct"] is False
