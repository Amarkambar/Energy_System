"""
build_installer.py — Pre-build script for Windows installer
Run BEFORE Inno Setup: python installer/build_installer.py

What it does:
1. Builds the React frontend (npm run build)
2. Copies frontend/dist → backend/static (so FastAPI can serve it)
3. Generates a default app icon if none exists
4. Runs Inno Setup to produce the .exe installer
"""

import os, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")
BACKEND_STATIC = os.path.join(ROOT, "backend", "static")
INSTALLER_DIR = os.path.join(ROOT, "installer")
ISCC = r"C:\Program Files\Inno Setup 7\ISCC.exe"

def step(msg): print(f"\n{'='*55}\n  {msg}\n{'='*55}")
def ok(msg):   print(f"  [OK]  {msg}")
def err(msg):  print(f"  [ERR] {msg}"); sys.exit(1)

# ── Step 1: Build frontend ────────────────────────────────────────────────────
step("STEP 1 — Building React frontend")
npm = "npm.cmd" if sys.platform == "win32" else "npm"
result = subprocess.run([npm, "run", "build"],
                        cwd=os.path.join(ROOT, "frontend"),
                        capture_output=True, text=True)
if result.returncode != 0:
    print(result.stdout[-2000:])
    print(result.stderr[-2000:])
    err("Frontend build failed — fix errors above and retry")
ok(f"Frontend built → {FRONTEND_DIST}")

# ── Step 2: Copy dist → backend/static ───────────────────────────────────────
import stat

def _force_remove(func, path, exc):
    """Handle read-only files during rmtree (needed for OneDrive folders)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

step("STEP 2 — Copying frontend dist to backend/static")
if os.path.exists(BACKEND_STATIC):
    shutil.rmtree(BACKEND_STATIC, onerror=_force_remove)
shutil.copytree(FRONTEND_DIST, BACKEND_STATIC)
ok(f"Copied {len(os.listdir(BACKEND_STATIC))} items to backend/static/")


# ── Step 3: Create installer/dist folder ─────────────────────────────────────
step("STEP 3 — Preparing installer output folder")
dist_out = os.path.join(INSTALLER_DIR, "dist")
os.makedirs(dist_out, exist_ok=True)

# Create a placeholder icon if none present
icon_path = os.path.join(INSTALLER_DIR, "app_icon.ico")
if not os.path.exists(icon_path):
    # Copy favicon from static if available
    favicon = os.path.join(BACKEND_STATIC, "favicon.ico")
    if os.path.exists(favicon):
        shutil.copy(favicon, icon_path)
        ok("Copied favicon.ico as app icon")
    else:
        # Create minimal 1x1 ICO (valid Windows icon)
        ico_bytes = bytes([
            0,0,1,0,1,0,1,1,0,0,1,0,8,0,40,0,0,0,22,0,0,0,
            40,0,0,0,1,0,0,0,2,0,0,0,1,0,8,0,0,0,0,0,1,0,0,0,
            0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,131,4,0
        ])
        with open(icon_path, "wb") as f: f.write(ico_bytes)
        ok("Created placeholder icon")

# Create a placeholder wizard banner (494x58 BMP) if none present
banner = os.path.join(INSTALLER_DIR, "wizard_banner.bmp")
if not os.path.exists(banner):
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (494, 58), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Energy Diagnostics System", fill=(99, 230, 190))
        draw.text((10, 35), "AI-powered industrial energy monitoring", fill=(148, 163, 184))
        img.save(banner, "BMP")
        ok("Created wizard banner with Pillow")
    except ImportError:
        # Minimal 494x58 white BMP header
        w, h = 494, 58
        row = bytes([220, 200, 255] * w)
        row_padded = row + bytes((4 - (w * 3) % 4) % 4)
        bmp = (b'BM' + (54 + len(row_padded)*h).to_bytes(4,'little') +
               b'\x00\x00\x00\x00' + (54).to_bytes(4,'little') +
               (40).to_bytes(4,'little') + w.to_bytes(4,'little') +
               (-h & 0xFFFFFFFF).to_bytes(4,'little') + b'\x01\x00\x18\x00' +
               b'\x00'*24 + row_padded * h)
        with open(banner, "wb") as f: f.write(bmp)
        ok("Created minimal wizard banner (install Pillow for a nicer one)")

# ── Step 4: Run Inno Setup ────────────────────────────────────────────────────
step("STEP 4 — Running Inno Setup compiler")
if not os.path.exists(ISCC):
    err(f"Inno Setup not found at:\n  {ISCC}\nInstall from https://jrsoftware.org/isdl.php")

iss_file = os.path.join(INSTALLER_DIR, "setup.iss")
result = subprocess.run([ISCC, iss_file], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
print(result.stdout[-3000:])
if result.returncode != 0:
    print(result.stderr[-1000:])
    err("Inno Setup compilation failed")

exe_files = [f for f in os.listdir(dist_out) if f.endswith(".exe")]
if exe_files:
    exe_path = os.path.join(dist_out, exe_files[0])
    size_mb = os.path.getsize(exe_path) / 1024 / 1024
    print(f"\n{'='*55}")
    print(f"  SUCCESS!")
    print(f"  Installer: {exe_path}")
    print(f"  Size:      {size_mb:.1f} MB")
    print(f"{'='*55}\n")
else:
    err("No .exe found in installer/dist — check Inno Setup output above")
