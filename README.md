# OBS Screen Translator

Live translation of on-screen text for streamers. The program reads the text in an [OBS Studio](https://obsproject.com/)
source (a game from a capture card, a game capture, a window), translates it with a language model running on your own PC
and draws the translation over the original text, on a black semi-transparent background. Viewers see subtitles, messages,
hints and menus in their language; nothing leaves your computer.

Slovak version: [README.sk.md](README.sk.md)

Open source under the MIT License, see [LICENSE](LICENSE).

## Vibe-coded, and saying so

The idea, the testing on a real stream and every decision come from a streamer who is not a programmer and does not pretend
to be one. All of the code, the installer and this documentation were written by an AI coding assistant (Claude, by
Anthropic) in conversation with him. Nobody has reviewed the code line by line. Treat it accordingly: read it before you
rely on it, and report what breaks.

## Install

1. Install [OBS Studio](https://obsproject.com/) 28 or newer and turn on *Tools > WebSocket Server Settings > Enable
   WebSocket server*.
2. Install [Ollama](https://ollama.com/download). It runs the translation model.
3. Download `OBS-Screen-Translator-Setup-<version>.exe` from the Releases page of this repository and run it. It installs
   for the current user, without administrator rights.

The installer is not signed, so Windows SmartScreen may warn about an unknown publisher; *More info > Run anyway* continues.
If you would rather not run an unsigned installer, run the program from source (below).

## Use

1. Start OBS, then start *OBS Screen Translator* from the Start menu.
2. Choose the languages in **Translate from** and **Translate to**.
3. Choose your game in **Game source in OBS**. *Refresh* reads the list of sources from OBS again.
4. Optional: **Area to read**. *Choose...* shows the current picture of the game; drag a rectangle around the part you
   want translated, for example only the subtitles, and press *Use this area*. Text outside the rectangle is ignored.
   *Whole picture* in the same dialog switches back.
5. Press **Start**.

On the first start the program downloads the translation model (8.1 GB, once) and adds a browser source named *Translation
overlay* to the scene that is on air. The window lists every translated text with the time it took.

To change the language, pick another one in the window. Translation restarts in the new language by itself; you do not have
to stop it first. Every language keeps its own stored translations. The area can be changed while translating in the same
way.

A smaller area means less to read and less to translate. It helps most on screens full of text and when you only care
about one part of the picture, such as the subtitles; see *Measured*.

The program works only while the overlay source is visible in the scene that is on air. Hide the source and the program
stops reading and translating until you show it again. To switch it with one key, open *Settings > Hotkeys* in OBS and give
the *Show* and *Hide* actions of the overlay source the same key. The overlay source has to sit directly in the scene, not
inside a nested scene.

Closing the window removes the translations from the picture.

## How it works

1. Four times a second the program asks OBS for a frame of the game source through the built-in WebSocket server.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (PP-OCR models) finds and reads the text in the whole frame. It runs on
   the graphics card through DirectML, which works on any DirectX 12 card, or on the processor.
3. Lines that belong together (a two-line subtitle, a paragraph of a message) are joined into one block.
4. A block is translated by [TranslateGemma](https://ollama.com/library/translategemma) served by Ollama. Sentences go one
   at a time as soon as they appear; short labels such as menu items go in batches of up to 12.
5. A browser source in OBS (`overlay.html`) receives the translations over a local WebSocket and draws each one at the place
   of the text it replaces.

Only new text reaches the model. A text that stays on screen is translated once, and every translation is stored on disk,
so a menu seen before appears at once, also after a restart.

A translation is shown only after its text has been read twice at the same place. Text that moves with the camera, such as
signs and number plates in the game world, is therefore left alone until the picture stands still.

## Requirements

- Windows 10 or 11, 64-bit. The program was developed and tested on Windows 11 only.
- OBS Studio 28 or newer with the WebSocket server enabled.
- Ollama. The model `translategemma:12b` needs about 7.5 GB of graphics memory; `translategemma:4b` needs about 2.7 GB and
  translates noticeably worse.
- A DirectX 12 graphics card for reading text. Without one the reading runs on the processor and keeps several cores busy.

## Languages

The lists offer 164 entries: the 160 base languages of the TranslateGemma language table, Filipino, Brazilian Portuguese
and Simplified and Traditional Chinese. Google describes the model as built for 55 languages, so expect the less common
ones to be weaker.
Only English to Slovak has been tested on a stream.

The text reader covers Latin script and Chinese. A game in another script (Cyrillic, Arabic, Korean and others) is not read
correctly yet, whatever language you choose.

## Settings

The window covers the languages, the game source and the area to read. Everything else is in `settings.json`, created on the first start in
`%APPDATA%\OBS Screen Translator` (next to `translator.py` when you run from source). Changes apply after a restart of the
program.

| key | default | meaning |
|---|---|---|
| `obs_source` | empty | Name of the OBS source to read. Set in the window. |
| `source_language`, `target_language` | `en`, `sk` | Language codes. Set in the window. |
| `region` | `[0, 0, 1, 1]` | Part of the picture that is read: left, top, right and bottom edge as fractions of the frame. Set in the window. |
| `scenes` | `[]` | Scenes that get the overlay source when it is created. Empty means the scene that is on air at that moment. |
| `overlay_source` | `Translation overlay` | Name of the browser source that draws the translations. |
| `create_overlay_source` | `true` | Create the overlay source if it does not exist, and keep its address current. |
| `context` | a sentence about games | One or two English sentences telling the model what kind of text it gets and how to address the reader. |
| `model` | `translategemma:12b` | Ollama model. It is downloaded on the first start. |
| `ollama_url` | `http://127.0.0.1:11434` | Ollama server. It can run on another PC. |
| `ocr_on_gpu` | `true` | Read text on the graphics card. `false` uses the processor. |
| `ocr_threads` | `8` | Processor threads for reading text when the graphics card is not used. |
| `min_score` | `0.9` | Texts the reader is less sure about are skipped. |
| `min_height` | `16` | Lines lower than this many pixels of a 1080p frame are skipped. |
| `interval` | `0.25` | Seconds between two frames. |
| `linger` | `0.6` | Seconds a translation stays after its text has disappeared. |
| `port` | `8777` | Port of the local WebSocket the overlay connects to. |

Stored translations are in `cache_<hash>.json` next to the settings. The name depends on the model, the languages and the
context, so changing any of them starts a new file.

The address of the overlay source accepts `opacity` (background opacity, default `0.85`), for example
`...overlay.html?scale=2&ws=ws://127.0.0.1:8777&opacity=1` for a solid background.

### Context

The default context is neutral. For dialogue it helps to say how people talk. Example for a crime game translated into
Slovak, where the model otherwise uses the formal form of address:

```
The text is shown on screen in a crime action video game (subtitles of spoken dialogue, phone messages, hints, menu items).
Dialogue is colloquial and informal: address a single person as 'ty', never the formal 'vy'. Leave names of people, places,
brands, vehicles and anything that is not a real English word exactly as written.
```

## Run from source

```
py -3 -m pip install -r requirements.txt
start-translator.cmd
```

`start-translator.cmd --preview` reads one frame from OBS, prints the texts it found with their translations and saves
`preview.png` with the texts marked. `--image file.png` does the same for a picture on disk, and `--settings path` selects
another settings file.

## Build the installer

`build.ps1` creates a virtual environment in `.venv`, builds the program with PyInstaller into `dist\OBS Screen Translator`
and, if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, the installer
`dist\OBS-Screen-Translator-Setup-<version>.exe`. The license texts of everything that gets bundled are copied into the
`licenses` folder of the program.

## Measured

On a PC with a Ryzen 9 5950X and an RTX 5080, a 1080p frame from a 4K canvas, English to Slovak, `translategemma:12b`:

- Reading a whole frame on the graphics card: about 100 ms in the game (92 to 117 ms) and 255 to 395 ms in a menu full of
  text. On the processor with 8 threads: 290 to 340 ms and about 565 ms.
- Reading only a band around the subtitles (60 % of the width, 15 % of the height): 68 to 86 ms in the game and 58 to 68 ms
  on the menu screen, where the whole frame took 255 to 269 ms in the same run. In the game the gain is small, because most
  of the time goes into finding text, not into the amount of it.
- Translation: a subtitle 0.5 to 1 s after it appears. Ollama adds about 0.35 s to every call, which is why short labels are
  sent in batches; 12 menu items took 1.3 s.
- OBS dropped no rendered frames in any run of about 3000 frames.
- Graphics memory: 7.5 GB for the model, about 13 GB in total with OBS idle on a 4K canvas.

## What was and was not tested

Tested: starting and stopping from the window, changing the target language while translating, choosing an area and
going back to the whole picture while translating, the built program and the installed program against a running OBS,
creation of the overlay source, silent install and uninstall.

Not tested: a PC without Ollama or without the model (the download on the first start), reading text on the processor in
the built program, a graphics card other than the RTX 5080, Windows 10, and a whole live broadcast.

## Limits

- The original text shows through the semi-transparent background. Set `opacity=1` for a solid one.
- The translation is as good as the local model. Slang is sometimes wrong, and a brand name that looks like a word can get
  a nonsense translation.
- A translation longer than the original is shrunk to 70 % of the original size at most and then grows over its neighbours.
- Text that moves is not translated; text in the game world is translated when the camera stands still.
- Protected video that OBS shows as a black picture cannot be read.
- Uninstalling leaves the settings and stored translations in `%APPDATA%\OBS Screen Translator`.

## License

MIT, see [LICENSE](LICENSE). The repository contains only this project's own code. The installer bundles third-party
software under its own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The project is not affiliated with
the OBS Project, Google, Ollama, Microsoft or any game publisher.
