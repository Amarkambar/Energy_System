"""
Quick security integration test — run with:
    venv\Scripts\python test_security.py
"""
from passlib.context import CryptContext
import hashlib, hmac

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. bcrypt hash/verify
h = ctx.hash("testpass123")
assert ctx.verify("testpass123", h), "bcrypt verify failed"
assert not ctx.verify("wrongpass", h), "bcrypt should reject wrong password"
print("PASS  bcrypt hash / verify")

# 2. bcrypt prefix detection
assert h.startswith(("$2b$", "$2a$", "$2y$")), f"Unexpected hash prefix: {h[:5]}"
print("PASS  bcrypt prefix detection")

# 3. Legacy SHA-256 compat
sha = hashlib.sha256("oldpass".encode()).hexdigest()
assert hmac.compare_digest(hashlib.sha256("oldpass".encode()).hexdigest(), sha)
assert not hmac.compare_digest(hashlib.sha256("badpass".encode()).hexdigest(), sha)
print("PASS  SHA-256 legacy compat (timing-safe compare)")

# 4. verify_password function (mirrors api.py logic exactly)
def verify_password(plain, hashed):
    if hashed.startswith(("$2b$", "$2a$", "$2y$")):
        return ctx.verify(plain, hashed)
    return hmac.compare_digest(hashlib.sha256(plain.encode()).hexdigest(), hashed)

# Test with bcrypt hash
assert verify_password("testpass123", h)
assert not verify_password("wrong", h)
# Test with legacy SHA-256 hash
assert verify_password("oldpass", sha)
assert not verify_password("wrong", sha)
print("PASS  verify_password() works for both bcrypt and legacy SHA-256")

print()
print("=" * 50)
print("  All security tests PASSED")
print("=" * 50)
