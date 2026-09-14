from app.judge import judge


def test_correct_solution_passes():
    code = "def add(a, b):\n    return a + b\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}],
                [{"args": [10, 20], "expected": 30}])
    assert res["passed"] is True
    assert res["tests_passed"] == 2


def test_wrong_solution_fails_and_hides_hidden():
    code = "def add(a, b):\n    return a - b\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}],
                [{"args": [10, 20], "expected": 30}])
    assert res["passed"] is False
    # sample results are exposed, hidden are only summarised
    assert len(res["sample_results"]) == 1
    assert "Hidden tests" in res["feedback"]


def test_blocked_import_rejected():
    code = "import os\ndef add(a, b):\n    return a + b\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}], [])
    assert res["passed"] is False
    assert "Disallowed" in res["feedback"]


def test_missing_function_rejected():
    code = "def other(a, b):\n    return a + b\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}], [])
    assert res["passed"] is False


def test_infinite_loop_times_out():
    code = "def add(a, b):\n    while True:\n        pass\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}], [])
    assert res["passed"] is False
    assert "Time limit" in res["feedback"] or "error" in res["feedback"].lower()


def test_runtime_error_handled():
    code = "def add(a, b):\n    return a + undefined_var\n"
    res = judge(code, "add", [{"args": [1, 2], "expected": 3}], [])
    assert res["passed"] is False
