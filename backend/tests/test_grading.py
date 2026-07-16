# tests/test_grading.py
from grading import letter_grade_for, compute_cumulative_grade


def test_letter_grade_boundaries():
    assert letter_grade_for(None) is None
    assert letter_grade_for(59.99) == "F"
    assert letter_grade_for(60) == "D"
    assert letter_grade_for(69.99) == "D"
    assert letter_grade_for(70) == "C"
    assert letter_grade_for(79.99) == "C"
    assert letter_grade_for(80) == "B"
    assert letter_grade_for(89.99) == "B"
    assert letter_grade_for(90) == "A"
    assert letter_grade_for(100) == "A"


def test_compute_cumulative_grade_all_categories_present():
    result = compute_cumulative_grade([
        (90, "homework"),
        (95, "quizzes"),
        (90, "tests"),
    ])
    assert result["percentage"] == 90 * 0.30 + 95 * 0.30 + 90 * 0.40
    assert result["letter_grade"] == "A"


def test_compute_cumulative_grade_renormalizes_missing_categories():
    # No "tests" grades yet -- weight should redistribute over homework/quizzes
    # only, rather than treating the missing category as a 0.
    result = compute_cumulative_grade([
        (80, "homework"),
        (80, "quizzes"),
    ])
    assert result["percentage"] == 80.0
    assert result["letter_grade"] == "B"


def test_compute_cumulative_grade_averages_within_category():
    result = compute_cumulative_grade([
        (100, "homework"),
        (80, "homework"),
    ])
    assert result["percentage"] == 90.0


def test_compute_cumulative_grade_no_submissions():
    result = compute_cumulative_grade([])
    assert result == {"percentage": None, "letter_grade": None}
