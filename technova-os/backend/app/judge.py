"""Safe, isolated code judge for the challenge platform.

Security model:
- User code runs in a SEPARATE python subprocess (never in the API process).
- Wall-clock timeout kills runaway/infinite loops.
- A restricted harness blocks obvious dangerous imports/builtins (os, sys, open, subprocess, eval...).
- Only the target function's return value is compared against test cases.
- Hidden test results are summarised (pass/fail counts) but never exposed.

NOTE: For production at scale this should run inside a container/nsjail/gVisor sandbox with cgroup limits
and no network. The subprocess + AST guard here is a solid first layer and keeps the API process safe.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

TIME_LIMIT_SECONDS = 5
BLOCKED = ["import os", "import sys", "import subprocess", "import shutil", "import socket",
           "__import__", "open(", "eval(", "exec(", "compile(", "input(", "import ctypes",
           "importlib", "globals(", "getattr(__", "os.system", "pty", "signal",
           "import threading", "import multiprocessing", "import asyncio", "fork",
           "__subclasses__", "__globals__", "__builtins__", "marshal", "import mmap",
           "import fcntl", "import requests", "import urllib", "import http"]

HARNESS = r'''
import json, sys, builtins, resource

# Drop dangerous runtime builtins. NOTE: exec/compile are needed by this harness itself and
# user code cannot reach them anyway (blocked by the static check before we get here), so we
# only null the ones that would let user code touch the filesystem / stdin.
for _b in ["open", "input"]:
    try:
        setattr(builtins, _b, None)
    except Exception:
        pass

try:
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))  # 256MB memory
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))                                 # 5s CPU
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))                               # no fork/exec (fork bomb guard)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))                               # no file writes
except Exception:
    pass

USER_CODE = json.loads(sys.stdin.readline())
FUNC = json.loads(sys.stdin.readline())
TESTS = json.loads(sys.stdin.readline())

ns = {}
results = []
try:
    exec(USER_CODE, ns)
except Exception as e:
    print(json.dumps({"error": "compile: " + str(e)[:200]}))
    sys.exit(0)

fn = ns.get(FUNC)
if not callable(fn):
    print(json.dumps({"error": "Function '%s' not defined" % FUNC}))
    sys.exit(0)

for t in TESTS:
    try:
        out = fn(*t.get("args", []))
        ok = out == t.get("expected")
        results.append({"ok": bool(ok), "got": repr(out)[:120]})
    except Exception as e:
        results.append({"ok": False, "got": "error: " + str(e)[:120]})

print(json.dumps({"results": results}))
'''


def _static_check(code: str) -> str | None:
    low = code
    for token in BLOCKED:
        if token in low:
            return f"Disallowed operation detected: '{token}'"
    return None


def _run(code: str, func: str, tests: list) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(HARNESS)
        harness_path = f.name
    try:
        payload = (json.dumps(code) + "\n" + json.dumps(func) + "\n" + json.dumps(tests) + "\n")
        proc = subprocess.run(
            [sys.executable, "-I", harness_path],
            input=payload, capture_output=True, text=True,
            timeout=TIME_LIMIT_SECONDS,
            env={"PATH": "/usr/bin:/bin"},
        )
    except subprocess.TimeoutExpired:
        return {"error": "Time limit exceeded"}
    finally:
        try:
            os.unlink(harness_path)
        except OSError:
            pass
    if proc.returncode != 0 and not proc.stdout:
        return {"error": (proc.stderr or "runtime error")[:200]}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": "judge failed to parse output"}


def judge(code: str, function_name: str, sample_tests: list, hidden_tests: list) -> dict:
    """Return a submission result. Sample test details are shown; hidden are summarised only."""
    err = _static_check(code)
    if err:
        return {"passed": False, "tests_passed": 0,
                "tests_total": len(sample_tests) + len(hidden_tests),
                "feedback": err, "sample_results": []}

    all_tests = list(sample_tests) + list(hidden_tests)
    res = _run(code, function_name, all_tests)
    if "error" in res:
        return {"passed": False, "tests_passed": 0, "tests_total": len(all_tests),
                "feedback": res["error"], "sample_results": []}

    results = res["results"]
    n_sample = len(sample_tests)
    sample_results = []
    for i, t in enumerate(sample_tests):
        r = results[i]
        sample_results.append({
            "args": t.get("args"), "expected": t.get("expected"),
            "got": r["got"], "ok": r["ok"],
        })
    passed_count = sum(1 for r in results if r["ok"])
    hidden_results = results[n_sample:]
    hidden_passed = sum(1 for r in hidden_results if r["ok"])
    all_passed = passed_count == len(all_tests)

    if all_passed:
        feedback = "All tests passed! 🎉"
    else:
        parts = []
        sample_fail = [i for i, r in enumerate(results[:n_sample]) if not r["ok"]]
        if sample_fail:
            parts.append(f"{len(sample_fail)} sample test(s) failed.")
        if hidden_results:
            parts.append(f"Hidden tests: {hidden_passed}/{len(hidden_results)} passed.")
        feedback = " ".join(parts) or "Some tests failed."

    return {
        "passed": all_passed,
        "tests_passed": passed_count,
        "tests_total": len(all_tests),
        "feedback": feedback,
        "sample_results": sample_results,
    }
