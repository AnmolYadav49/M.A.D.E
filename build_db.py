"""Build the FAISS methodology corpus used by researcher_node for grounded RAG.

Every entry is a compact "how you actually solve this class of problem" recipe —
what libraries to reach for, the load-bearing function names, and the shape of
the solution. Kept intentionally short so the Researcher can retrieve several
relevant recipes and still fit them into the LLM's context budget.

Run this once before booting the app:  python build_db.py
"""
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

CORPUS: list[dict] = [
    # --- Pandas: cleaning, aggregation, joins ------------------------------
    {"title": "Pandas · load a CSV", "text": "Use pd.read_csv('file.csv'). For large files, pass chunksize=N to iterate rows in batches instead of loading everything at once. dtype= can preallocate types."},
    {"title": "Pandas · drop missing values", "text": "df.dropna() drops any row with a NaN. Pass subset=['col'] to only consider specific columns. inplace=True mutates the frame in place."},
    {"title": "Pandas · fill missing values", "text": "df.fillna(0) or df.fillna(method='ffill') / 'bfill' for time series. For per-column defaults, pass a dict: df.fillna({'age': 0, 'name': ''})."},
    {"title": "Pandas · group by and aggregate", "text": "df.groupby('category').mean() for averages. .agg({'col': ['sum', 'mean']}) for multiple aggregations. .transform() keeps the original row count."},
    {"title": "Pandas · joins", "text": "pd.merge(left, right, on='key', how='inner'|'left'|'outer'). For pivots use df.pivot_table(index=, columns=, values=, aggfunc=)."},
    {"title": "Pandas · time series", "text": "pd.to_datetime(col) parses strings. df.set_index('ts').resample('1D').mean() bins into daily buckets. .rolling(window=7).mean() for moving averages."},
    {"title": "Pandas · fast filtering", "text": "Boolean masks: df[df['x'] > 0]. For multiple conditions chain with & and | with parens around each. Prefer .query('x > 0 and y < 10') for readability."},

    # --- NumPy: numeric arrays, linear algebra -----------------------------
    {"title": "NumPy · array creation", "text": "np.array([...]) from lists, np.zeros(n), np.ones(n), np.arange(start, stop, step), np.linspace(start, stop, N). Prefer vectorized ops over Python loops."},
    {"title": "NumPy · linear algebra", "text": "np.linalg.solve(A, b) for Ax=b. np.linalg.eig(A) for eigenvalues. np.linalg.inv(A) rarely needed — solve() is more stable."},
    {"title": "NumPy · statistics", "text": "arr.mean(), arr.std(), arr.median(). For per-axis pass axis=0 (columns) or axis=1 (rows). np.percentile(arr, [25, 50, 75])."},
    {"title": "NumPy · random sampling", "text": "rng = np.random.default_rng(seed); rng.integers(low, high, size), rng.normal(mu, sigma, size), rng.choice(a, size, replace=False)."},

    # --- SymPy: symbolic math (the "solve this equation" path) -------------
    {"title": "SymPy · declare symbols", "text": "from sympy import symbols; x, y = symbols('x y'). Positive/real hints improve simplification: symbols('x', positive=True, real=True)."},
    {"title": "SymPy · symbolic integration", "text": "from sympy import integrate, exp, oo; integrate(f, x) for indefinite, integrate(f, (x, a, b)) for definite. Use oo for infinity."},
    {"title": "SymPy · symbolic differentiation", "text": "from sympy import diff; diff(f, x, n) for the n-th derivative. Partial derivatives just add more variables: diff(f, x, y)."},
    {"title": "SymPy · solve equations", "text": "from sympy import solve, Eq; solve(Eq(x**2 - 1, 0), x) returns a list of roots. solve([eq1, eq2], [x, y]) for systems."},
    {"title": "SymPy · simplify / expand / factor", "text": "simplify(expr), expand(expr), factor(expr), collect(expr, x), trigsimp(expr) for trigonometric identities."},
    {"title": "SymPy · limits and series", "text": "from sympy import limit, series; limit(f, x, oo) or limit(f, x, 0, '+'). series(f, x, 0, n) for a Taylor expansion around 0 up to order n."},
    {"title": "SymPy · numeric evaluation", "text": ".evalf(precision) converts a symbolic result to a float with N-digit precision. Use N(expr, 30) for arbitrary precision."},

    # --- SciPy: numeric integration, optimization, stats -------------------
    {"title": "SciPy · numeric integration", "text": "from scipy.integrate import quad; quad(f, a, b) returns (value, abserr) for definite integrals of Python callables. For infinite bounds pass np.inf."},
    {"title": "SciPy · ODE integration", "text": "from scipy.integrate import solve_ivp; solve_ivp(rhs, (t0, t1), y0, dense_output=True) for initial-value problems."},
    {"title": "SciPy · optimization", "text": "from scipy.optimize import minimize; minimize(f, x0, method='BFGS'). For bounded/constrained problems use method='SLSQP' and pass bounds=/constraints=."},
    {"title": "SciPy · root finding", "text": "from scipy.optimize import brentq, fsolve; brentq(f, a, b) needs a sign change on [a, b]. fsolve(f, x0) is a Newton-style multivariate solver."},
    {"title": "SciPy · statistics", "text": "from scipy import stats; stats.norm.pdf/cdf, stats.ttest_ind(a, b) for two-sample t-test, stats.pearsonr(x, y) for correlation coefficient."},

    # --- Scikit-learn: classical ML -----------------------------------------
    {"title": "Sklearn · train/test split", "text": "from sklearn.model_selection import train_test_split; X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)."},
    {"title": "Sklearn · classification", "text": "from sklearn.ensemble import RandomForestClassifier; clf = RandomForestClassifier(n_estimators=100, random_state=42); clf.fit(X_tr, y_tr); clf.predict(X_te)."},
    {"title": "Sklearn · regression", "text": "from sklearn.linear_model import LinearRegression, Ridge, Lasso; reg.fit(X, y); reg.predict(X_new). Use Ridge/Lasso for regularization."},
    {"title": "Sklearn · clustering", "text": "from sklearn.cluster import KMeans; km = KMeans(n_clusters=k, random_state=42, n_init='auto'); labels = km.fit_predict(X)."},
    {"title": "Sklearn · scaling", "text": "from sklearn.preprocessing import StandardScaler; sc = StandardScaler(); X_tr_s = sc.fit_transform(X_tr); X_te_s = sc.transform(X_te). Fit on train only."},
    {"title": "Sklearn · metrics", "text": "from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score, confusion_matrix, classification_report."},
    {"title": "Sklearn · pipeline", "text": "from sklearn.pipeline import make_pipeline; pipe = make_pipeline(StandardScaler(), LogisticRegression()); pipe.fit(X, y). Cross-validate the whole pipe with cross_val_score."},

    # --- Statistics / probability (pure stdlib and formulas) ---------------
    {"title": "Statistics · descriptive", "text": "statistics.mean, .median, .stdev, .variance, .quantiles(data, n=4) for quartiles. All work on plain iterables — no numpy needed for small samples."},
    {"title": "Probability · combinations", "text": "math.comb(n, k) for n-choose-k, math.perm(n, k) for permutations, math.factorial(n). All exact integers."},

    # --- Data engineering odds and ends -------------------------------------
    {"title": "CSV · streaming a large file", "text": "import csv; with open(path) as f: for row in csv.DictReader(f): process(row). Never load a multi-GB CSV into memory."},
    {"title": "JSON · parsing", "text": "import json; data = json.loads(text) or json.load(open(path)). Round-trip with json.dumps(obj, indent=2). For streaming JSONL, iterate lines and json.loads each."},
    {"title": "Regex · common patterns", "text": "import re; re.findall(pattern, text) for all matches, re.sub(pattern, repl, text) to substitute. Compile hot patterns: p = re.compile(...)."},
    {"title": "Datetime · parsing / formatting", "text": "from datetime import datetime; datetime.fromisoformat('2024-01-01'), datetime.strptime(s, fmt), dt.isoformat(). Prefer zoneinfo for timezones."},

    # --- Sanity guardrails for the sandbox environment ---------------------
    {"title": "Sandbox constraints", "text": "The sandbox has no network access, a 10-second CPU budget, and no filesystem writes outside /tmp. Avoid subprocess, requests, sockets. Vectorize with numpy/pandas to stay inside the budget."},
    {"title": "Sandbox · allowed libraries", "text": "Only import from: math, statistics, decimal, fractions, json, csv, re, collections, itertools, functools, datetime, hashlib, numpy, pandas, scipy, sklearn, sympy, matplotlib. Everything else is refused by the AST audit."},
]

if __name__ == "__main__":
    print("Downloading embedding model (first-run only)…")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Building FAISS index over {len(CORPUS)} methodology docs…")
    docs = [Document(page_content=e["text"], metadata={"title": e["title"]}) for e in CORPUS]
    vector_db = FAISS.from_documents(docs, embeddings)
    vector_db.save_local("faiss_index")

    print("Done. faiss_index/ is ready — the Researcher will use it on the next task.")
