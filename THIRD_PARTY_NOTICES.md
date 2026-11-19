# Third-party notices

The code of this project is licensed under the MIT License (see [LICENSE](LICENSE)). The repository contains no third-party
code, models or media. This file lists the third-party software and models the tool uses at run time without redistributing
them. Licenses are given as published by the projects at the time of writing; check the upstream project before relying on
them.

## Installed by the user

| software | used for | license |
|---|---|---|
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | text detection and recognition | Apache-2.0 |
| [PP-OCR models](https://github.com/PaddlePaddle/PaddleOCR) (downloaded by RapidOCR on first use) | text detection and recognition models | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | running the models on the CPU | MIT |
| [PyTorch](https://github.com/pytorch/pytorch) (optional) | running the models on the GPU | BSD-3-Clause |
| [OpenCV](https://github.com/opencv/opencv) | decoding and drawing images | Apache-2.0 |
| [NumPy](https://github.com/numpy/numpy) | image arrays | BSD-3-Clause |
| [websockets](https://github.com/python-websockets/websockets) | connection to OBS and to the overlay | BSD-3-Clause |
| [Ollama](https://github.com/ollama/ollama) | serving the translation model | MIT |
| [TranslateGemma](https://ollama.com/library/translategemma) | translation model | Gemma Terms of Use |

## Used through its interface

| software | used for | license |
|---|---|---|
| [OBS Studio](https://github.com/obsproject/obs-studio) with its WebSocket server | source of the frames, host of the overlay | GPL-2.0-or-later |

The tool talks to OBS Studio over its WebSocket protocol and is loaded by OBS only as a web page in a browser source. It
contains no OBS code.

## Trademarks

Names of products and games are trademarks of their owners and are used only to describe what the tool works with.
