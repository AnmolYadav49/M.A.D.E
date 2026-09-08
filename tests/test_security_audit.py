"""Regression tests for the AST security audit.

Every BLOCKED case here corresponds to something that either was, or plausibly
could become, a real bypass. The credential-exfiltration cases in particular
were live defects: `print(open('.env').read())` passed the audit, executed in
the subprocess, and put OPENROUTER_API_KEY into the session log rendered in
the browser.

Run:  python tests/test_security_audit.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from console import force_utf8  # noqa: E402

force_utf8()

from security import analyze_code, PASS, BLOCK  # noqa: E402

# (label, source, expected_verdict)
CASES: list[tuple[str, str, str]] = [
    # ---- must PASS: legitimate data / math work ---------------------------
    ("plain arithmetic", "print(2 + 2)", PASS),
    ("math module", "import math\nprint(math.sqrt(16))", PASS),
    ("sieve of eratosthenes",
     "n=200\ns=[True]*(n+1)\nfor i in range(2,int(n**0.5)+1):\n"
     "    if s[i]:\n        for j in range(i*i,n+1,i): s[j]=False\n"
     "print([i for i in range(2,n+1) if s[i]])", PASS),
    ("sympy symbolic integral",
     "from sympy import integrate, symbols, oo, exp\n"
     "x = symbols('x')\nprint(integrate(x**2*exp(-x), (x, 0, oo)))", PASS),
    ("numpy blockwise", "import numpy as np\nprint(np.ones((10,5)).sum(axis=0))", PASS),
    ("random histogram",
     "import random\nrandom.seed(1)\nprint(sum(random.randint(1,6) for _ in range(100)))", PASS),
    ("class with __init__",
     "class P:\n    def __init__(self, v): self.v = v\nprint(P(3).v)", PASS),
    ("main guard", "def go(): return 1\nif __name__ == '__main__': print(go())", PASS),

    # ---- must BLOCK: command execution ------------------------------------
    ("os.system", "import os\nos.system('id')", BLOCK),
    ("os import alone", "import os\nprint(os.getcwd())", BLOCK),
    ("subprocess.run", "import subprocess\nsubprocess.run(['ls'])", BLOCK),
    ("from os import system", "from os import system\nsystem('id')", BLOCK),
    ("aliased os", "import os as o\no.system('id')", BLOCK),
    ("aliased from-import", "from os import system as s\ns('id')", BLOCK),

    # ---- must BLOCK: dynamic evaluation ------------------------------------
    ("eval", "print(eval('1+1'))", BLOCK),
    ("exec", "exec('x=1')", BLOCK),
    ("compile", "compile('1','<s>','eval')", BLOCK),
    ("__import__", "__import__('os').system('id')", BLOCK),

    # ---- must BLOCK: sandbox escape via introspection ----------------------
    ("subclasses walk", "print(().__class__.__base__.__subclasses__())", BLOCK),
    ("globals reach", "print((lambda: 0).__globals__)", BLOCK),

    # ---- must BLOCK: credential exfiltration (these were live defects) -----
    ("read .env via open", "print(open('.env').read())", BLOCK),
    ("write arbitrary file", "open('/tmp/pwned','w').write('x')", BLOCK),
    ("with-open read", "with open('.env') as f:\n    print(f.read())", BLOCK),
    ("io.open", "import io\nprint(io.open('.env').read())", BLOCK),
    ("pandas read_csv", "import pandas as pd\nprint(pd.read_csv('.env'))", BLOCK),
    ("pandas aliased oddly", "import pandas as zz\nprint(zz.read_csv('.env'))", BLOCK),
    ("numpy loadtxt", "import numpy as np\nprint(np.loadtxt('.env'))", BLOCK),

    # ---- must BLOCK: RCE via eval-equivalents in ALLOWLISTED libraries -----
    # sympify() eval()s its argument; this was verified returning 'root' via
    # subprocess before it was blocked. An import allowlist alone is not a
    # sandbox precisely because of this class of API.
    ("sympy.sympify RCE", "from sympy import sympify\nsympify(\"__import__('subprocess').check_output(['id'])\")", BLOCK),
    ("sympy.sympify qualified", "import sympy\nsympy.sympify('1+1')", BLOCK),
    ("sympy S alias", "from sympy import S\nS('1+1')", BLOCK),
    ("sympy aliased module", "import sympy as sp\nsp.sympify('1+1')", BLOCK),
    ("parse_expr", "from sympy import parse_expr\nparse_expr('1+1')", BLOCK),
    ("pandas.eval", "import pandas as pd\npd.eval('1+1')", BLOCK),
    ("DataFrame.query", "import pandas as pd\ndf=pd.DataFrame({'a':[1]})\ndf.query('a>0')", BLOCK),
    ("DataFrame.eval", "import pandas as pd\ndf=pd.DataFrame({'a':[1]})\ndf.eval('a*2')", BLOCK),

    # ---- must BLOCK: network egress ---------------------------------------
    ("socket", "import socket\nsocket.socket()", BLOCK),
    ("requests", "import requests\nrequests.get('http://x')", BLOCK),
    ("urllib", "import urllib.request\nurllib.request.urlopen('http://x')", BLOCK),

    # ---- must BLOCK: unparseable ------------------------------------------
    ("syntax error", "def f(:\n    pass", BLOCK),
]


def main() -> int:
    failures = 0
    for label, src, expected in CASES:
        audit = analyze_code(src)
        ok = audit.verdict == expected
        if ok:
            print(f"  \033[32m✔\033[0m {expected.upper():5s} {label}")
        else:
            failures += 1
            reasons = "; ".join(f"{f.check}: {f.detail}" for f in audit.findings if f.severity == BLOCK)
            print(f"  \033[31m✘\033[0m expected {expected.upper()}, got {audit.verdict.upper()} — {label}")
            if reasons:
                print(f"      findings: {reasons}")

    print()
    if failures:
        print(f"\033[31m{failures} of {len(CASES)} security cases FAILED.\033[0m")
        return 1
    print(f"\033[32mAll {len(CASES)} security cases passed.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
