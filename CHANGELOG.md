# Changelog

## 0.7.0 - 2026-11-20

- **In Slovak**: the whole program is also in Slovak, including the guide, the details and the list of changes. The button
  next to *Help* switches between English and Slovak at once; until you choose, the program follows the language of
  Windows. Stored as `ui_language`.
- **Model in the window**: *Translation* → *Model* chooses between TranslateGemma 12b (best, about 7.5 GB of graphics
  memory) and 4b (weaker, about 2.7 GB). The line below shows the graphics card of the PC and its memory. A model that is
  not on the PC yet is downloaded on the next Start, and the model used before is unloaded from the graphics card.
- **Every window can be resized**. In *Areas to read* the picture follows the size of the window and keeps the
  proportions of the OBS source; it is taken from OBS at 1920 pixels wide, so it stays sharp in a big window.
- **The place of a moved area keeps its proportions**: while you drag it, the blue rectangle keeps the shape of its yellow
  area, so the translation is never squeezed or stretched. A place drawn with 0.6.0 in other proportions is filled as far
  as the translation fits, centred.

## 0.6.0 - 2026-11-20

- **Areas shown somewhere else**: an area can be read in one place and its translation drawn in another (*Areas to read*
  → *Draw where area N is shown*). The translation is moved there and scaled to the new box.
- **More translation sources in OBS**: *Look of translations* → *Shown in OBS source* sends an area to a browser source of
  its own. *New source...* creates it in OBS, *Remove source* removes it. Each source can be placed, cropped, filtered
  and shown or hidden in OBS separately; the areas of a hidden source are not read. The show/hide key switches all of
  them.
- **New look of the windows**: Windows 11 style (the Sun Valley theme), dark or light as Windows is set, settings grouped
  into sections and title bars in the colour of the window. *Help* is a button at the top right.
- **Look of translations** (*Edit...* in the window, replaces the opacity slider): font, size (the size of the original
  text or a fixed size), bold, italic, text colour, background colour and opacity, outline and alignment.
- One default look for all areas, and any area can keep it or get a look of its own (*Settings for* in the editor).
- While the editor is open, OBS shows a sample translation with the look being edited; changes apply at once, also to
  translations that are on screen.
- *Help* → *What's new in 0.6.0* shows the changes of the installed version.
- The guide (*Help* → *Installation and setup*) and the README explain how to get Ollama running. After its installation
  Ollama opens a window of its own with commands for a terminal (*Launch*); the translator does not need them, and right
  after installing Ollama it now says so in its window.
- Settings: `style` holds the default look and `overlays` lists the translation sources (it replaces `overlay_source`);
  each entry of `regions` is now `{"box": [...], "style": null or a look, "display": null or a box, "overlay": 0}`.
  Settings of 0.5.0 (`opacity`, `overlay_source`, areas as plain lists) are converted on the first start.
- The address of the overlay source carries the version, so OBS loads the new page after an update.
- Translations appear about a third of a second sooner. Ollama spends about 0.35 s on every request before the model starts
  working. After the first answer the program sends the text straight to the llama-server that Ollama starts for the model,
  with the template and settings Ollama would use. It does so only after checking that a test sentence comes back exactly
  as through Ollama, and it goes back to Ollama whenever that connection fails. Ollama still loads, keeps and unloads the
  model; the program reminds it every five minutes that the model is in use. The window showed subtitles 0.4 to 0.85 s
  after they appeared, against 1.2 to 1.5 s before.

## 0.5.0 - 2026-11-20

The program sets up most things itself, so installing comes down to the installer and the Start button.

- If the WebSocket server in OBS is off, the program offers to turn it on. It waits until OBS is closed, changes the
  setting and keeps the previous one in `config.before-screen-translator.json`.
- If Ollama is missing, the program offers to download it from ollama.com and install it. The downloaded installer is run
  only if it carries Ollama's signature.
- The game source is chosen automatically when the scene that is on air has exactly one capture card, game capture,
  window capture or display capture.
- On the first start the target language is the language of Windows.
- **Show/hide key**: a key or key combination, set in the window, that shows and hides the translations from anywhere,
  also from a Stream Deck. Stored as `hotkey`.
- **Start translating when this program opens**. Stored as `start_automatically`.
- **Background opacity**: a slider in the window, from no background (0 %) to solid black (100 %). It changes the
  translations that are on screen at once. Stored as `opacity`; the `opacity` in the address of the overlay source is no
  longer used.
- **Help** menu: *Installation and setup* (a short guide in the program), *Details* (version, license, how it works,
  where the settings and stored translations are), *Open the settings folder* and *Project page*.
- The program waits for OBS and connects as soon as it runs; *Refresh* is no longer needed for that.
- Closing the window unloads the translation model from the graphics card at once. Before, Ollama kept it loaded for
  30 minutes after the last translation.

## 0.4.1 - 2026-11-20

- Smaller installer. The build leaves out three parts the program never uses: the video library that comes with OpenCV,
  the AVIF module of Pillow and the text-rotation model. Nothing changes in how the program works.

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
