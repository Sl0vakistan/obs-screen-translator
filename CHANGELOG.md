# Changelog

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
