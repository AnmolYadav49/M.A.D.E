"""Scripted stand-in for the OpenRouter LLM, enabled with MADE_DEMO_MODE=1.

WHY THIS EXISTS
---------------
Two practical reasons, neither of which is "fake the product":

1. A live judged demo should not be able to fail because a free-tier LLM
   endpoint rate-limited you thirty seconds before your slot.
2. Recording a reproducible walkthrough needs deterministic agent output.

WHAT IS AND ISN'T REAL IN DEMO MODE
-----------------------------------
Real, unchanged:  the LangGraph routing, the conditional self-heal edge, the
                  retry cap, the sandbox subprocess (the code below genuinely
                  executes, in a scrubbed env and a throwaway cwd), the failure
                  classifier, the AST security audit, the HITL gate, and the
                  websocket log stream.
Scripted:         only the *text* the Researcher / Coder / Reviewer would have
                  gotten back from the model.

Nothing here bypasses the audit or fakes a result. The "primes" scenario's
first attempt has a genuine NameError and the sandbox genuinely fails on it;
the self-heal that follows is real control flow reacting to a real traceback.
The "exfiltration" scenario emits code that the AST audit genuinely refuses —
the block you see in the UI is the real policy firing, not a scripted screen.

The server logs a DEMO MODE banner on startup and every node logs `(demo)` so
this can never be quietly mistaken for real inference.
"""
from __future__ import annotations

import logging
import os
import re
import time

# Scripted responses return instantly, which would make the pipeline finish
# before a viewer can see the tracker advance. Real model calls take seconds;
# this reintroduces comparable latency so the demo is watchable and honest
# about pacing. Set to 0 to disable.
STEP_DELAY_SEC = float(os.getenv("MADE_DEMO_STEP_DELAY", "1.6"))


class _Scenario:
    def __init__(self, keywords, research, attempts, review):
        self.keywords = keywords
        self.research = research
        self.attempts = attempts  # list[str]; index 0 is the first Coder answer
        self.review = review

    def matches(self, task: str) -> bool:
        t = task.lower()
        return any(k in t for k in self.keywords)


# --- Scenario: primes (clean task, one genuine self-heal) ---------------------
_PRIMES_BAD = '''\
# Sieve of Eratosthenes up to 200.
limit = 200
sieve = [True] * (limit + 1)
sieve[0] = sieve[1] = False

for i in range(2, int(sqrt(limit)) + 1):   # bug: sqrt was never imported
    if sieve[i]:
        for j in range(i * i, limit + 1, i):
            sieve[j] = False

print(", ".join(str(i) for i in range(limit + 1) if sieve[i]))
'''

_PRIMES_GOOD = '''\
import math

# Self-heal: math.sqrt was used without importing math. Import added and the
# call qualified.
limit = 200
sieve = [True] * (limit + 1)
sieve[0] = sieve[1] = False

for i in range(2, int(math.sqrt(limit)) + 1):
    if sieve[i]:
        for j in range(i * i, limit + 1, i):
            sieve[j] = False

print(", ".join(str(i) for i in range(limit + 1) if sieve[i]))
'''

# --- Scenario: symbolic integral (the "can it do real maths" answer) ---------
_SYMPY_GOOD = '''\
from sympy import symbols, integrate, exp, oo

x = symbols("x", positive=True)
result = integrate(x**2 * exp(-x), (x, 0, oo))

print("integral of x**2 * exp(-x) from 0 to oo =", result)
'''

# --- Scenario: dice histogram ------------------------------------------------
_DICE_GOOD = '''\
import random
from collections import Counter

random.seed(42)
counts = Counter(random.randint(1, 6) + random.randint(1, 6) for _ in range(1000))

for total in range(2, 13):
    n = counts.get(total, 0)
    print(f"{total:>2} | {'#' * (n // 5):<28} {n}")
'''

# --- Scenario: adversarial exfiltration (must be refused) --------------------
# This is what a compliant-but-unsafe model would produce for the prompt. It is
# emitted deliberately so the AST audit can be seen refusing it for real.
_EXFIL = '''\
# Read the server configuration and print it.
with open(".env") as f:
    print(f.read())
'''

SCENARIOS = [
    _Scenario(
        keywords=("prime", "eratosthenes", "sieve"),
        research=(
            "This is a classic sieve problem — no third-party libraries needed. "
            "Allocate a boolean array of size n+1, mark 0 and 1 as composite, then "
            "for each i up to sqrt(n) mark multiples starting at i*i. math.sqrt "
            "bounds the outer loop; the survivors are the primes."
        ),
        attempts=[_PRIMES_BAD, _PRIMES_GOOD],
        review=(
            "Sieve bounds are correct: the outer loop stops at floor(sqrt(limit)) "
            "and inner marking starts at i*i, so no composite is missed and none "
            "is marked twice unnecessarily. math is now imported. No file, network "
            "or subprocess access. No further concerns."
        ),
    ),
    _Scenario(
        keywords=("integral", "integrate", "sympy", "symbolic", "∫"),
        research=(
            "Use sympy for the symbolic work rather than a numeric quadrature — the "
            "task asks for an exact result. Declare x as a positive real symbol, then "
            "call integrate(expr, (x, 0, oo)) with sympy's oo for the infinite bound. "
            "This is the gamma integral and evaluates exactly to 2."
        ),
        attempts=[_SYMPY_GOOD],
        review=(
            "sympy.integrate with an explicit (x, 0, oo) tuple gives the definite "
            "form directly, and declaring x positive lets sympy pick the convergent "
            "branch without extra assumptions. Pure symbolic computation, no I/O. "
            "No concerns."
        ),
    ),
    _Scenario(
        keywords=("dice", "histogram", "roll"),
        research=(
            "Pure standard library: random for the rolls and collections.Counter to "
            "tally sums in a single pass. Seed the RNG so the run is reproducible, "
            "then format each bucket with a scaled run of '#' characters."
        ),
        attempts=[_DICE_GOOD],
        review=(
            "Counter tallies in one pass and the RNG is explicitly seeded, so the "
            "output is deterministic and reviewable. Bar scaling divides by 5 to keep "
            "the histogram within terminal width. No I/O. No concerns."
        ),
    ),
    _Scenario(
        keywords=(".env", "exfiltrat", "api key", "api keys", "configuration file", "secrets"),
        research=(
            "The request is to read a configuration file from disk. Note that the "
            "execution policy refuses filesystem access, so this is expected to be "
            "rejected at the audit stage rather than executed."
        ),
        attempts=[_EXFIL],
        review="(not reached — the AST audit refuses this before review)",
    ),
]

_DEFAULT = _Scenario(
    keywords=(),
    research=(
        "Break the task into a small pure-Python computation using only allowlisted "
        "libraries (math, statistics, itertools, numpy, sympy). Avoid file and network "
        "access, and keep the work inside the sandbox's time budget."
    ),
    attempts=['print("demo mode: no scripted scenario matched this task")\n'],
    review="Trivial computation, no I/O, nothing to flag.",
)


class _ScriptedResponse:
    """Mimics the .content attribute of a LangChain chat response."""

    def __init__(self, content: str) -> None:
        self.content = content


class ScriptedLLM:
    """Drop-in for ChatOpenAI.invoke() that returns canned agent text.

    The scenario is chosen from the task text embedded in the prompt, so the
    generated code always corresponds to the prompt the operator actually
    clicked. Coder attempts advance per call so the self-heal loop gets a
    genuinely different second answer.
    """

    def __init__(self) -> None:
        self._coder_calls = 0

    @staticmethod
    def _task_from_prompt(prompt: str) -> str:
        m = re.search(r"(?:TASK:|Original task:|code for this task:)\s*(.+)", prompt)
        return m.group(1).strip() if m else prompt

    def _scenario(self, prompt: str) -> _Scenario:
        task = self._task_from_prompt(prompt)
        for s in SCENARIOS:
            if s.matches(task):
                return s
        return _DEFAULT

    def invoke(self, messages) -> _ScriptedResponse:
        prompt = messages[0].content if messages else ""
        if STEP_DELAY_SEC:
            time.sleep(STEP_DELAY_SEC)
        scenario = self._scenario(prompt)

        if "Senior Data Science Researcher" in prompt:
            # The Researcher is always the first node in a run, so this is the
            # reliable signal that a new run has begun. Resetting here matters
            # because ScriptedLLM is a process-wide singleton: without it the
            # attempt counter carried across runs, so the second dispatch in a
            # session skipped straight to the already-repaired code and the
            # self-heal never appeared to happen.
            self._coder_calls = 0
            logging.info("--- 🔍 (demo) scripted Researcher response (run reset) ---")
            return _ScriptedResponse(scenario.research)

        if "Security & Code Reviewer" in prompt:
            logging.info("--- 🛡️  (demo) scripted Reviewer response ---")
            return _ScriptedResponse(scenario.review)

        if "Expert Python Developer" in prompt:
            idx = min(self._coder_calls, len(scenario.attempts) - 1)
            self._coder_calls += 1
            logging.info("--- 💻 (demo) scripted Coder attempt %d ---", self._coder_calls)
            return _ScriptedResponse(scenario.attempts[idx])

        return _ScriptedResponse("(demo mode: no scripted response for this prompt)")
