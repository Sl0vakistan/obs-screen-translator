# OBS Screen Translator

Live translation of on-screen text for streamers. The tool reads the text in an [OBS Studio](https://obsproject.com/) source
(a game from a capture card, a game capture, a window), translates it with a language model running on your own PC and draws
the translation over the original text, on a black semi-transparent background. Viewers see subtitles, messages, hints and
menus in their language; nothing leaves your computer.

Slovak version: [README.sk.md](README.sk.md)

Open source under the MIT License, see [LICENSE](LICENSE).

## How it works

1. Four times a second the tool asks OBS for a frame of the game source through the built-in WebSocket server.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (PP-OCR models) finds and reads the text in the whole frame, on the GPU
   or on the CPU.
3. Lines that belong together (a two-line subtitle, a paragraph of a message) are joined into one block.
4. A block is translated by [TranslateGemma](https://ollama.com/library/translategemma) served by
   [Ollama](https://ollama.com/). Sentences go one at a time as soon as they appear; short labels such as menu items go in
   batches of up to 12.
5. A browser source in OBS (`overlay.html`) receives the translations over a local WebSocket and draws each one at the place
   of the text it replaces.

Only new text reaches the model. A text that stays on screen is translated once, and every translation is stored in a cache
file, so a menu seen before appears at once, also after a restart.

A translation is shown only after its text has been read twice at the same place. Text that moves with the camera, such as
signs and number plates in the game world, is therefore left alone until the picture stands still.

## Requirements

- Windows 10 or 11. The tool was developed and tested on Windows 11 only.
- OBS Studio 28 or newer with the WebSocket server enabled (*Tools > WebSocket Server Settings*).
- Python 3.10 or newer.
- Ollama with a TranslateGemma model. `translategemma:12b` needs about 7.5 GB of GPU memory, `translategemma:4b` about
  2.7 GB and translates noticeably worse.
- Optional: an NVIDIA GPU and PyTorch with CUDA for reading text on the GPU. Without it the reading runs on the CPU and
  keeps several cores busy.

## Installation

```
py -3 -m pip install -r requirements.txt
ollama pull translategemma:12b
copy settings.example.json settings.json
```

For reading text on the GPU install PyTorch with CUDA as described on [pytorch.org](https://pytorch.org/get-started/locally/).
Otherwise set `ocr_on_gpu` to `false` in `settings.json`.

In `settings.json` set `obs_source` to the name of the OBS source that shows the game.

The first start downloads the text-reading models (tens of megabytes).

## Usage

Start OBS, then run `start-translator.cmd`. On the first run the tool adds a browser source named *Translation overlay* to
the current scene, or to the scenes listed in `scenes`. Keep the window open; it prints every translated text with the time
it took. Closing the window removes the translations from the picture.

The tool works only while the overlay source is visible in the scene that is on air. Hide the source and the tool stops
reading and translating until you show it again. To switch it with one key, open *Settings > Hotkeys* in OBS and give the
*Show* and *Hide* actions of the overlay source the same key.

The overlay source has to sit directly in the scene, not inside a nested scene.

To check the setup without going live:

```
start-translator.cmd --preview
```

This reads one frame from OBS, prints the texts it found with their translations and saves `preview.png` with the texts
marked. `--image file.png` does the same for a picture on disk, and `--settings path` selects another settings file, for
example one per game.

## Settings

| key | default | meaning |
|---|---|---|
| `obs_source` | `Game Capture` | Name of the OBS source to read. |
| `scenes` | `[]` | Scenes that get the overlay source when it is created. Empty means the scene that is on air at that moment. |
| `overlay_source` | `Translation overlay` | Name of the browser source that draws the translations. |
| `create_overlay_source` | `true` | Create the overlay source if it does not exist. |
| `source_language`, `target_language` | English, Slovak | Language name and code, as [TranslateGemma expects them](https://ollama.com/library/translategemma). |
| `context` | a sentence about games | One or two English sentences telling the model what kind of text it gets and how to address the reader. |
| `model` | `translategemma:12b` | Ollama model. |
| `ollama_url` | `http://127.0.0.1:11434` | Ollama server. It can run on another PC. |
| `ocr_on_gpu` | `true` | Read text with PyTorch and CUDA instead of ONNX Runtime on the CPU. |
| `ocr_threads` | `8` | CPU threads for reading text when `ocr_on_gpu` is `false`. |
| `min_score` | `0.9` | Texts the reader is less sure about are skipped. |
| `min_height` | `16` | Lines lower than this many pixels of a 1080p frame are skipped. |
| `interval` | `0.25` | Seconds between two frames. |
| `linger` | `0.6` | Seconds a translation stays after its text has disappeared. |
| `port` | `8777` | Port of the local WebSocket the overlay connects to. |

The cache file `cache_<hash>.json` is written next to the settings file. Its name depends on the model, the languages and
the context, so changing any of them starts a new cache.

The address of the overlay source accepts `opacity` (background opacity, default `0.85`), `scale` (set by the tool for
canvases larger than 1920 pixels) and `ws` (address of the WebSocket), for example `overlay.html?scale=2&opacity=1`.

### Context

The default context is neutral. For dialogue it helps to say how people talk. Example for a crime game translated into
Slovak, where the model otherwise uses the formal form of address:

```
The text is shown on screen in a crime action video game (subtitles of spoken dialogue, phone messages, hints, menu items).
Dialogue is colloquial and informal: address a single person as 'ty', never the formal 'vy'. Leave names of people, places,
brands, vehicles and anything that is not a real English word exactly as written.
```

## Measured

On a PC with a Ryzen 9 5950X and an RTX 5080, a 1080p frame from a 4K canvas, English to Slovak, `translategemma:12b`:

- Reading a whole frame: 64 ms in the game and up to 180 ms in a menu full of text on the GPU; 190 to 470 ms on the CPU with
  8 threads, which kept about 7 cores busy.
- Translation: a subtitle 0.5 to 1 s after it appears. Ollama adds about 0.35 s to every call, which is why short labels are
  sent in batches; 12 menu items took 1.3 s.
- OBS dropped no rendered frames in any run of about 3000 frames.
- GPU memory: 7.5 GB for the model, about 13 GB in total with OBS idle on a 4K canvas.

## Limits

- The original text shows through the semi-transparent background. Set `opacity=1` for a solid one.
- The translation is as good as the local model. Slang is sometimes wrong, and a brand name that looks like a word can get
  a nonsense translation.
- A translation longer than the original is shrunk to 70 % of the original size at most and then grows over its neighbours.
- The default reading model covers Latin script and Chinese. Other scripts need a different RapidOCR recognition model.
- Text that moves is not translated; text in the game world is translated when the camera stands still.
- Protected video that OBS shows as a black picture cannot be read.

## Repository layout

- `translator.py` is the tool, `overlay.html` the page for the OBS browser source.
- `settings.example.json` is the template of `settings.json`, `start-translator.cmd` the launcher.
- `THIRD_PARTY_NOTICES.md` lists the software and models the tool uses at run time.

## License

MIT, see [LICENSE](LICENSE). The project ships no third-party code, models or game content; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for what it downloads and uses at run time. It is not affiliated with the
OBS Project, Google, Ollama or any game publisher.
