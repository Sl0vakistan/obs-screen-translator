# Builds dist\OBS Screen Translator\ (the program) and dist\OBS-Screen-Translator-Setup-<version>.exe (the installer).
# Needs Python 3.10+ (py launcher) and, for the installer, Inno Setup 6 (winget install JRSoftware.InnoSetup).
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$name = 'OBS Screen Translator'
$version = (Get-Content "$root\VERSION").Trim()
$python = "$root\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) { py -3 -m venv "$root\.venv" }
& $python -m pip install --quiet --disable-pip-version-check -r "$root\requirements.txt" pyinstaller
if ($LASTEXITCODE) { throw 'pip failed' }

# The text-reading models are downloaded into the rapidocr package on first use; do it now so they get bundled.
& $python -W ignore -c "import numpy; from rapidocr import RapidOCR; RapidOCR(params={'Global.use_cls': False, 'Global.log_level': 'error'})(numpy.zeros((64, 256, 3), numpy.uint8))"
if ($LASTEXITCODE) { throw 'downloading the text-reading models failed' }

Remove-Item "$root\build", "$root\dist" -Recurse -Force -ErrorAction SilentlyContinue
& $python -m PyInstaller --noconfirm --clean --windowed --log-level WARN --name $name `
    --distpath "$root\dist" --workpath "$root\build" --specpath "$root\build" `
    --add-data "$root\overlay.html;." --add-data "$root\languages.json;." --add-data "$root\CHANGELOG.md;." `
    --collect-data rapidocr --collect-data sv_ttk --collect-submodules rapidocr --collect-submodules websockets `
    "$root\translator.py"
if ($LASTEXITCODE) { throw 'PyInstaller failed' }

# Parts the program never uses: OpenCV's video library, Pillow's AVIF module and the text-rotation model.
Remove-Item "$root\dist\$name\_internal\cv2\opencv_videoio_ffmpeg*.dll", "$root\dist\$name\_internal\PIL\_avif*.pyd",
    "$root\dist\$name\_internal\rapidocr\models\*_cls_*.onnx"

# License texts of everything that is bundled, as shipped by each package.
@'
import importlib.metadata as md, pathlib, re, shutil, sys
out = pathlib.Path(sys.argv[1])
out.mkdir()
skip = {"pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes", "pip", "setuptools", "packaging"}
rows = []
for d in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = d.metadata["Name"]
    if name.lower() in skip:
        continue
    lic = d.metadata.get("License-Expression") or (d.metadata.get("License") or "").split("\n")[0][:60] or \
        "; ".join(c.split(" :: ")[-1] for c in d.metadata.get_all("Classifier", []) if c.startswith("License"))
    rows.append(f"{name} {d.version}: {lic or 'see the files in its folder'}")
    for f in d.files or []:
        if re.search(r"(licen[cs]e|copying|notice|authors)", f.name, re.I) and ".dist-info" in str(f):
            target = out / f"{name}-{d.version}"
            target.mkdir(exist_ok=True)
            shutil.copy2(d.locate_file(f), target / f.name)
shutil.copy2(pathlib.Path(sys.base_prefix) / "LICENSE.txt", out / "Python-LICENSE.txt")
rows.append(f"Python {sys.version.split()[0]} with Tcl/Tk: PSF-2.0 and the Tcl/Tk license, see Python-LICENSE.txt")
rows.append("PyInstaller bootloader: GPL-2.0-or-later with an exception that allows distributing bundled programs under any license")
(out / "README.txt").write_text("Third-party software bundled with OBS Screen Translator, with the license each package declares.\n"
                                "The license texts shipped by the packages are in the folders next to this file.\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
print(len(rows), "bundled components listed")
'@ | & $python - "$root\dist\$name\licenses"
if ($LASTEXITCODE) { throw 'collecting licenses failed' }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    & $iscc /Q "/DAppVersion=$version" "$root\installer.iss"
    if ($LASTEXITCODE) { throw 'Inno Setup failed' }
    Get-Item "$root\dist\OBS-Screen-Translator-Setup-$version.exe" | ForEach-Object { '{0}  {1:N1} MB' -f $_.FullName, ($_.Length / 1MB) }
} else {
    'Inno Setup not found: the program is in dist\, the installer was not built.'
}
