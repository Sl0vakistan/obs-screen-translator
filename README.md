# OBS Screen Translator

Live translation of on-screen text for streamers. The program reads the text in an [OBS Studio](https://obsproject.com/)
source (a game from a capture card, a game capture, a window), translates it with a language model running on your own PC
and draws the translation over the original text or wherever you want it. Viewers see subtitles, messages, hints, phone
chats and menus in their language; nothing leaves your computer.

- **Reads what you choose**: the whole picture or areas you draw. The translation of an area can be shown in another place
  and in an OBS source of its own, which you place, crop and hide in OBS like any other source.
- **Steady on screen**: tilted text, such as a phone in a hand, is translated at its angle; a translation follows small
  movements of its text without flickering and stands still on a still picture.
- **Your look**: font, size, colours, a background box and a soft shadow around the letters, for all areas or each one,
  with a sample in OBS while you edit.
- **Sets itself up**: it turns on the WebSocket server of OBS, installs Ollama and downloads the TranslateGemma model
  (4b, 12b or 27b) when you agree. A show/hide key works from any window and from a Stream Deck.
- **In English and Slovak**, with a guide in the program; 164 languages in the lists.

Download the installer from [Releases](https://github.com/Sl0vakistan/obs-screen-translator/releases/latest).

Slovak version: [README.sk.md](README.sk.md)

Open source under the MIT License, see [LICENSE](LICENSE).

## Vibe-coded, and saying so

The idea, the testing on a real stream and every decision come from a streamer who is not a programmer and does not pretend
to be one. All of the code, the installer and this documentation were written by an AI coding assistant (Claude, by
Anthropic) in conversation with him. Nobody has reviewed the code line by line. Treat it accordingly: read it before you
rely on it, and report what breaks.

## Install

1. Install [OBS Studio](https://obsproject.com/) and start it once.
2. Download `OBS-Screen-Translator-Setup-<version>.exe` from the Releases page of this repository and run it. It installs
   for the current user, without administrator rights.

The rest is set up by the program on the first start, each step after asking you:

- If the WebSocket server in OBS is off, the program offers to turn it on. OBS reads that setting only when it starts, so
  OBS has to be closed for a moment; the program waits for that, changes the setting and keeps the previous one in
  `config.before-screen-translator.json` in the same folder.
- If [Ollama](https://ollama.com/), which runs the translation model, is missing, the program offers to download it from
  ollama.com (1.9 GB) and install it. The downloaded installer is run only if it carries Ollama's signature. After its
  installation Ollama opens a window of its own with commands for a terminal; the translator does not need them, see
  [Ollama](#ollama).
- The translation model is downloaded once: 8.1 GB for the recommended TranslateGemma 12b, 3.3 GB for 4b, 17.4 GB for 27b.

You can do the first two by hand instead: *Tools > WebSocket Server Settings > Enable WebSocket server* in OBS, and the
installer from [ollama.com/download](https://ollama.com/download).

The installer is not signed, so Windows SmartScreen may warn about an unknown publisher; *More info > Run anyway* continues.
If you would rather not run an unsigned installer, run the program from source (below).

## Use

1. Start OBS and *OBS Screen Translator* from the Start menu, in any order. The program waits for OBS.
2. Check the languages in **Translate from** and **Translate to** under *Translation*. The target language starts as the
   language of your Windows. **Model** chooses between TranslateGemma 4b (weaker, about 2.7 GB of graphics memory), 12b
   (recommended, about 7.5 GB) and 27b (best, about 17 GB); the line below it shows the graphics card of your PC and its
   memory. A model bigger than the card runs partly on the processor and translates much more slowly; the window says so.
3. Check **Source in OBS** under *Game*. If the scene that is on air has exactly one capture card, it is chosen for you; the same
   goes for a single game capture, window capture or display capture. Otherwise pick the game from the list. *Refresh*
   reads the list of sources from OBS again.
4. Optional: **Areas to read**. *Choose...* shows the current picture of the game; drag a rectangle around each part you
   want translated, for example the subtitles and the phone. You can draw several. Text outside the rectangles is
   ignored. *Remove last* and *Remove all* take rectangles away; with no rectangle the whole picture is read. A
   translation is drawn over its original text unless you give it another place: choose *Draw where area [number] is
   shown* and drag the place (blue, with an arrow from the area). The place keeps the proportions of its area, so the
   translation is moved there and scaled without being squeezed or stretched. *Show it where it is read* undoes that.
   *OK* confirms; *Apply* saves the areas without closing the window, and the changes show in OBS at once. While the
   window is open, every area shows its number in OBS where its translations will appear.
5. Optional: **Look** → *Edit...* opens *Look of translations*: font, size (the size of the original text or a fixed size), bold,
   italic, text colour, background colour and opacity, a background box (0 none, it grows smoothly, at 8 it covers the
   original text), a shadow around the letters (a soft shadow without edges, from none to large, with its own intensity), outline and
   alignment. *Settings for* chooses whether you change
   the default look, which every area uses, or the look of one area; an area can keep the default look or get its own.
   Changes apply at once, and while the editor is open OBS shows a sample translation with the look you are editing.
   **Shown in OBS source** sends the translations of an area to another browser source: *New source...* adds one to OBS,
   *Remove source* removes it from OBS again and moves its areas back to the first source. Each source can be placed,
   cropped, filtered and shown or hidden in OBS on its own, for example the subtitles in every scene and the phone only in
   some.
6. Optional: **Show/hide key**. Press *Set...* and then a function key (F1 to F24) or a combination with Ctrl or Alt.
   That key shows and hides the translations whatever window is in front, also when a Stream Deck sends it.
7. Press **Start**. With **Start translating when this program opens** ticked, the program does that for you next time.

The button next to **Help** switches the program between English and Slovak; until you choose, it follows the language of
Windows. Every window can be resized; *Areas to read* scales the picture with the window and keeps the proportions of the
OBS source.

On the first start the program adds a browser source named *Translation overlay* to the scene that is on air. Sources
added with *New source...* are created the same way when translation starts or restarts.

The **Help** button at the top right has a short guide (*Installation and setup*), the changes of the installed version (*What's new in <version>*), *Details* with the version, the license and the place of the
settings and stored translations, *Open the settings folder* and a link to this project. The window lists every translated text with the time it took.

To change the language or the model, pick another one in the window. Translation restarts by itself; you do not have to
stop it first. Every language and every model keeps its own stored translations. A model that is not on the PC yet is
downloaded first, and the model used before is unloaded from the graphics card. The areas can be changed while
translating in the same way.

Smaller areas mean less to read and less to translate, and no translations drawn over parts of the picture you do not
care about. They help most on screens full of text; see *Measured*.

An area is read only while the source that shows its translations is visible in the scene that is on air. Hide a source
and its areas are neither read nor translated; with every translation source hidden the program waits until you show one
again. The show/hide key shows and hides all translation sources together, in every scene that contains them. A
translation source has to sit directly in the scene, not inside a nested scene.

Closing the window removes the translations from the picture and unloads the translation model from the graphics card at
once. While the program runs, Ollama keeps the model loaded between translations.

## Ollama

[Ollama](https://ollama.com/) is a free program that runs the translation model on your PC. The translator sends it the
text to translate; nothing leaves your computer.

- You do not have to start Ollama or type anything in a terminal. When you press **Start**, the program starts Ollama in
  the background if it is not running and downloads the model if it is missing (8.1 GB; the window shows the progress).
  It says *translation model ready* when it can translate.
- After its installation Ollama opens a window of its own, *Launch*, with the line "Copy a command and run it in your
  terminal" and commands such as `ollama launch claude`. Those start AI coding tools and have nothing to do with the
  translator: close the window. Ollama keeps running in the background.
- Installing it by hand: run `OllamaSetup.exe` from [ollama.com/download](https://ollama.com/download). It installs for
  the current user, without administrator rights, and needs no account.
- Is it running? <http://127.0.0.1:11434> in a browser says *Ollama is running*. `ollama list` in Command Prompt lists the
  downloaded models.
- To download the model before a stream, press **Start** once and wait for *translation model ready*, or run
  `ollama pull translategemma:12b` in Command Prompt.
- With less than about 8 GB of free graphics memory, choose *TranslateGemma 4b* in *Translation* → *Model* (3.3 GB, about
  2.7 GB of graphics memory). It translates noticeably worse and is downloaded on the next **Start**.
- Ollama keeps the models in `%USERPROFILE%\.ollama\models`. To keep them elsewhere, change *Model location* in Ollama's
  settings (open Ollama from the Start menu) or set the environment variable `OLLAMA_MODELS`, best before the model is
  downloaded.
- Ollama on another PC: there, turn on *Expose Ollama to the network* in Ollama's settings (or set `OLLAMA_HOST=0.0.0.0`)
  and allow Ollama through the Windows firewall; here, set `ollama_url` in `settings.json` to `http://<that PC>:11434`.
  Every translation then goes through Ollama and takes about a third of a second longer, because the direct connection to
  the model works only on the same PC.
- *Ollama did not start*: open Ollama from the Start menu, wait for its icon next to the clock and press **Start** again.
- A download of the model that stopped continues where it stopped when you press **Start** again.

## How it works

1. Four times a second the program asks OBS for a frame of the game source through the built-in WebSocket server.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (PP-OCR models) finds and reads the text in the whole frame. It runs on
   the graphics card through DirectML, which works on any DirectX 12 card, or on the processor.
3. Lines that belong together (a two-line subtitle, a paragraph of a message) are joined into one block. Every line is
   measured along its own direction, so tilted text, such as a phone in a hand, is joined correctly and translated at the
   same angle.
4. A block is translated by [TranslateGemma](https://ollama.com/library/translategemma) served by Ollama. Sentences go one
   at a time as soon as they appear; short labels such as menu items go in batches of up to 12. Ollama spends about 0.35 s
   on every request before the model starts working, so the program sends the text straight to the llama-server that
   Ollama starts for the model, with the same template and settings. It checks first that a test sentence comes back
   exactly as through Ollama and falls back to Ollama whenever that fails.
5. A browser source in OBS (`overlay.html`) receives the translations over a local WebSocket and draws each one at the place
   of the text it replaces.

Only new text reaches the model. A text that stays on screen is translated once, and every translation is stored on disk,
so a menu seen before appears at once, also after a restart.

A translation is shown only after its text has been read twice in nearly the same place, so text that sweeps across the
picture with the camera, such as signs and number plates, is left alone. Once shown, a translation follows its text while it
moves a little, like a phone in a hand, and glides along instead of flickering; on a still picture it does not move at all. An old translation stays until the text that
replaced it is translated.

## Requirements

- Windows 10 or 11, 64-bit. The program was developed and tested on Windows 11 only.
- OBS Studio. The program was developed and tested with OBS 33. It reads the WebSocket settings from
  `plugin_config\obs-websocket\config.json`; OBS versions that still keep them in `global.ini` are not supported.
- Ollama; the program can install it. The model `translategemma:12b` needs about 7.5 GB of graphics memory; `translategemma:4b` needs about 2.7 GB and
  translates noticeably worse; `translategemma:27b` (17.4 GB download) needs about 17 GB and a card with more memory than
  16 GB. The 27b model has not been tested.
- A DirectX 12 graphics card for reading text. Without one the reading runs on the processor and keeps several cores busy.

## Languages

The lists offer 164 entries: the 160 base languages of the TranslateGemma language table, Filipino, Brazilian Portuguese
and Simplified and Traditional Chinese. Google describes the model as built for 55 languages, so expect the less common
ones to be weaker.
Only English to Slovak has been tested on a stream.

The text reader covers Latin script and Chinese. A game in another script (Cyrillic, Arabic, Korean and others) is not read
correctly yet, whatever language you choose.

## Settings

The window covers the languages, the model, the game source, the areas to read and where they are shown, the look of
translations and the OBS sources they go to, the show/hide key, the automatic start and the language of the program. Everything else is in `settings.json`, created on the first start in
`%APPDATA%\OBS Screen Translator` (next to `translator.py` when you run from source). Changes apply after a restart of the
program.

| key | default | meaning |
|---|---|---|
| `obs_source` | empty | Name of the OBS source to read. Set in the window. |
| `source_language`, `target_language` | `en`, `sk` | Language codes. Set in the window. |
| `ui_language` | `null` | Language of the program: `en` or `sk`; `null` follows the language of Windows. Set in the window. |
| `regions` | `[]` | Parts of the picture that are read, each with `box` (left, top, right and bottom edge in fractions of the frame), `style` (`null` for the default look, or a look of its own with the same keys as `style`), `display` (`null` to draw the translations over the original text, or the box where they are drawn) and `overlay` (which entry of `overlays` draws them, counted from 0). Empty means the whole picture. Set in the window. |
| `start_automatically` | `false` | Start translating when the program opens. Set in the window. |
| `hotkey` | none | The show/hide key: Windows key code, modifiers (1 Alt, 2 Ctrl, 4 Shift) and the label shown in the window. Set in the window. |
| `style` | Segoe UI Semibold, white on black 85 % | The default look: `font`, `size` (0 = the size of the original text, else pixels in a 1080p picture), `bold`, `italic`, `color`, `background`, `opacity` (0 to 1), `outline` (pixels), `outline_color`, `align` (`auto`, `left`, `center`, `right`) `padding` (the background box: 0 none, 1 to 4 a box around the translation coming in, 8 covers the original text with a margin of 8 pixels, more adds margin) `shadow` (a soft shadow around the letters, 0 to 20 pixels) and `shadow_strength` (its intensity, 0 to 1). Set in the window. |
| `scenes` | `[]` | Scenes that get a translation source when it is created. Empty means the scene that is on air at that moment. |
| `overlays` | one source, `Translation overlay` | Browser sources that draw the translations, each `{"name": ...}`. The first one serves the whole picture and every area that has no other. Set in the window. |
| `create_overlay_source` | `true` | Create the translation sources that do not exist, and keep their addresses current. |
| `context` | a sentence about games | One or two English sentences telling the model what kind of text it gets and how to address the reader. |
| `model` | `translategemma:12b` | Ollama model, chosen in the window (`translategemma:4b`, `translategemma:12b` or `translategemma:27b`). Another Ollama model can be written here; that is untested. A missing model is downloaded on Start. |
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
- Several areas are put next to each other into one picture and read in one pass. They were measured only while the
  graphics card was busy with another game, which about doubled all times: two areas then took as long as the whole frame
  in the game (150 to 270 ms against 170 to 270 ms) and three areas about a quarter less on the menu screen (430 to 620 ms
  against 560 to 820 ms).
- Translation: Ollama adds about 0.35 s to every request before the model starts working. Through Ollama a subtitle took
  0.57 to 1.08 s (median 0.64 s), straight to its llama-server 0.14 to 0.72 s (median 0.28 s) with the same translations.
  The window then showed subtitles 0.4 to 0.85 s after they appeared. Short labels go in batches; 5 menu items took 0.4 s.
- OBS dropped no rendered frames in any run of about 3000 frames.
- Graphics memory: 7.5 GB for the model, about 13 GB in total with OBS idle on a 4K canvas.

## What was and was not tested

Tested: starting and stopping from the window, changing the target language while translating, choosing one and several
areas and going back to the whole picture while translating, the built program and the installed program against a running OBS,
creation of the overlay source, silent install and uninstall, the download of the translation model, the automatic choice of
the game source, the start on opening, showing and hiding with the key, and, with a test picture in a running OBS, two
translation sources with an area drawn in another place, hiding one source, adding and removing a source in the look
editor and moving an area's place in *Areas to read*. The windows were checked in dark and light mode on a 4K display at
125 %. Version 0.7.0: the program in English and Slovak with switching while it translates, the choice of the model with
the previous model unloaded, every window made bigger and smaller, and the proportions of a moved area while drawing it
and in OBS. Version 0.8.0: tilted text and steady translations on 40 pictures of a phone moved as in a hand and in a running
OBS with the same phone turned and moved by a script, *OK* and *Apply* in *Areas to read* with the areas changed while
translating, and the background box and the shadow around the letters.

Tested only in part:

- Turning on the WebSocket server was tried on a copy of the OBS settings file. That OBS then starts the server from the
  changed file follows from the OBS source code; it was not tried in a real OBS.
- Installing Ollama: the download from ollama.com and the signature check ran with the real installer, and an unsigned
  file was refused. The installer itself was not run, because the test PC already has Ollama.
- The show/hide key: registering the key with Windows and the reaction to it were tested by sending the key message to the
  program, not by pressing a key.

Not tested: reading text on the processor in the built program, a graphics card other than the RTX 5080, Windows 10, an
OBS version other than 33, and a whole live broadcast. The areas were drawn in the tests by a script that simulates the
mouse, not by hand.

## Limits

- The original text shows through a semi-transparent background. Set the background opacity to 100 % in *Look of
  translations* for a solid one.
- The translation is as good as the local model. Slang is sometimes wrong, and a brand name that looks like a word can get
  a nonsense translation.
- A translation longer than the original is shrunk to 70 % of the original size at most and then grows over its neighbours.
- Text that moves fast is not translated; text in the game world is translated when the camera slows down.
- Tilted text is drawn at its angle, but flat: a translation is a turned rectangle, not one in perspective.
- Protected video that OBS shows as a black picture cannot be read.
- Uninstalling leaves the settings and stored translations in `%APPDATA%\OBS Screen Translator`.

## License

MIT, see [LICENSE](LICENSE). The repository contains only this project's own code. The installer bundles third-party
software under its own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The project is not affiliated with
the OBS Project, Google, Ollama, Microsoft or any game publisher.
