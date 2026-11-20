# Changelog

## 0.4.0 - 2026-11-20

- Several areas to read: in the *Area to read* dialog you can draw any number of rectangles; *Remove last* and
  *Remove all* take them away, and with no rectangle the whole picture is read. All areas are put into one picture and
  read in one pass.
- The setting is now `regions`, a list of areas. A `region` from version 0.3.0 is converted on the first start.
- The window says that it is preparing the translation model, which can take a while after the model was unloaded.

## 0.3.0 - 2026-11-20

- Area to read: *Choose...* in the window shows the current picture of the game source and lets you drag a rectangle
  around the part to translate. Only that part is read; text outside it is ignored. *Whole picture* switches back. The
  area can be changed while translating. It is stored in `settings.json` as `region`.
- `--preview` marks the area in `preview.png`.

## 0.2.0 - 2026-11-20

- The program has a window: the languages are chosen from lists (164 entries from the TranslateGemma language table), the game
  source from the list of sources in OBS, and Start and Stop are buttons. Changing a language while translating restarts
  the translation in the new language.
- Installer `OBS-Screen-Translator-Setup-<version>.exe` (Inno Setup, per user, no administrator rights), built by
  `build.ps1` from a PyInstaller bundle. Python is no longer needed to use the program.
- Text is read on the graphics card through DirectML (`onnxruntime-directml`) instead of PyTorch with CUDA, so any
  DirectX 12 card works and the bundle stays small. If that fails, the processor is used.
- `settings.json` is created on the first start (in `%APPDATA%\OBS Screen Translator` for the installed program);
  `settings.example.json` is gone. The languages are stored as codes.
- On start the program starts Ollama if it is installed but not running, and downloads the translation model if it is
  missing. Problems such as a missing Ollama or OBS are reported in the window.
- The address of the overlay source is kept current, so the source survives a reinstall into another folder.
- README states plainly that the project is vibe-coded.

## 0.1.0 - 2026-11-19

Initial public release.

- `translator.py`: reads frames of an OBS source through the OBS WebSocket server, finds text in the whole frame with
  RapidOCR (GPU through PyTorch and CUDA, or CPU), joins lines into blocks and translates them with a TranslateGemma model
  served by Ollama.
- Translations are published on a local WebSocket and drawn by `overlay.html`, an OBS browser source, over the original
  text on a black semi-transparent background.
- Only new text is translated; translations are cached on disk. Short labels are translated in batches.
- A translation appears after its text has been read twice at the same place, so moving text in the game world is skipped.
- The overlay source is created on the first run. Hiding it pauses reading and translating.
- `--preview`, `--image` and `--settings`; `settings.example.json` with the source and target language, the context
  sentence, the model and the reading thresholds.
