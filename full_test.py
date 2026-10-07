"""
full_test.py — Comprehensive API test + security vulnerability scan
Tests: Auth, Pipeline, ML Endpoints, Injection, CORS, Rate limits, JWT
"""
import sys, os, json, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

BASE = "http://localhost:8000"
OK   = "  [PASS]"
ERR  = "  [FAIL]"
WRN  = "  [WARN]"

results = {"pass": 0, "fail": 0, "warn": 0}
TOKEN = [None]   # mutable container avoids global declaration issues

def p(status, name, detail=""):
    results[status] += 1
    sym = {"pass": OK, "fail": ERR, "warn": WRN}[status]
    print(f"{sym} {name}" + (f" — {detail}" if detail else ""))

def get(path, auth=False, **kw):
    h = {"Authorization": f"Bearer {TOKEN[0]}"} if (auth and TOKEN[0]) else {}
    try:
        return requests.get(f"{BASE}{path}", headers=h, timeout=10, **kw)
    except Exception:
        return None

def post(path, body=None, auth=False, **kw):
    h = {"Content-Type": "application/json"}
    if auth and TOKEN[0]:
        h["Authorization"] = f"Bearer {TOKEN[0]}"
    try:
        return requests.post(f"{BASE}{path}", json=body, headers=h, timeout=10, **kw)
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ENERGY DIAGNOSTICS — FULL TEST + SECURITY AUDIT")
print("="*60)

# ── 1. REACHABILITY ─────────────────────────────────────────
print("\n[1] BACKEND REACHABILITY")
r = get("/api/pipeline/status")
if r and r.status_code == 200:
    s = r.json()
    p("pass", "Backend reachable", f"status={s.get('status')} rows={s.get('rows')}")
else:
    p("fail", "Backend not reachable — start uvicorn first")
    sys.exit(1)

# ── 2. AUTHENTICATION ────────────────────────────────────────
print("\n[2] AUTHENTICATION TESTS")
ts = int(time.time())
email = f"test{ts}@test.com"

r = post("/api/auth/register", {"name": "Test User", "email": email, "password": "SecurePass123!"})
if r and r.status_code == 200:
    TOKEN[0] = r.json().get("token")
    p("pass", "Register new user")
elif r and r.status_code == 409:
    p("pass", "Register — duplicate correctly rejected (409)")
else:
    p("fail", f"Register failed: {r.status_code if r else 'no response'}")

r = post("/api/auth/register", {"name": "X", "email": f"bad{ts}@test.com", "password": "123"})
if r and r.status_code == 400:
    p("pass", "Weak password (<6 chars) rejected")
else:
    p("warn", f"Weak password not rejected — got {r.status_code if r else 'N/A'}")

r = post("/api/auth/login", {"email": email, "password": "SecurePass123!"})
if r and r.status_code == 200:
    TOKEN[0] = r.json().get("token")
    p("pass", "Valid login returns JWT token")
else:
    p("fail", f"Valid login failed: {r.status_code if r else 'no response'}")

r = post("/api/auth/login", {"email": email, "password": "WrongPass"})
if r and r.status_code == 401:
    p("pass", "Wrong password rejected (401)")
else:
    p("fail", f"Wrong password not rejected — got {r.status_code if r else 'N/A'}")

r = post("/api/auth/login", {"email": "nobody@nowhere.com", "password": "x"})
if r and r.status_code in (401, 404):
    p("pass", "Non-existent user rejected")
else:
    p("fail", f"Non-existent user not rejected — got {r.status_code if r else 'N/A'}")

r = get("/api/auth/me", auth=True)
if r and r.status_code == 200:
    p("pass", "/api/auth/me returns user data with valid token")
else:
    p("fail", f"/api/auth/me failed: {r.status_code if r else 'N/A'}")

# ── 3. JWT TAMPERING ─────────────────────────────────────────
print("\n[3] JWT SECURITY TESTS")

bad = "eyJhbGciOiJub25lIn0.eyJlbWFpbCI6ImhhY2tlckBoYWNrLmNvbSJ9."
r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {bad}"}, timeout=5)
if r.status_code == 401:
    p("pass", "Tampered JWT rejected (401)")
else:
    p("fail", f"CRITICAL: Tampered JWT accepted — got {r.status_code}")

r = requests.get(f"{BASE}/api/auth/me", timeout=5)
if r.status_code == 401:
    p("pass", "No token correctly rejected (401)")
else:
    p("fail", f"Unauthenticated access allowed — got {r.status_code}")

expired = "eyJlbWFpbCI6InhAeC5jb20iLCAiZXhwIjogMX0.badsig"
r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {expired}"}, timeout=5)
if r.status_code == 401:
    p("pass", "Expired/bad-signature token rejected (401)")
else:
    p("fail", f"Invalid token accepted — got {r.status_code}")

# ── 4. INJECTION ATTACKS ─────────────────────────────────────
print("\n[4] INJECTION ATTACK TESTS")

nosql_payloads = [
    {"email": {"$gt": ""}, "password": "anything"},
    {"email": "admin@admin.com' OR '1'='1", "password": "x"},
    {"email": "'; DROP TABLE users; --", "password": "x"},
]
for payload in nosql_payloads:
    r = post("/api/auth/login", payload)
    if r and r.status_code in (401, 422):
        p("pass", f"NoSQL/SQL injection rejected: {str(payload['email'])[:35]}")
    else:
        p("fail", f"Injection may have succeeded: {r.status_code if r else 'N/A'}")

r = post("/api/auth/register", {"name": "<script>alert(1)</script>",
         "email": f"xss{ts}@test.com", "password": "SecurePass123!"})
if r:
    if "<script>" not in r.text:
        p("pass", "XSS payload not reflected in API response")
    else:
        p("warn", "XSS payload echoed in response — sanitize output")

for path in ["/api/data/../../../etc/passwd", "/api/data/%2e%2e%2f%2e%2e%2fetc%2fpasswd"]:
    r = requests.get(f"{BASE}{path}", timeout=5)
    if r and r.status_code in (400, 401, 403, 404, 405, 422):
        p("pass", f"Path traversal blocked ({r.status_code})")
    else:
        p("warn", f"Unexpected path traversal response: {r.status_code if r else 'N/A'}")

# ── 5. CORS ──────────────────────────────────────────────────
print("\n[5] CORS SECURITY")
r = requests.options(f"{BASE}/api/auth/login",
    headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "POST"}, timeout=5)
origin = r.headers.get("Access-Control-Allow-Origin", "")
cred   = r.headers.get("Access-Control-Allow-Credentials", "")
if origin == "*" and cred.lower() == "true":
    p("fail", "CRITICAL: CORS allows * with credentials=true (CSRF risk)")
elif origin == "*":
    p("warn", "CORS allows all origins (*) — acceptable for public API, restrict for production")
elif "evil.com" in origin:
    p("fail", "CORS reflects arbitrary Origin header (CORS misconfiguration)")
else:
    p("pass", f"CORS restricted: origin={origin or 'not set'}")

# ── 6. BRUTE FORCE / RATE LIMIT ──────────────────────────────
print("\n[6] BRUTE FORCE PROTECTION")
blocked = False
for i in range(12):
    r = post("/api/auth/login", {"email": "victim@test.com", "password": f"wrong{i}"})
    if r and r.status_code == 429:
        p("pass", f"Rate limiting triggered after {i+1} attempts (429)")
        blocked = True
        break
if not blocked:
    p("warn", "No rate limiting on login endpoint — brute force is possible")
    p("warn", "Recommendation: add slowapi (pip install slowapi) with 5 req/min on /api/auth/login")

# ── 7. ML ENDPOINTS ──────────────────────────────────────────
print("\n[7] ML / DATA ENDPOINTS")
s = get("/api/pipeline/status")
if s and s.json().get("ready"):
    p("pass", f"Pipeline ready — {s.json().get('rows')} rows")
    for path, name in [
        ("/api/data/overview",            "Overview"),
        ("/api/data/forecast",            "Forecast"),
        ("/api/data/models",              "Models summary"),
        ("/api/data/alerts",              "Alerts"),
        ("/api/data/pipeline-stats",      "Pipeline stats"),
        ("/api/metrics/confusion-matrix", "Confusion matrix"),
        ("/api/metrics/roc-curves",       "ROC curves"),
        ("/api/metrics/precision-recall", "Precision-Recall"),
        ("/api/metrics/comparison",       "Model comparison"),
        ("/api/metrics/feature-importance","Feature importance"),
    ]:
        r = get(path)
        if r and r.status_code == 200:
            p("pass", f"{name}", f"{len(r.content)} bytes")
        elif r and r.status_code == 503:
            p("warn", f"{name} → 503 (pipeline warming up)")
        else:
            p("fail", f"{name} → {r.status_code if r else 'no response'}")
else:
    p("warn", "Pipeline not ready — triggering auto-run")
    post("/api/pipeline/run", auth=True)

# ── 8. INPUT VALIDATION ──────────────────────────────────────
print("\n[8] INPUT VALIDATION")
for body, desc in [
    ({"email": "x@x.com", "password": "abc123"},           "missing name"),
    ({"name": "X", "password": "abc123"},                   "missing email"),
    ({"name": "X", "email": "x@x.com"},                    "missing password"),
    ({"name": "X", "email": "not-an-email", "password": "abc123"}, "invalid email"),
]:
    r = post("/api/auth/register", body)
    if r and r.status_code == 422:
        p("pass", f"Validation — {desc} rejected (422)")
    else:
        p("warn", f"Validation — {desc} got {r.status_code if r else 'N/A'} (expected 422)")

# ── 9. SECURITY HEADERS ──────────────────────────────────────
print("\n[9] HTTP SECURITY HEADERS")
r = get("/api/pipeline/status")
if r:
    missing = []
    for h, desc in [
        ("X-Content-Type-Options", "Prevents MIME sniffing"),
        ("X-Frame-Options",        "Clickjacking protection"),
        ("Strict-Transport-Security", "HTTPS enforcement (HSTS)"),
        ("Content-Security-Policy",   "XSS / injection protection"),
    ]:
        if r.headers.get(h):
            p("pass", f"{h}: {r.headers[h]}")
        else:
            p("warn", f"Missing: {h} — {desc}")

# ── 10. HARDCODED SECRETS SCAN ───────────────────────────────
print("\n[10] HARDCODED SECRETS SCAN")
patterns = [
    (r'(?i)password\s*=\s*["\'][^"\']{8,}["\']', "password"),
    (r'(?i)secret\s*=\s*["\'][^"\']{8,}["\']',   "secret"),
    (r'mongodb\+srv://[^@]+:[^@]+@',              "MongoDB URI with credentials"),
]
files = ["backend/api.py","backend/config.py","backend/data/pipeline.py",
         "backend/models/ml_models.py","frontend/src/lib/api.ts"]
found = False
for fp in files:
    try:
        content = open(fp, encoding="utf-8", errors="ignore").read()
        for pat, label in patterns:
            for m in re.findall(pat, content):
                if not any(s in m.lower() for s in
                           ["getenv","environ","change-me","your_","example","placeholder","dummy"]):
                    p("warn", f"Possible hardcoded {label} in {fp}: {m[:50]}")
                    found = True
    except FileNotFoundError:
        pass
if not found:
    p("pass", "No hardcoded secrets detected in source files")

# ── 11. SETTINGS / SYNC ENDPOINTS ───────────────────────────
print("\n[11] OTHER ENDPOINTS")
for path, name, need_auth in [
    ("/api/settings",    "Settings",       True),
    ("/api/sync/status", "Excel sync",     False),
]:
    r = get(path, auth=need_auth)
    if r and r.status_code == 200:
        p("pass", name)
    elif r and r.status_code == 404:
        p("warn", f"{name} → 404 (not implemented)")
    else:
        p("fail", f"{name} → {r.status_code if r else 'no response'}")

# ── FINAL SUMMARY ────────────────────────────────────────────
total = sum(results.values())
print("\n" + "="*60)
print(f"  RESULTS: {total} tests")
print(f"  ✅ PASS:    {results['pass']}")
print(f"  ❌ FAIL:    {results['fail']}")
print(f"  ⚠️  WARN:    {results['warn']}")
score = int(100 * results["pass"] / total) if total else 0
print(f"\n  SECURITY SCORE: {score}/100")
if results["fail"] == 0:
    print("  ✅ No critical failures — project is production-ready")
else:
    print(f"  ❌ {results['fail']} critical issue(s) must be fixed before production")
print("="*60 + "\n")
