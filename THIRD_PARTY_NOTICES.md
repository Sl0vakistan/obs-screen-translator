# Third-party notices

The code of this project is licensed under the MIT License (see [LICENSE](LICENSE)). The repository contains only this
project's own code. The installer and the program built by `build.ps1` bundle third-party software, each under its own
license. Licenses are given as declared by the packages at build time; check the upstream project before relying on them.

## Bundled in the installer

`build.ps1` writes the complete list, with versions and the license each package declares, to `licenses\README.txt` in the
program folder, and copies the license texts shipped by the packages next to it. The main components:

| software | used for | license |
|---|---|---|
| [Python](https://www.python.org/) with Tcl/Tk | running the program, the window | PSF-2.0, Tcl/Tk license |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | text detection and recognition | Apache-2.0 |
| [PP-OCR models](https://github.com/PaddlePaddle/PaddleOCR) (`PP-OCRv6_det_small`, `PP-OCRv6_rec_small`) | text detection and recognition models | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) with [DirectML](https://github.com/microsoft/DirectML) | running the models on the graphics card or processor | MIT |
| [OpenCV](https://github.com/opencv/opencv) (`opencv-python-headless`) | decoding and drawing images | Apache-2.0; the FFmpeg video library that comes with the package is left out of the program |
| [NumPy](https://github.com/numpy/numpy) | image arrays | BSD-3-Clause and others listed by the package |
| [websockets](https://github.com/python-websockets/websockets) | connection to OBS and to the overlay | BSD-3-Clause |
| [Sun Valley ttk theme](https://github.com/rdbende/Sun-Valley-ttk-theme) (`sv-ttk`) | look of the windows | MIT |
| [Shapely](https://github.com/shapely/shapely) | geometry of text boxes | BSD-3-Clause; the package ships GEOS under LGPL-2.1 |
| Pillow, pyclipper, OmegaConf, PyYAML, requests, urllib3, certifi, charset-normalizer, idna, tqdm, colorlog, six and others | dependencies of the above | see `licenses\README.txt` |
| [PyInstaller](https://pyinstaller.org/) bootloader | starting the bundled program | GPL-2.0-or-later with an exception that allows distributing bundled programs under any license |

The LGPL library (GEOS) is shipped as a separate file inside the program folder and can be replaced there.

## Installed separately, not bundled

| software | used for | license |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) (installed by the user, or downloaded from ollama.com by the program when the user agrees) | serving the translation model | MIT |
| [TranslateGemma](https://ollama.com/library/translategemma) (downloaded by Ollama on the first start) | translation model | Gemma Terms of Use |
| [OBS Studio](https://github.com/obsproject/obs-studio) with its WebSocket server | source of the frames, host of the overlay | GPL-2.0-or-later |

The program talks to OBS Studio over its WebSocket protocol and is loaded by OBS only as a web page in a browser source. It
contains no OBS code.

## Tools used to build

[Inno Setup](https://jrsoftware.org/isinfo.php) builds the installer (Inno Setup License).

## Trademarks

Names of products and games are trademarks of their owners and are used only to describe what the program works with.
