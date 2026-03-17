"""
build.py — Builds car_scanner.exe then packages it as a .msi installer.

Requirements (install once):
    pip install pyinstaller
    Download & install WiX Toolset v3: https://github.com/wixtoolset/wix3/releases

Usage:
    python build.py
"""

import os
import re
import sys
import subprocess
import hashlib
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
APP_NAME     = "EngineScannerAI"
APP_VERSION  = "1.0.0"
MAIN_SCRIPT  = "car_scanner.py"
ICON_FILE    = "car.jpj.ico"
MANUFACTURER = "Piyush Productions"
UPGRADE_CODE = "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
# ─────────────────────────────────────────────────────────────────────────────

ROOT     = Path(__file__).parent
EXE_DIR  = ROOT / "dist" / APP_NAME
EXE_PATH = EXE_DIR / f"{APP_NAME}.exe"
WXS_PATH = ROOT / f"{APP_NAME}.wxs"
MSI_PATH = ROOT / f"{APP_NAME}-{APP_VERSION}-setup.msi"


def step(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def sanitize_id(s):
    """Strip all chars not allowed in WiX identifiers, ensure starts with letter/underscore."""
    s = re.sub(r'[^A-Za-z0-9_]', '_', s)   # replace EVERYTHING except letters, digits, underscore
    if s and (s[0].isdigit()):
        s = '_' + s
    return s[:72]


def generate_guid(seed):
    h = hashlib.md5(seed.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}".upper()


# ── Step 1: PyInstaller ───────────────────────────────────────────────────────

def build_exe():
    step("Building .exe with PyInstaller")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onedir",
        f"--name={APP_NAME}",
        "--windowed", "--clean",
        "--hidden-import=PIL._tkinter_finder",
    ]
    if Path(ICON_FILE).exists():
        cmd += [f"--icon={ICON_FILE}"]
    cmd.append(MAIN_SCRIPT)

    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        print("\n❌  PyInstaller failed."); sys.exit(1)
    if not EXE_PATH.exists():
        print(f"\n❌  Exe not found: {EXE_PATH}"); sys.exit(1)
    print(f"\n✅  Exe built: {EXE_PATH}")


# ── Step 2: Generate .wxs ────────────────────────────────────────────────────

def generate_wxs():
    step("Generating WiX source (.wxs)")

    file_entries  = []
    dir_entries   = []
    component_ids = []
    used_ids      = {}

    def unique_id(raw):
        base = sanitize_id(raw)
        if not base:
            base = "_item"
        if base not in used_ids:
            used_ids[base] = 0
            return base
        used_ids[base] += 1
        return sanitize_id(f"{base}_{used_ids[base]}")

    dir_id_map = {Path("."): "INSTALLFOLDER"}

    for root, dirs, files in os.walk(EXE_DIR):
        rel_root = Path(root).relative_to(EXE_DIR)

        if rel_root not in dir_id_map:
            raw = "dir_" + str(rel_root).replace(os.sep, "_")
            dir_id_map[rel_root] = unique_id(raw)

        dir_id = dir_id_map[rel_root]

        if rel_root != Path("."):
            parent_rel = rel_root.parent
            parent_id  = dir_id_map.get(parent_rel, "INSTALLFOLDER")
            dir_entries.append((dir_id, parent_id, rel_root.name))

        for d in dirs:
            sub = rel_root / d
            if sub not in dir_id_map:
                dir_id_map[sub] = unique_id("dir_" + str(sub).replace(os.sep, "_"))

        for fname in files:
            fpath   = Path(root) / fname
            rel_key = str(rel_root / fname)
            file_id = unique_id("file_" + rel_key.replace(os.sep, "_"))
            comp_id = unique_id("comp_" + rel_key.replace(os.sep, "_"))
            guid    = generate_guid(rel_key)
            component_ids.append(comp_id)
            file_entries.append((comp_id, guid, dir_id, file_id, str(fpath)))

    # Directory XML
    children = {}
    for did, pid, name in dir_entries:
        children.setdefault(pid, []).append((did, name))

    def render_dirs(parent_id, indent=8):
        lines = []
        for did, name in children.get(parent_id, []):
            lines.append(" " * indent + f'<Directory Id="{did}" Name="{name}">')
            lines.extend(render_dirs(did, indent + 2))
            lines.append(" " * indent + "</Directory>")
        return lines

    dir_xml = "\n".join(render_dirs("INSTALLFOLDER"))

    # Component XML
    comp_parts = []
    for comp_id, guid, dir_id, file_id, fpath in file_entries:
        shortcut = ""
        if fpath.endswith(f"{APP_NAME}.exe"):
            shortcut = f"""
            <Shortcut Id="DesktopShortcut" Directory="DesktopFolder"
                      Name="{APP_NAME}" WorkingDirectory="{dir_id}"
                      Icon="AppIcon.exe" IconIndex="0" Advertise="yes"/>
            <Shortcut Id="StartMenuShortcut" Directory="ProgramMenuFolder"
                      Name="{APP_NAME}" WorkingDirectory="{dir_id}"
                      Icon="AppIcon.exe" IconIndex="0" Advertise="yes"/>"""

        comp_parts.append(f"""
    <DirectoryRef Id="{dir_id}">
      <Component Id="{comp_id}" Guid="{guid}">
        <File Id="{file_id}" Source="{fpath}" KeyPath="yes">{shortcut}
        </File>
      </Component>
    </DirectoryRef>""")

    comp_xml = "\n".join(comp_parts)
    ref_xml  = "\n      ".join(f'<ComponentRef Id="{c}"/>' for c in component_ids)
    icon_line = f'<Icon Id="AppIcon.exe" SourceFile="{ICON_FILE}"/>' if Path(ICON_FILE).exists() else ""

    wxs = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="{APP_NAME}" Language="1033" Version="{APP_VERSION}"
           Manufacturer="{MANUFACTURER}" UpgradeCode="{UPGRADE_CODE}">

    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine"/>
    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed."/>
    <MediaTemplate EmbedCab="yes"/>

    {icon_line}
    <Property Id="ARPPRODUCTICON" Value="AppIcon.exe"/>

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="{APP_NAME}">
{dir_xml}
        </Directory>
      </Directory>
      <Directory Id="DesktopFolder"/>
      <Directory Id="ProgramMenuFolder"/>
    </Directory>

{comp_xml}

    <Feature Id="ProductFeature" Title="{APP_NAME}" Level="1">
      {ref_xml}
    </Feature>

  </Product>
</Wix>
"""
    WXS_PATH.write_text(wxs, encoding="utf-8")
    print(f"✅  WiX source written: {WXS_PATH}")


# ── Step 3: Compile .wxs → .msi ──────────────────────────────────────────────

def build_msi():
    step("Compiling .msi with WiX")
    wixobj = ROOT / f"{APP_NAME}.wixobj"

    r1 = subprocess.run(["candle.exe", str(WXS_PATH), "-o", str(wixobj)], cwd=ROOT)
    if r1.returncode != 0:
        print("\n❌  candle.exe failed."); sys.exit(1)

    r2 = subprocess.run(
        ["light.exe", str(wixobj), "-o", str(MSI_PATH),
         "-ext", "WixUIExtension", "-cultures:en-us"],
        cwd=ROOT,
    )
    if r2.returncode != 0:
        print("\n❌  light.exe failed."); sys.exit(1)

    wixobj.unlink(missing_ok=True)
    WXS_PATH.unlink(missing_ok=True)
    print(f"\n✅  MSI ready: {MSI_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🚗  Building {APP_NAME} v{APP_VERSION} installer\n")

    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    build_exe()
    generate_wxs()
    build_msi()

    print(f"""
╔══════════════════════════════════════════════════╗
║  ✅  BUILD COMPLETE                              ║
║                                                  ║
║  Installer: {str(MSI_PATH.name):<37}║
║                                                  ║
║  Share this .msi — users just double-click       ║
║  to install. No Python required!                 ║
╚══════════════════════════════════════════════════╝
""")
