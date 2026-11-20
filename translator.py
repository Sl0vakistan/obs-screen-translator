import argparse
import asyncio
import base64
import copy
import ctypes
import ctypes.wintypes
import difflib
import hashlib
import json
import locale
import math
import os
import pathlib
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import types
import unicodedata
import urllib.request
import webbrowser
from tkinter import colorchooser, font as tkfont, messagebox, ttk

import cv2
import numpy as np
import sv_ttk
import websockets
from rapidocr import RapidOCR

import ui_sk

VERSION = "0.8.0"
PROJECT = "https://github.com/Sl0vakistan/obs-screen-translator"
FROZEN = getattr(sys, "frozen", False)
HERE = pathlib.Path(sys._MEIPASS) if FROZEN else pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get("APPDATA", HERE)) / "OBS Screen Translator" if FROZEN else HERE
LANGUAGES = json.loads((HERE / "languages.json").read_text(encoding="utf-8"))
STYLE = {"font": "Segoe UI Semibold", "size": 0, "bold": False, "italic": False, "color": "#ffffff", "background": "#000000",
         "opacity": 0.85, "outline": 0, "outline_color": "#000000", "align": "auto", "padding": 8, "shadow": 0, "shadow_strength": 0.5}
ALIGN = {"auto": "Automatic", "left": "Left", "center": "Centre", "right": "Right"}
SAMPLE = "This is how the translations will look"
STAGE = "#3d4650"
MODELS = {"translategemma:4b": "TranslateGemma 4b: weaker translations, about 2.7 GB of graphics memory",
          "translategemma:12b": "TranslateGemma 12b: recommended, about 7.5 GB of graphics memory",
          "translategemma:27b": "TranslateGemma 27b: best translations, about 17 GB of graphics memory"}
# Graphics memory in GB (2^30 bytes) each model takes: the size of the model plus a little for its work.
MEMORY = {"translategemma:4b": 2.7, "translategemma:12b": 7.5, "translategemma:27b": 17}
DEFAULTS = {
    "obs_source": "",
    "scenes": [],
    "overlays": [{"name": "Translation overlay"}],
    "create_overlay_source": True,
    "source_language": "en",
    "target_language": "sk",
    "ui_language": None,
    "regions": [],
    "start_automatically": False,
    "hotkey": None,
    "style": STYLE,
    "context": "The text is shown on screen in a video game (subtitles of spoken dialogue, messages, hints, menu items). "
               "Leave names of people, places, brands and anything that is not a real word exactly as written.",
    "model": "translategemma:12b",
    "ollama_url": "http://127.0.0.1:11434",
    "ocr_on_gpu": True,
    "ocr_threads": 8,
    "min_score": 0.9,
    "min_height": 16,
    "interval": 0.25,
    "linger": 0.6,
    "port": 8777,
}
log = print
ask = lambda question: False
OPTIONS = {"temperature": 0, "num_predict": 400, "num_ctx": 2048}
# The settings Ollama itself sends to the llama-server it starts for a model (its defaults plus TranslateGemma's top_k, top_p and stop).
DIRECT = {"temperature": 0, "top_k": 64, "top_p": 0.95, "min_p": 0, "repeat_penalty": 1.1, "repeat_last_n": 64, "n_predict": 400,
          "cache_prompt": True, "stop": ["<end_of_turn>"]}
GUIDE = """# What you need
- Windows 10 or 11 and OBS Studio from obsproject.com.
- A graphics card with about 8 GB of free memory for the translation model (about 3 GB for the smaller one), and about 10 GB of free disk space.

# First start
1. Start OBS once, then this program. The order does not matter: the program waits for OBS.
2. If the WebSocket server in OBS is off, the program asks to turn it on. Close OBS when it says so and start OBS again. The previous OBS setting is kept in a backup file.
3. If Ollama is missing, the program asks to download it from ollama.com (1.9 GB) and install it. Ollama runs the translation model. After its installation Ollama opens a window of its own with commands for a terminal: close it, the translator does not need them (see Ollama below).
4. On the first Start the translation model (8.1 GB) is downloaded, once. The window shows the progress and says "translation model ready" when it can translate.

# Setting up
- Translation > Translate from / Translate to: the language of the game and the language of your viewers. The target starts as the language of Windows.
- Translation > Model: TranslateGemma 4b (about 2.7 GB of graphics memory, weaker translations), 12b (about 7.5 GB, recommended) or 27b (about 17 GB, best translations; on a card with 16 GB or less part of it runs on the processor and it translates much more slowly). The line below it shows the graphics card of this PC. A model that is not on this PC yet is downloaded on the next Start.
- Game > Source in OBS: the source with the game. A single capture card in the scene that is on air is chosen by itself.
- Game > Areas to read: optional rectangles around the parts to translate, for example the subtitles. With none the whole picture is read. For each area you can also draw where its translation is shown, if not over the original text. That place keeps the proportions of its area, so the translation is never squeezed. OK confirms; Apply shows the changes in OBS at once and keeps the window open, and while it is open every area shows its number in OBS where its translations will appear.
- On screen > Look: font, size, colours, background and its size, outline and alignment. Background box: at 0 there is none, it grows smoothly and at 8 it covers the original text. Shadow around letters: a soft shadow without edges that follows the letters, from none to large; its intensity makes it lighter or darker. One look for all areas, or a look of its own for any area. While the editor is open, a sample translation is shown in OBS. Each area can also be shown in an OBS source of its own: New source... adds another browser source, which you can move, show and hide in OBS on its own.
- On screen > Show/hide key: one key that shows and hides all translation sources from any window, also from a Stream Deck.
- Start translating when this program opens: no need to press Start next time.
- The button next to Help switches this program between English and Slovak. Every window can be made bigger or smaller.

Then press Start. A browser source named Translation overlay appears in the scene that is on air. Keep it above the game.

# During the stream
- Hiding a translation source in OBS stops reading the areas shown in it. With all of them hidden, for example with the show/hide key, reading and translating pause.
- Changing a language or the model while translating restarts the translation by itself; changed areas take effect at once.
- Tilted text, such as a phone in a hand, is translated at the same angle, and a translation follows small movements of its text instead of flickering. On a still picture translations do not move.
- Keep this window open. Closing it removes the translations from the picture and unloads the translation model from the graphics card.

# Ollama
Ollama is a free program that runs the translation model on this PC. The translator only sends it text; nothing leaves your computer.
- You do not have to start Ollama or type anything in a terminal. Start in this window starts Ollama in the background when it is not running and downloads the model when it is missing.
- After its installation Ollama opens its own window, Launch, saying "Copy a command and run it in your terminal", with commands such as ollama launch claude. Those start AI coding tools and have nothing to do with the translator. Close that window; Ollama keeps running in the background.
- Installing it by hand: run OllamaSetup.exe from ollama.com/download. It needs no account and no administrator rights.
- Is it running? Open http://127.0.0.1:11434 in a browser: it says "Ollama is running".
- Downloading the model before a stream: press Start once and wait for "translation model ready".
- Less than about 8 GB of free graphics memory: choose TranslateGemma 4b in Translation > Model. It is downloaded on the next Start (3.3 GB) and translates noticeably worse.
- Little space on drive C: Ollama keeps the models in .ollama\\models in your user folder. To keep them elsewhere, open Ollama from the Start menu and set Model location in its Settings to a folder on another drive, best before the model is downloaded.
- Ollama on another PC: there, turn on Expose Ollama to the network in Ollama's Settings and allow Ollama through the Windows firewall. Here, set ollama_url in settings.json (Help > Open the settings folder) to http://<address of that PC>:11434. Translations then take about a third of a second longer.

# When something does not work
- "Waiting for OBS": OBS is not running, or its WebSocket server is off (Tools > WebSocket Server Settings in OBS).
- "Ollama did not start": open Ollama from the Start menu, wait for its icon next to the clock and press Start again.
- The download of the model stopped: check the internet connection and the free disk space, then press Start again. The download continues where it stopped.
- Translations take several seconds: the model does not fit into the graphics memory, for example next to a demanding game. Choose TranslateGemma 4b (see Ollama).
- No translations on screen: the translation source (Translation overlay, or one you added) is hidden, is not in the scene that is on air, or sits inside a nested scene.
- Text that moves fast stays untranslated until it slows down. This is on purpose: it skips signs and number plates while the camera turns. Small movements, like a phone in a hand, are followed.
- The first translation after a break is late: the model is being loaded, which takes about 12 seconds.
- Cyrillic, Arabic, Korean and other scripts are not read yet. Latin script and Chinese are.
"""
DETAILS = """# OBS Screen Translator {version}
Live translation of on-screen text for streamers. The text in an OBS source is read, translated by a language model on this PC and drawn over the original. Nothing leaves your computer.

Free and open source under the MIT License. Project page: {project}

# Vibe-coded
The idea, the testing and every decision come from a streamer who is not a programmer. All of the code was written by an AI coding assistant (Claude, by Anthropic). Nobody has reviewed it line by line.

# How it works
1. Four times a second the program asks OBS for a picture of the game source.
2. RapidOCR finds and reads the text, on the graphics card through DirectML or on the processor.
3. TranslateGemma, run by Ollama, translates new text. Every translation is stored, so text seen before appears at once.
4. The browser source draws each translation where the original text is, or in the place chosen for its area.

# On this PC
Settings: {settings}
Stored translations: cache_*.json in {folder}
OBS WebSocket settings: {websocket}
Ollama: {ollama}, model {model}
Text is read on: {reader}
Overlay connection: ws://127.0.0.1:{port}

# Third-party software
The program bundles Python, RapidOCR with the PP-OCR models, ONNX Runtime with DirectML, OpenCV, NumPy, websockets, the Sun Valley theme and other packages, each under its own license. See {notices} and the licenses folder next to the program.
"""
reader = None
THEME = "light"
COLORS = {"dark": {"bg": "#1c1c1c", "fg": "#fafafa", "field": "#232323", "line": "#3a3a3a", "muted": "#a0a0a0"},
          "light": {"bg": "#fafafa", "fg": "#1c1c1c", "field": "#ffffff", "line": "#e0e0e0", "muted": "#5f5f5f"}}
UI = {}
UI_LANGUAGE = "en"
UI_LANGUAGES = {"en": "English", "sk": "Slovenčina"}


class Problem(Exception):
    pass


def _(text):
    return UI.get(text, text)


def plural(n, forms):
    parts = _(forms).split("|")
    index = 0 if n == 1 else 1 if 2 <= n <= 4 or len(parts) < 3 else 2
    return parts[min(index, len(parts) - 1)].format(n=n)


def decimal(value, digits):
    return f"{value:.{digits}f}".replace(".", _("."))


def set_ui_language(code):
    global UI_LANGUAGE
    UI_LANGUAGE = code
    UI.clear()
    if code == "sk":
        UI.update(ui_sk.TEXTS)
        UI[GUIDE], UI[DETAILS] = ui_sk.GUIDE, ui_sk.DETAILS


def language_name(code):
    return ui_sk.LANGUAGES[code] if UI_LANGUAGE == "sk" else LANGUAGES[code]


def short_path(path):
    # The full path contains the Windows user name, which should not end up on a stream.
    text = str(path)
    for name in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        value = os.environ.get(name)
        if value and text.lower().startswith(value.lower()):
            return f"%{name}%" + text[len(value):]
    return text


def windows_theme():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "dark"
    except OSError:
        return "light"


def fonts(widget):
    # The theme gives input fields their font only at the moment it is set; fields made later get it here.
    for child in widget.winfo_children():
        if child.winfo_class() in ("TEntry", "TCombobox", "TSpinbox"):
            child.configure(font="SunValleyBodyFont")
        fonts(child)


def themed(window):
    window.configure(bg=COLORS[THEME]["bg"])
    fonts(window)
    if sys.platform == "win32":
        # Windows draws the title bar itself: attribute 20 turns on its dark mode, 35 gives it the colour of the window (Windows 11).
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        bg = COLORS[THEME]["bg"]
        for attribute, value in ((20, THEME == "dark"), (35, int(bg[5:7] + bg[3:5] + bg[1:3], 16))):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(ctypes.c_int(value)), 4)


def ask_text(parent, title, prompt, initial):
    top = tk.Toplevel(parent)
    top.title(title)
    top.resizable(True, False)
    top.transient(parent)
    result = {}
    frame = ttk.Frame(top, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=prompt).pack(anchor="w")
    entry = ttk.Entry(frame, width=42)
    entry.insert(0, initial)
    entry.pack(fill="x", pady=(8, 14))
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x")

    def done(value):
        result["value"] = value
        top.destroy()
    ttk.Button(buttons, text=_("Cancel"), command=lambda: done(None)).pack(side="right")
    ttk.Button(buttons, text="OK", style="Accent.TButton", command=lambda: done(entry.get())).pack(side="right", padx=(0, 8))
    entry.bind("<Return>", lambda e: done(entry.get()))
    entry.focus_set()
    entry.select_range(0, "end")
    themed(top)
    top.minsize(top.winfo_reqwidth(), top.winfo_reqheight())
    top.grab_set()
    parent.wait_window(top)
    return result.get("value")


def changes():
    name = "CHANGELOG.sk.md" if UI_LANGUAGE == "sk" else "CHANGELOG.md"
    text = (HERE / name).read_text(encoding="utf-8")
    section = re.search(rf"^## {re.escape(VERSION)} .*?$(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
    lines = []
    for line in section.strip().splitlines():
        if lines and lines[-1] and line and not line.startswith("- "):
            lines[-1] += " " + line.strip()
        else:
            lines.append(line)
    body = "**".join(part.replace("*", "").replace("`", "") for part in "\n".join(lines).split("**"))
    return (_("# What's new in {version}").format(version=VERSION) + f"\n{body}\n\n" + _("The changes of every version:")
            + f" {PROJECT}/blob/main/{name}")


def system_language():
    if sys.platform == "win32":
        kernel = ctypes.windll.kernel32
        for number in (kernel.GetUserDefaultLCID(), kernel.GetUserDefaultUILanguage()):
            code = (locale.windows_locale.get(number) or "").split("_")[0]
            if code in LANGUAGES and code != DEFAULTS["source_language"]:
                return code
    return DEFAULTS["target_language"]


def graphics_card():
    try:
        import winreg
        cards = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}") as adapters:
            for n in range(winreg.QueryInfoKey(adapters)[0]):
                try:
                    with winreg.OpenKey(adapters, winreg.EnumKey(adapters, n)) as card:
                        cards.append((winreg.QueryValueEx(card, "HardwareInformation.qwMemorySize")[0], winreg.QueryValueEx(card, "DriverDesc")[0]))
                except OSError:
                    pass
        return max(cards, default=None)
    except OSError:
        return None


def fit(box, place):
    # A translation keeps the proportions of its area: it is made as big as fits into the place and centred in it.
    s = min((place[2] - place[0]) / (box[2] - box[0]), (place[3] - place[1]) / (box[3] - box[1]))
    w, h = (box[2] - box[0]) * s, (box[3] - box[1]) * s
    x, y = (place[0] + place[2] - w) / 2, (place[1] + place[3] - h) / 2
    return [x, y, x + w, y + h]


def unload_model(url, model):
    # keep_alive 0 unloads the model, so the graphics card is free right away instead of after the keep-alive time.
    body = json.dumps({"model": model, "keep_alive": 0}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/api/generate", data=body, headers={"Content-Type": "application/json"}),
                               timeout=5).close()
    except OSError:
        pass


def load_settings(path):
    stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"target_language": system_language()}
    settings = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(stored)}
    single = settings.pop("region", None)
    if single and single != [0, 0, 1, 1] and not settings["regions"]:
        settings["regions"] = [single]
    opacity = settings.pop("opacity", None)
    settings["style"] = {**STYLE, **({} if opacity is None else {"opacity": opacity}), **stored.get("style", {})}
    name = settings.pop("overlay_source", None)
    if name and "overlays" not in stored:
        settings["overlays"] = [{"name": name}]
    settings["regions"] = [r if isinstance(r, dict) else {"box": r, "style": None} for r in settings["regions"]]
    for region in settings["regions"]:
        region["style"] = {**STYLE, **region["style"]} if region.get("style") else None
        region["display"] = region.get("display")
        region["overlay"] = region.get("overlay", 0) if 0 <= region.get("overlay", 0) < len(settings["overlays"]) else 0
    if settings != stored:
        save_settings(path, settings)
    return settings


def save_settings(path, settings):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def key(text):
    return re.sub(r"\W", "", text.lower())


def text_reader(settings):
    global reader
    if reader is None:
        base = {"Global.use_cls": False, "Global.log_level": "error", "Det.limit_type": "max", "Det.limit_side_len": 1280,
                "EngineConfig.onnxruntime.intra_op_num_threads": settings["ocr_threads"]}
        warmup = np.zeros((1080, 1920, 3), np.uint8)
        cv2.putText(warmup, "Warming up the text reader", (500, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        if settings["ocr_on_gpu"]:
            try:
                reader = RapidOCR(params={**base, "EngineConfig.onnxruntime.use_dml": True})
                reader(warmup)
                log(_("text reader ready (graphics card)"))
                return reader
            except Exception as e:
                log(_("reading text on the graphics card failed ({error}); using the processor").format(error=e))
        reader = RapidOCR(params=base)
        reader(warmup)
        log(_("text reader ready (processor)"))
    return reader


def obs_websocket_file():
    files = [pathlib.Path(base).expanduser() / "obs-studio/plugin_config/obs-websocket/config.json"
             for base in (os.environ.get("APPDATA"), "~/.config", "~/Library/Application Support") if base]
    return next((f for f in files if f.exists()), files[0])


def obs_websocket_config():
    file = obs_websocket_file()
    if not file.exists():
        raise Problem(_("OBS WebSocket settings not found. Start OBS once and enable Tools > WebSocket Server Settings > Enable WebSocket server."))
    return json.loads(file.read_text(encoding="utf-8-sig"))


def obs_running():
    return "obs64.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True, text=True,
                                         stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW).stdout


def enable_obs_websocket():
    # OBS reads this file only when it starts, so OBS must be closed. A missing password is generated by OBS itself.
    file = obs_websocket_file()
    config = {}
    if file.exists():
        config = json.loads(file.read_text(encoding="utf-8-sig"))
        backup = file.with_name("config.before-screen-translator.json")
        if not backup.exists():
            shutil.copy2(file, backup)
    config["server_enabled"] = True
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")


class OBS:
    async def connect(self):
        cfg = obs_websocket_config()
        self.ws = await websockets.connect(f"ws://127.0.0.1:{cfg['server_port']}", max_size=None)
        self.n = 0
        identify = {"rpcVersion": 1, "eventSubscriptions": 0}
        auth = json.loads(await self.ws.recv())["d"].get("authentication")
        if auth:
            secret = base64.b64encode(hashlib.sha256((cfg["server_password"] + auth["salt"]).encode()).digest()).decode()
            identify["authentication"] = base64.b64encode(hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
        await self.ws.send(json.dumps({"op": 1, "d": identify}))
        await self.ws.recv()
        return self

    async def request(self, kind, **data):
        self.n += 1
        await self.ws.send(json.dumps({"op": 6, "d": {"requestType": kind, "requestId": str(self.n), "requestData": data}}))
        while True:
            m = json.loads(await self.ws.recv())
            if m["op"] == 7 and m["d"]["requestId"] == str(self.n):
                if not m["d"]["requestStatus"]["result"]:
                    raise RuntimeError(f"{kind}: {m['d']['requestStatus'].get('comment')}")
                return m["d"].get("responseData") or {}


async def obs_video_sources():
    obs = await OBS().connect()
    inputs = (await obs.request("GetInputList"))["inputs"]
    scene = (await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]
    in_scene = [i["sourceName"] for i in (await obs.request("GetSceneItemList", sceneName=scene))["sceneItems"]]
    await obs.ws.close()
    kinds = {i["inputName"]: i["inputKind"] for i in inputs}
    names = sorted(n for n, kind in kinds.items() if not re.search("audio|wasapi|pulse|alsa|browser|text", kind))
    return names, likely_game_source(kinds, in_scene)


def likely_game_source(kinds, in_scene):
    # The only capture card in the current scene, else the only game capture, and so on; with two of a kind nobody can tell.
    for names in ([n for n in in_scene if n in kinds], list(kinds)):
        for kind in ("dshow_input", "game_capture", "window_capture", "monitor_capture"):
            found = [n for n in names if kinds[n] == kind]
            if found:
                return found[0] if len(found) == 1 else None


async def toggle_overlays(names):
    obs = await OBS().connect()
    scenes = [(await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]]
    scenes += [s["sceneName"] for s in (await obs.request("GetSceneList"))["scenes"] if s["sceneName"] != scenes[0]]
    shown = None
    for scene in scenes:
        for item in (await obs.request("GetSceneItemList", sceneName=scene))["sceneItems"]:
            if item["sourceName"] in names and item["inputKind"] == "browser_source":
                if shown is None:
                    shown = not item["sceneItemEnabled"]
                await obs.request("SetSceneItemEnabled", sceneName=scene, sceneItemId=item["sceneItemId"], sceneItemEnabled=shown)
    await obs.ws.close()
    return shown


async def remove_input(name):
    obs = await OBS().connect()
    if any(i["inputName"] == name and i["inputKind"] == "browser_source" for i in (await obs.request("GetInputList"))["inputs"]):
        await obs.request("RemoveInput", inputName=name)
    await obs.ws.close()


def remove_source(name):
    try:
        asyncio.run(remove_input(name))
    except (Problem, OSError, websockets.WebSocketException):
        pass


def install_ollama():
    with urllib.request.urlopen("https://ollama.com/download/OllamaSetup.exe") as response:
        total = int(response.headers["Content-Length"])
        if not ask(_("Ollama, the program that runs the translation model, is not installed.\n\n"
                     "Download it from ollama.com ({size} GB) and install it now?").format(size=decimal(total / 1e9, 1))):
            raise Problem(_("Ollama is not installed. Get it from https://ollama.com/download, install it and press Start again."))
        setup = pathlib.Path(tempfile.gettempdir()) / "OllamaSetup.exe"
        log(_("downloading Ollama..."))
        with open(setup, "wb") as out:
            done = shown = 0
            while chunk := response.read(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if 100 * done // total >= shown + 10:
                    shown = 100 * done // total // 10 * 10
                    log(f"  {shown} %")
    signature = subprocess.run(["powershell", "-NoProfile", "-Command", "$s = Get-AuthenticodeSignature -LiteralPath $env:OLLAMA_SETUP; "
                                "$s.Status.ToString() + ' ' + $s.SignerCertificate.Subject"],
                               env={**os.environ, "OLLAMA_SETUP": str(setup), "PSModulePath": ""}, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    if not signature.startswith("Valid CN=Ollama Inc."):
        setup.unlink()
        raise Problem(_("The downloaded Ollama installer is not signed by Ollama, so it was not started. "
                        "Install Ollama yourself from https://ollama.com/download and press Start again."))
    log(_("installing Ollama..."))
    failed = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]).returncode
    setup.unlink()
    if failed:
        raise Problem(_("Installing Ollama failed. Install it yourself from https://ollama.com/download and press Start again."))
    log(_("Ollama is installed. It may open a window of its own with commands for a terminal: close it, the translator does not need them."))


async def obs_picture(source):
    obs = await OBS().connect()
    data = (await obs.request("GetSourceScreenshot", sourceName=source, imageFormat="png", imageWidth=1920))["imageData"]
    await obs.ws.close()
    return data.split(",", 1)[1]


def same_text(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85


def covered(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w > 0 and h > 0 and w * h > 0.5 * (a[2] - a[0]) * (a[3] - a[1])


def direction(angle):
    return np.array((math.cos(math.radians(angle)), math.sin(math.radians(angle))))


def overlap(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w > 0 and h > 0 and w * h > 0.3 * min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


class Translator:
    def __init__(self, settings, folder):
        self.s = settings
        src, dst = (f"{LANGUAGES[settings[k]]} ({settings[k]})" for k in ("source_language", "target_language"))
        src_name, dst_name = LANGUAGES[settings["source_language"]], LANGUAGES[settings["target_language"]]
        self.prompt = (f"You are a professional {src} to {dst} translator. Your goal is to accurately convey the meaning and nuances "
                       f"of the original {src_name} text while adhering to {dst_name} grammar, vocabulary, and cultural sensitivities. "
                       f"{settings['context']}\n"
                       f"Produce only the {dst_name} translation, without any additional explanations or commentary. "
                       f"Please translate the following {src_name} text into {dst_name}:\n\n\n")
        self.cache_file = folder / f"cache_{hashlib.md5((settings['model'] + self.prompt).encode()).hexdigest()[:8]}.json"
        self.cache = json.loads(self.cache_file.read_text(encoding="utf-8")) if self.cache_file.exists() else {}
        self.obs = None
        self.closed = False
        self.direct = None
        self.touched = 0.0
        self.sample = None
        self.count = 0
        self.aspect = 16 / 9
        self.reset = False

    def ollama(self, path, body=None, timeout=60):
        request = urllib.request.Request(self.s["ollama_url"] + path, data=body and json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(request, timeout=timeout)

    def prepare_model(self):
        log(_("preparing the translation model, this can take a while..."))
        try:
            self.ollama("/api/version").close()
        except OSError:
            program = shutil.which("ollama") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            if not os.path.exists(program):
                install_ollama()
                program = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            log(_("starting Ollama..."))
            subprocess.Popen([program, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for attempt in range(30):
                time.sleep(1)
                try:
                    self.ollama("/api/version").close()
                    break
                except OSError:
                    pass
            else:
                raise Problem(_("Ollama did not start. Start it yourself and press Start again."))
        with self.ollama("/api/tags") as response:
            installed = [m["name"] for m in json.loads(response.read())["models"]]
        if self.s["model"] not in installed:
            log(_("downloading the translation model {model} (several gigabytes, once)...").format(model=self.s["model"]))
            shown = -10
            with self.ollama("/api/pull", {"model": self.s["model"]}, timeout=None) as response:
                for line in response:
                    step = json.loads(line)
                    if step.get("error"):
                        raise Problem(_("The model could not be downloaded: {error}").format(error=step["error"]))
                    percent = 100 * step.get("completed", 0) // step["total"] if step.get("total") else None
                    if percent is not None and percent >= shown + 10:
                        shown = percent
                        log(f"  {percent} %")
        hello = self.translate(["Hello there."])[0]
        log(_("translation model ready: {model} | {sample} | {cached} | {connection}").format(
            model=self.s["model"], sample=hello, cached=plural(len(self.cache), "{n} cached translation|{n} cached translations"),
            connection=_("direct connection to the model") if self.direct else _("through Ollama")))

    # visible: the translation sources shown in OBS; areas whose source is hidden are not read.
    def read(self, frame, visible=None):
        h, w = frame.shape[:2]
        self.aspect = w / h
        picture, strips = frame, [(0, h, 0, 0, None)]
        if not self.s["regions"] and visible is not None and 0 not in visible:
            return []
        if self.s["regions"]:
            areas = [(n, *(int(a * b) for a, b in zip(region["box"], (w, h, w, h)))) for n, region in enumerate(self.s["regions"])
                     if visible is None or region["overlay"] in visible]
            if not areas:
                return []
            picture = np.zeros((sum(b - t for n, l, t, r, b in areas) + 16 * (len(areas) - 1), max(r - l for n, l, t, r, b in areas), 3), np.uint8)
            strips, y = [], 0
            for n, l, t, r, b in areas:
                picture[y:y + b - t, :r - l] = frame[t:b, l:r]
                strips.append((y, y + b - t, l, t, n))
                y += b - t + 16
        r = text_reader(self.s)(picture)
        # Every line comes as four corners, so a tilted line (a phone in a hand) is measured along its own direction:
        # its true height, and where the next line starts below it, instead of an upright box around it.
        lines = []
        for quad, text, score in zip(r.boxes, r.txts, r.scores) if r.txts else ():
            middle = (quad[:, 1].min() + quad[:, 1].max()) / 2
            start, stop, left, top, region = min(strips, key=lambda s: max(s[0] - middle, middle - s[1], 0))
            p = quad.astype(float) + (left, top - start)
            width, height = float(np.hypot(*(p[1] - p[0]))), float(np.hypot(*(p[3] - p[0])))
            angle = math.degrees(math.atan2(p[1][1] - p[0][1], p[1][0] - p[0][0])) if width >= 2 * height else None
            if score >= self.s["min_score"] and height * 1080 / h >= self.s["min_height"] and re.search(r"[^\W\d_]{2}", text):
                # A line with fewer than three letters in a row ("go.") may end a block, but is never translated on its own.
                lines.append(types.SimpleNamespace(p=p, width=width, height=height, angle=angle, text=" ".join(text.split()), region=region,
                                                   short=not re.search(r"[^\W\d_]{3}", text)))
        blocks = []
        for line in sorted(lines, key=lambda line: (line.p[0][1], line.p[0][0])):
            for b in blocks:
                last = b.lines[-1]
                u = direction(last.angle if last.angle is not None else b.angle)
                along, across = float((line.p[0] - last.p[0]) @ u), float((line.p[0] - last.p[0]) @ (-u[1], u[0]))
                shift = along + line.width / 2 - last.width / 2
                if (0.5 * last.height < across < last.height + 0.6 * line.height and 0.7 < line.height / last.height < 1.4
                        and (line.angle is None or last.angle is None or abs(line.angle - last.angle) < 4)
                        and (abs(along) < 1.5 * line.height or abs(shift) < 1.5 * line.height)):
                    b.lines.append(line)
                    b.centered += abs(shift) < 2 * abs(along)
                    break
            else:
                if not line.short:
                    blocks.append(types.SimpleNamespace(lines=[line], centered=0, region=line.region, angle=line.angle or 0))
        result = []
        for b in blocks:
            angles = [line.angle for line in b.lines if line.angle is not None]
            angle = sum(angles) / len(angles) if angles else 0.0
            angle = 0.0 if abs(angle) < 2 else angle
            u = direction(angle)
            corners = np.vstack([line.p for line in b.lines])
            along, across = corners @ u, corners @ (-u[1], u[0])
            width, height = float(np.ptp(along)), float(np.ptp(across))
            cx, cy = (u * (along.max() + along.min()) / 2 + np.array((-u[1], u[0])) * (across.max() + across.min()) / 2) / (w, h)
            box = [float(cx - width / w / 2), float(cy - height / h / 2), float(cx + width / w / 2), float(cy + height / h / 2)]
            result.append(types.SimpleNamespace(text=" ".join(line.text for line in b.lines), box=box, rows=len(b.lines), region=b.region,
                                                line_height=height / h / len(b.lines), angle=round(angle, 1),
                                                centered=b.centered > 0 if len(b.lines) > 1 else abs(box[0] + box[2] - 1) < 0.04))
        return result

    # Ollama spends about a third of a second on every request before the model starts working, so after the first answer the
    # program talks to the llama-server that Ollama started for the model, as long as it answers exactly like Ollama does.
    def ask_model(self, text):
        if self.direct:
            try:
                answer = self.ask_direct(self.direct, text)
                if time.monotonic() - self.touched > 300:
                    self.touched = time.monotonic()
                    threading.Thread(target=self.touch, daemon=True).start()
                return answer
            except (OSError, ValueError, KeyError):
                self.direct = None
        answer = self.ask_ollama(text)
        if self.direct is None:
            self.direct = self.find_direct()
            self.touched = time.monotonic()
        return answer

    def ask_ollama(self, text):
        if self.closed:
            raise Problem(_("the program is closing"))
        body = {"model": self.s["model"], "messages": [{"role": "user", "content": self.prompt + text}], "stream": False,
                "keep_alive": "30m", "options": OPTIONS}
        with self.ollama("/api/chat", body) as response:
            return json.loads(response.read())["message"]["content"]

    def ask_direct(self, url, text):
        body = {"prompt": f"<start_of_turn>user\n{self.prompt}{text}<end_of_turn>\n<start_of_turn>model\n", **DIRECT}
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())["content"]

    def find_direct(self):
        try:
            with self.ollama("/api/show", {"model": self.s["model"]}) as response:
                show = json.loads(response.read())
            if "<start_of_turn>" not in show.get("template", ""):
                return False
            model_file = re.search(r"^FROM (.+)$", show["modelfile"], re.M).group(1).strip().lower()
            lines = subprocess.run(["powershell", "-NoProfile", "-Command",
                                    "(Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\").CommandLine"],
                                   env={**os.environ, "PSModulePath": ""}, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW).stdout.splitlines()
            port = re.search(r"--port\s+(\d+)", next(line for line in lines if model_file in line.lower())).group(1)
            url = f"http://127.0.0.1:{port}/completion"
            check = "I told you, we do this my way or not at all."
            return url if self.ask_direct(url, check).strip() == self.ask_ollama(check).strip() else False
        except (OSError, ValueError, KeyError, AttributeError, StopIteration):
            return False

    def touch(self):
        try:
            self.ollama("/api/generate", {"model": self.s["model"], "keep_alive": "30m", "stream": False, "options": OPTIONS}).close()
        except OSError:
            pass

    def region(self, n):
        regions = self.s["regions"]
        return regions[n] if n is not None and 0 <= n < len(regions) else None

    def style(self, n):
        region = self.region(n)
        return region["style"] if region and region["style"] else self.s["style"]

    def overlay(self, n):
        region = self.region(n)
        return region["overlay"] if region else 0

    # An area can show its translations elsewhere: the boxes are moved from where they are read to where they are shown and
    # scaled by the same factor in both directions, so the text keeps its proportions.
    def place(self, n, box, line_height):
        region = self.region(n)
        if not region or not region["display"]:
            return box, line_height
        (a0, b0, a1, b1), (c0, d0, c1, d1) = region["box"], fit(region["box"], region["display"])
        s = (c1 - c0) / (a1 - a0)
        return [c0 + (box[0] - a0) * s, d0 + (box[1] - b0) * s, c0 + (box[2] - a0) * s, d0 + (box[3] - b0) * s], line_height * s

    # While the look editor is open, a sample translation shows the chosen look in OBS; while the areas are being chosen,
    # every area shows its number where its translations will appear.
    def sample_items(self):
        if self.sample is None:
            return []
        items = []
        for n in range(len(self.s["regions"])) if self.sample == "areas" else [self.sample]:
            region = self.region(n)
            box = (fit(region["box"], region["display"]) if region["display"] else region["box"]) if region else [0.2, 0.8, 0.8, 0.86]
            middle, height = (box[1] + box[3]) / 2, min(0.034, box[3] - box[1])
            items.append({"id": f"sample-{n}", "text": _("Area {n}").format(n=n + 1) if self.sample == "areas" else _(SAMPLE),
                          "box": [box[0] + 0.01, middle - height / 2, box[2] - 0.01, middle + height / 2], "rows": 1,
                          "line_height": height, "centered": True, "style": self.style(n), "overlay": self.overlay(n)})
        return items

    def moved(self, b, t):
        return math.hypot((b.box[0] + b.box[2] - t.box[0] - t.box[2]) / 2 * self.aspect, (b.box[1] + b.box[3] - t.box[1] - t.box[3]) / 2) / t.line_height

    # New text is shown after it has been read twice in nearly the same place, so text that sweeps across the picture with the
    # camera is skipped. A translation on screen then follows its text while it moves less than 2.5 line heights between reads,
    # like a phone in a hand, and an old translation stays until the text that took its place is translated.
    def follow(self, tracks, blocks, now, started):
        for b in blocks:
            matches = [t for t in tracks if t.seen != now and (same_text(b.text, t.text) or not t.sentence and overlap(b.box, t.box)
                                                               and (key(t.text) in key(b.text) or key(b.text) in key(t.text)))]
            t = min(matches, key=lambda t: self.moved(b, t), default=None)
            if t:
                step = self.moved(b, t)
                t.stable = step < (2.5 if t.stable else 0.6)
                t.seen, t.replaced = now, None
                # Two reads of a still picture differ by a pixel or two, and a menu item is sometimes read together with its
                # neighbour; the translation moves only when the same text really moved, turned or changed its size.
                size = max(abs((b.box[2] - b.box[0]) / (t.box[2] - t.box[0]) - 1), abs((b.box[3] - b.box[1]) / (t.box[3] - t.box[1]) - 1))
                if same_text(b.text, t.text) and (step >= 0.25 or abs(b.angle - t.angle) >= 2 or size >= 0.25 or b.rows != t.rows):
                    t.box, t.angle, t.rows, t.line_height, t.centered = b.box, b.angle, b.rows, b.line_height, b.centered
                continue
            self.count += 1
            for old in tracks:
                if old.seen != now and overlap(old.box, b.box):
                    old.replaced = self.count
            words = re.findall(r"[^\W\d_]+", b.text)
            tracks.append(types.SimpleNamespace(id=self.count, text=b.text, box=b.box, angle=b.angle, rows=b.rows, line_height=b.line_height,
                                                centered=b.centered, region=b.region, seen=now, since=started, stable=False, replaced=None,
                                                translation=self.cache.get(key(b.text)), logged=False,
                                                sentence=sum(not x.isupper() for x in words) >= 2))
        shown = {t.id for t in self.showing(tracks)}
        tracks[:] = [t for t in tracks if now - t.seen <= self.s["linger"] or t.replaced and t.replaced not in shown and now - t.seen <= 3]

    # Bigger blocks first; a translation whose place is mostly taken by one already shown (a line read on its own) is left out.
    def showing(self, tracks):
        ready = {t.id for t in tracks if t.stable and t.translation}
        shown = []
        for t in sorted((t for t in tracks if t.id in ready), key=lambda t: -t.rows):
            if t.replaced not in ready and not any(covered(t.box, s.box) for s in shown):
                shown.append(t)
        return shown

    def tidy(self, text, translation):
        translation = " ".join(translation.split())
        if "(" not in text:
            # The model sometimes adds a remark in brackets, such as that a sentence is unfinished; it is not in the text.
            translation = re.sub(r"\s*\([^)]*\)", "", translation).strip()
        if translation.endswith(".") and not text.endswith("."):
            translation = translation[:-1]
        if text.isupper():
            translation = translation.upper()
        return "" if key(translation) == key(text) or len(translation) > 3 * len(text) + 20 else translation

    def translate(self, texts):
        try:
            if len(texts) > 1:
                answers = [x for x in self.ask_model("\n".join(texts)).split("\n") if x.strip()]
                if len(answers) == len(texts):
                    return [self.tidy(a, b) for a, b in zip(texts, answers)]
            return [self.tidy(a, self.ask_model(a)) for a in texts]
        except Exception as e:
            log(_("translation failed: {error}").format(error=e))
            return [None] * len(texts)

    async def frame(self, obs):
        d = (await obs.request("GetSourceScreenshot", sourceName=self.s["obs_source"], imageFormat="jpg", imageWidth=1920,
                               imageCompressionQuality=85))["imageData"]
        return cv2.imdecode(np.frombuffer(base64.b64decode(d.split(",", 1)[1]), np.uint8), cv2.IMREAD_COLOR)

    async def prepare_overlays(self, obs):
        video = await obs.request("GetVideoSettings")
        existing = {i["inputName"]: i["inputKind"] for i in (await obs.request("GetInputList"))["inputs"]}
        # The address carries a fingerprint of the page, so OBS loads it again whenever the page changes.
        page = hashlib.md5((HERE / "overlay.html").read_bytes()).hexdigest()[:8]
        for n, overlay in enumerate(self.s["overlays"]):
            name = overlay["name"]
            if existing.get(name, "browser_source") != "browser_source":
                raise Problem(_('OBS already has a source named "{name}" that is not a browser source. In Look of translations, '
                                'remove this translation source and add one with another name.').format(name=name))
            url = (HERE / "overlay.html").as_uri() + (f"?scale={video['baseWidth'] / 1920:g}&ws=ws://127.0.0.1:{self.s['port']}"
                                                      f"&overlay={n}&v={page}")
            if name in existing:
                if (await obs.request("GetInputSettings", inputName=name))["inputSettings"].get("url", "") != url:
                    await obs.request("SetInputSettings", inputName=name, inputSettings={"url": url})
                continue
            scenes = self.s["scenes"] or [(await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]]
            await obs.request("CreateInput", sceneName=scenes[0], inputName=name, inputKind="browser_source",
                              inputSettings={"url": url, "width": video["baseWidth"], "height": video["baseHeight"], "shutdown": False,
                                             "restart_when_active": False})
            for scene in scenes[1:]:
                await obs.request("CreateSceneItem", sceneName=scene, sourceName=name)
            log(_('added the browser source "{name}" to: {scenes}').format(name=name, scenes=", ".join(scenes)))

    async def visible_overlays(self, obs):
        try:
            scene = (await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]
            shown = {i["sourceName"] for i in (await obs.request("GetSceneItemList", sceneName=scene))["sceneItems"] if i["sceneItemEnabled"]}
        except RuntimeError:
            return set()
        return {n for n, overlay in enumerate(self.s["overlays"]) if overlay["name"] in shown}

    async def run(self, publish):
        self.obs = obs = await OBS().connect()
        log(_("connected to OBS"))
        if self.s["create_overlay_source"]:
            await self.prepare_overlays(obs)
        loop = asyncio.get_running_loop()
        tracks = []
        state = types.SimpleNamespace(job=None, error=None, dirty=False, active=None)

        def send():
            shown = self.showing(tracks)
            for t in shown:
                if not t.logged:
                    t.logged = True
                    log(f"{decimal(time.monotonic() - t.since, 2)} s  {t.text}\n          {t.translation}")
            items = []
            for t in shown:
                box, line_height = self.place(t.region, t.box, t.line_height)
                items.append({"id": t.id, "text": t.translation, "box": box, "rows": t.rows, "line_height": line_height, "angle": t.angle,
                              "centered": t.centered, "style": self.style(t.region), "overlay": self.overlay(t.region)})
            publish({"items": items + self.sample_items()})

        def done(batch, translations):
            state.job = None
            for t, translation in zip(batch, translations):
                t.translation = translation or ""
                if translation is not None:
                    self.cache[key(t.text)] = translation
                    state.dirty = True
            next_job()
            send()

        def next_job():
            for t in tracks:
                if t.translation is None:
                    t.translation = self.cache.get(key(t.text))
            waiting = sorted((t for t in tracks if t.translation is None and (t.stable or t.sentence)),
                             key=lambda t: (not t.stable, not t.sentence, -t.line_height))
            if waiting and not state.job:
                batch = waiting[:1] if waiting[0].sentence else list({key(t.text): t for t in waiting if not t.sentence}.values())[:12]
                state.job = loop.run_in_executor(None, self.translate, [t.text for t in batch])
                state.job.add_done_callback(lambda f: f.cancelled() or done(batch, f.result()))

        while True:
            started = time.monotonic()
            visible = await self.visible_overlays(obs)
            active = bool(visible)
            if active != state.active:
                state.active = active
                log(_("translating") if active else _("paused (no translation source is shown in the current scene)"))
            if not active:
                tracks.clear()
                send()
                await asyncio.sleep(0.5)
                continue
            try:
                blocks = await loop.run_in_executor(None, self.read, await self.frame(obs), visible)
                state.error = None
            except RuntimeError as e:
                if str(e) != state.error:
                    log(_("screenshot failed: {error}").format(error=e))
                state.error, blocks = str(e), []
            if self.reset:
                self.reset = False
                tracks.clear()
            self.follow(tracks, blocks, time.monotonic(), started)
            next_job()
            send()
            if state.dirty:
                state.dirty = False
                self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=0), encoding="utf-8")
            await asyncio.sleep(max(0, self.s["interval"] - (time.monotonic() - started)))

    async def serve(self):
        clients = set()
        last = {"message": json.dumps({"items": []})}

        async def client(ws):
            clients.add(ws)
            try:
                await ws.send(last["message"])
                await ws.wait_closed()
            finally:
                clients.discard(ws)

        def publish(obj):
            message = json.dumps(obj, ensure_ascii=False)
            if message != last["message"]:
                last["message"] = message
                websockets.broadcast(clients, message)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.prepare_model)
        await loop.run_in_executor(None, text_reader, self.s)
        async with websockets.serve(client, "127.0.0.1", self.s["port"]):
            while True:
                try:
                    await self.run(publish)
                except (OSError, websockets.ConnectionClosed):
                    publish({"items": []})
                    log(_("OBS is not reachable, retrying in 3 s"))
                    await asyncio.sleep(3)
                finally:
                    if self.obs:
                        await self.obs.ws.close()
                        self.obs = None

    async def preview(self, image, folder):
        self.prepare_model()
        frame = cv2.imdecode(np.fromfile(image, np.uint8), cv2.IMREAD_COLOR) if image else await self.frame(await OBS().connect())
        h, w = frame.shape[:2]
        text_reader(self.s)
        started = time.perf_counter()
        blocks = self.read(frame)
        log(f"reading took {(time.perf_counter() - started) * 1000:.0f} ms, {len(blocks)} texts")
        for x0, y0, x1, y1 in (region["box"] for region in self.s["regions"]):
            cv2.rectangle(frame, (int(x0 * w), int(y0 * h)), (int(x1 * w) - 1, int(y1 * h) - 1), (0, 204, 255), 2)
        for b in blocks:
            cv2.rectangle(frame, (int(b.box[0] * w), int(b.box[1] * h)), (int(b.box[2] * w), int(b.box[3] * h)), (0, 255, 0), 2)
            log(f"  {b.text}\n    -> {self.translate([b.text])[0] or '(no translation)'}")
        (folder / "preview.png").write_bytes(cv2.imencode(".png", frame)[1])
        log(f"frame with the detected texts: {folder / 'preview.png'}")


class Window:
    def __init__(self, settings_file):
        global log, ask, THEME
        self.file = settings_file
        self.s = load_settings(settings_file)
        self.messages = queue.Queue()
        self.loop = self.task = self.translator = self.retry = self.said = self.websocket = self.listener = None
        self.editor = self.sample = None
        self.restart = self.looking = self.started = self.running = False
        self.sources = []
        self.card = graphics_card()
        log = self.messages.put
        ask = self.ask
        set_ui_language(self.s["ui_language"] or ("sk" if system_language() == "sk" else "en"))
        self.root = root = tk.Tk()
        THEME = windows_theme()
        sv_ttk.set_theme(THEME, root)
        root.title(f"OBS Screen Translator {VERSION}")
        # The theme sizes its fonts in pixels; they are scaled to the display like the rest of Windows.
        scale = root.winfo_fpixels("1i") / 96
        for name in tkfont.names(root):
            if name.startswith("SunValley"):
                font = tkfont.Font(root=root, name=name, exists=True)
                font.configure(size=round(font.cget("size") * scale))
        root.option_add("*TCombobox*Listbox.font", "SunValleyBodyFont")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.build()
        themed(root)
        # A smaller window keeps four lines of the activity list instead of nine.
        line = tkfont.Font(root=root, font=self.text.cget("font")).metrics("linespace")
        root.minsize(root.winfo_reqwidth(), root.winfo_reqheight() - 5 * line)
        root.after(100, self.pump)
        self.listen_for_key()
        self.refresh()

    def build(self):
        root = self.root
        muted = COLORS[THEME]["muted"]
        self.labels = {f"{language_name(code)} ({code})": code for code in LANGUAGES}
        names = sorted(self.labels, key=lambda label: unicodedata.normalize("NFD", label.lower()))
        self.models = {_(text): name for name, text in MODELS.items()}
        if self.s["model"] not in MODELS:
            self.models[self.s["model"]] = self.s["model"]
        self.page = page = ttk.Frame(root, padding=(22, 16, 22, 20))
        page.pack(fill="both", expand=True)
        head = ttk.Frame(page)
        head.pack(fill="x")
        ttk.Label(head, text="OBS Screen Translator", font="SunValleyTitleFont").pack(side="left")
        ttk.Label(head, text=VERSION, font="SunValleyCaptionFont", foreground=muted).pack(side="left", anchor="s", padx=10, pady=(0, 7))
        help_button = ttk.Menubutton(head, text=_("Help"))
        help_button.pack(side="right")
        menu = tk.Menu(help_button, tearoff=False)
        news = _("What's new in {version}").format(version=VERSION)
        menu.add_command(label=_("Installation and setup"), command=lambda: Page(root, _("Installation and setup"), _(GUIDE)))
        menu.add_command(label=news, command=lambda: Page(root, news, changes()))
        menu.add_command(label=_("Details"), command=self.details)
        menu.add_separator()
        menu.add_command(label=_("Open the settings folder"), command=lambda: os.startfile(self.file.parent))
        menu.add_command(label=_("Project page"), command=lambda: webbrowser.open(PROJECT))
        help_button.configure(menu=menu)
        language_button = ttk.Menubutton(head, text=UI_LANGUAGES[UI_LANGUAGE])
        language_button.pack(side="right", padx=(0, 8))
        menu = tk.Menu(language_button, tearoff=False)
        self.ui_language = tk.StringVar(value=UI_LANGUAGE)
        for code, name in UI_LANGUAGES.items():
            menu.add_radiobutton(label=name, value=code, variable=self.ui_language, command=self.switch_language)
        language_button.configure(menu=menu)
        ttk.Label(page, text=_("Live translation of the text in an OBS source, drawn over the original."), foreground=muted).pack(anchor="w")
        body = tkfont.Font(root=root, name="SunValleyBodyFont", exists=True)
        cards, widths = [], []

        def card(title):
            ttk.Label(page, text=title, font="SunValleyBodyStrongFont").pack(anchor="w", pady=(16, 6))
            frame = ttk.Frame(page, style="Card.TFrame", padding=(16, 10))
            frame.pack(fill="x")
            frame.columnconfigure(1, weight=1)
            cards.append(frame)
            return frame

        def line(frame, n, text, widget, button=None):
            ttk.Label(frame, text=text).grid(row=n, column=0, sticky="w", pady=5)
            widths.append(body.measure(text))
            widget.grid(row=n, column=1, columnspan=1 if button else 2, sticky="ew", padx=(8, 0))
            if button:
                button.grid(row=n, column=2, sticky="ew", padx=(12, 0))

        translation = card(_("Translation"))
        self.source = ttk.Combobox(translation, values=names, state="readonly")
        line(translation, 0, _("Translate from"), self.source)
        self.target = ttk.Combobox(translation, values=names, state="readonly")
        line(translation, 1, _("Translate to"), self.target)
        self.model = ttk.Combobox(translation, values=list(self.models), state="readonly")
        line(translation, 2, _("Model"), self.model)
        if self.card:
            ttk.Label(translation, foreground=muted, text=_("This PC: {card} with {memory} GB of graphics memory.").format(
                card=self.card[1], memory=round(self.card[0] / 2 ** 30))).grid(row=3, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(0, 4))
        game = card(_("Game"))
        self.obs_source = ttk.Combobox(game, values=self.sources)
        line(game, 0, _("Source in OBS"), self.obs_source, ttk.Button(game, text=_("Refresh"), width=12, command=self.refresh))
        self.area = ttk.Label(game)
        line(game, 1, _("Areas to read"), self.area, ttk.Button(game, text=_("Choose..."), width=12, command=self.choose_area))
        screen = card(_("On screen"))
        self.look_label = ttk.Label(screen, wraplength=440)
        self.look_label.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(e.width, 200)))
        line(screen, 0, _("Look"), self.look_label, ttk.Button(screen, text=_("Edit..."), width=12,
                                                            command=lambda: self.editor.top.lift() if self.editor else StyleEditor(self)))
        self.key = ttk.Label(screen)
        line(screen, 1, _("Show/hide key"), self.key, ttk.Button(screen, text=_("Set..."), width=12, command=lambda: KeyPicker(self)))
        self.auto = tk.BooleanVar(value=self.s["start_automatically"])
        ttk.Checkbutton(screen, text=_("Start translating when this program opens"), variable=self.auto, style="Switch.TCheckbutton",
                        command=self.remember).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 4))
        for frame in cards:
            frame.columnconfigure(0, minsize=max(widths) + 12)
        action = ttk.Frame(page)
        action.pack(fill="x", pady=(18, 0))
        self.button = ttk.Button(action, width=14, style="Accent.TButton", command=self.toggle)
        self.button.pack(side="left")
        self.status = ttk.Label(action, foreground=muted)
        self.status.pack(side="left", padx=14)
        ttk.Label(page, text=_("Activity"), font="SunValleyBodyStrongFont").pack(anchor="w", pady=(16, 6))
        frame = ttk.Frame(page)
        frame.pack(fill="both", expand=True)
        mono = "Cascadia Mono" if "Cascadia Mono" in tkfont.families(root) else "Consolas"
        colors = COLORS[THEME]
        self.text = tk.Text(frame, height=9, wrap="word", state="disabled", relief="flat", borderwidth=0, padx=12, pady=8,
                            font=(mono, 9), bg=colors["field"], fg=colors["fg"], highlightthickness=1,
                            highlightbackground=colors["line"], highlightcolor=colors["line"], selectbackground="#2f60d8")
        bar = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y", padx=(6, 0))
        self.text.pack(fill="both", expand=True)
        self.source.set(self.label(self.s["source_language"]))
        self.target.set(self.label(self.s["target_language"]))
        self.model.set(next(label for label, name in self.models.items() if name == self.s["model"]))
        self.obs_source.set(self.s["obs_source"])
        self.show_area()
        self.show_look()
        self.show_key()
        self.show_state()
        for box in (self.source, self.target, self.obs_source, self.model):
            box.bind("<<ComboboxSelected>>", self.changed)

    def show_sample(self, sample):
        self.sample = sample
        if self.translator:
            self.translator.sample = sample

    # New areas take effect at once, also while translating: the running translator reads them from the next picture on.
    def set_regions(self, regions):
        self.s["regions"] = regions
        save_settings(self.file, self.s)
        if self.translator:
            self.translator.s["regions"] = regions
            self.translator.reset = True
        self.show_area()
        self.show_look()

    def label(self, code):
        return next(label for label, value in self.labels.items() if value == code)

    def switch_language(self):
        self.s["ui_language"] = self.ui_language.get()
        save_settings(self.file, self.s)
        set_ui_language(self.s["ui_language"])
        if self.editor:
            self.editor.close()
        activity = self.text.get("1.0", "end-1c")
        self.page.destroy()
        self.build()
        fonts(self.root)
        self.text.configure(state="normal")
        self.text.insert("end", activity)
        self.text.see("end")
        self.text.configure(state="disabled")

    def ask(self, question):
        answer = queue.Queue()
        self.messages.put(lambda: answer.put(messagebox.askyesno("OBS Screen Translator", question, parent=self.root)))
        return answer.get()

    def say(self, message):
        if message != self.said:
            self.said = message
            log(message)

    def refresh(self):
        if self.retry:
            self.root.after_cancel(self.retry)
            self.retry = None
        if not self.looking:
            self.looking = True
            threading.Thread(target=self.look, daemon=True).start()

    def look(self):
        try:
            names, suggestion = asyncio.run(obs_video_sources())
            self.messages.put(lambda: self.found(names, suggestion))
        except (Problem, OSError, websockets.WebSocketException):
            self.say(self.without_obs())
            self.messages.put(self.look_again)

    def look_again(self):
        self.looking = False
        self.retry = self.root.after(3000, self.refresh)

    def without_obs(self):
        file = obs_websocket_file()
        if not file.parents[2].exists():
            return _("Waiting for OBS. Install OBS Studio from https://obsproject.com and start it.")
        if file.exists() and json.loads(file.read_text(encoding="utf-8-sig")).get("server_enabled"):
            return _("Waiting for OBS. Start it; if it is running, check Tools > WebSocket Server Settings > Enable WebSocket server.")
        if self.websocket is None:
            self.websocket = ask(_("The WebSocket server in OBS is turned off. The translator needs it to get the picture of the game "
                                   "and to show the translations.\n\nTurn it on now? The current OBS setting is kept in a backup file."))
        if not self.websocket:
            return _("The WebSocket server in OBS is off. Turn it on in OBS: Tools > WebSocket Server Settings > Enable WebSocket server.")
        if obs_running():
            return _("Close OBS now: its WebSocket server will be turned on as soon as OBS is closed.")
        enable_obs_websocket()
        return _("The WebSocket server in OBS is turned on. Start OBS.")

    def found(self, names, suggestion):
        self.looking = False
        if self.said:
            log(_("OBS found."))
        self.said = None
        self.sources = names
        self.obs_source.configure(values=names)
        if not self.s["obs_source"] and suggestion:
            self.obs_source.set(suggestion)
            self.changed()
            log(_('Game source chosen automatically: "{source}". Pick another one in the list if this is not the game.').format(source=suggestion))
        if not self.s["obs_source"]:
            log(_("Choose the game source and press Start."))
        elif self.auto.get() and not self.started and not self.loop:
            self.toggle()

    def details(self):
        folder = pathlib.Path(sys.executable).parent if FROZEN else HERE
        Page(self.root, _("Details"), _(DETAILS).format(
            version=VERSION, project=PROJECT, settings=short_path(self.file), folder=short_path(self.file.parent),
            websocket=short_path(obs_websocket_file()), ollama=self.s["ollama_url"], model=self.s["model"], port=self.s["port"],
            reader=_("the graphics card (the processor if that fails)") if self.s["ocr_on_gpu"] else _("the processor"),
            notices=short_path(folder / "THIRD_PARTY_NOTICES.md")))

    def show_look(self):
        st = self.s["style"]
        own = sum(1 for region in self.s["regions"] if region["style"])
        sources = len(self.s["overlays"])
        size = f"{st['size']} px" if st["size"] else _("size of the original")
        text = _("{font}, {size}, background {opacity} %").format(font=st["font"], size=size, opacity=round(st["opacity"] * 100))
        more = [plural(own, "{n} area with a look of its own|{n} areas with a look of its own")] if own else []
        more += [plural(sources, "{n} OBS source|{n} OBS sources")] if sources > 1 else []
        self.look_label.configure(text=text + ("\n" + ", ".join(more) if more else ""))

    def show_key(self):
        self.key.configure(text=self.s["hotkey"]["label"] if self.s["hotkey"] else _("None"))

    def show_state(self):
        self.button.configure(text=_("Stop") if self.running else _("Start"))
        self.status.configure(text=f"{self.source.get()} → {self.target.get()}" if self.running else _("Stopped"))

    def remember(self):
        self.s["start_automatically"] = self.auto.get()
        save_settings(self.file, self.s)

    def set_key(self, hotkey):
        self.s["hotkey"] = hotkey
        save_settings(self.file, self.s)
        if self.listener:
            ctypes.windll.user32.PostThreadMessageW(self.listener.native_id, 0x0012, 0, 0)
            self.listener.join(1)
            self.listener = None
        self.listen_for_key()

    def listen_for_key(self):
        self.show_key()
        if self.s["hotkey"]:
            self.listener = threading.Thread(target=self.listen, args=(self.s["hotkey"],), daemon=True)
            self.listener.start()

    def listen(self, hotkey):
        user = ctypes.windll.user32
        if not user.RegisterHotKey(None, 1, hotkey["modifiers"] | 0x4000, hotkey["key"]):
            log(_("The key {key} is taken by another program. Set another one.").format(key=hotkey["label"]))
            return
        message = ctypes.wintypes.MSG()
        while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == 0x0312:
                try:
                    if asyncio.run(toggle_overlays([overlay["name"] for overlay in self.s["overlays"]])) is None:
                        log(_("There is nothing to show or hide yet. Press Start first."))
                except (Problem, OSError, websockets.WebSocketException):
                    log(_("The key was pressed, but OBS is not reachable."))
        user.UnregisterHotKey(None, 1)

    def show_area(self):
        count = len(self.s["regions"])
        moved = sum(1 for region in self.s["regions"] if region["display"])
        text = plural(count, "{n} area|{n} areas") if count else _("Whole picture")
        self.area.configure(text=text + (", " + plural(moved, "{n} shown elsewhere") if moved else ""))
        if self.editor:
            self.editor.close()

    def choose_area(self):
        source = self.obs_source.get().strip()
        if not source:
            log(_("Choose the game source in OBS first."))
            return

        def work():
            try:
                picture = asyncio.run(obs_picture(source))
                self.messages.put(lambda: AreaPicker(self, picture))
            except Problem as e:
                log(str(e))
            except (OSError, RuntimeError, websockets.WebSocketException) as e:
                log(_("Could not get a picture from OBS: {error}").format(error=e))
        threading.Thread(target=work, daemon=True).start()

    def changed(self, event=None):
        model = self.models[self.model.get()]
        if model != self.s["model"] and self.started and not self.loop:
            threading.Thread(target=unload_model, args=(self.s["ollama_url"], self.s["model"]), daemon=True).start()
        if model != self.s["model"] and self.card and MEMORY.get(model, 0) > self.card[0] / 2 ** 30:
            log(_("{model} needs about {need} GB of graphics memory and this graphics card has {memory} GB: part of the model runs on "
                  "the processor and it translates much more slowly.").format(
                model=model, need=decimal(MEMORY[model], 0 if MEMORY[model] >= 10 else 1), memory=round(self.card[0] / 2 ** 30)))
        self.s.update(source_language=self.labels[self.source.get()], target_language=self.labels[self.target.get()],
                      obs_source=self.obs_source.get().strip(), model=model)
        save_settings(self.file, self.s)
        if self.loop:
            self.restart = True
            self.stop()

    def toggle(self):
        if self.loop:
            self.stop()
        else:
            self.changed()
            if not self.s["obs_source"]:
                log(_("Choose the game source in OBS first."))
                return
            self.start()

    def start(self):
        self.started = self.running = True
        self.show_state()
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        self.loop = asyncio.new_event_loop()
        self.translator = Translator(dict(self.s), self.file.parent)
        self.translator.sample = self.sample
        self.task = self.loop.create_task(self.translator.serve())
        try:
            self.loop.run_until_complete(self.task)
        except asyncio.CancelledError:
            pass
        except Problem as e:
            log(str(e))
        except OSError as e:
            log(_("Could not start: {error}").format(error=e))
        finally:
            rest = asyncio.all_tasks(self.loop)
            for task in rest:
                task.cancel()
            if rest:
                self.loop.run_until_complete(asyncio.wait(rest))
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
            self.loop = None
            if self.translator.s["model"] != self.s["model"]:
                unload_model(self.s["ollama_url"], self.translator.s["model"])
            self.messages.put(self.stopped)

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.task.cancel)

    def stopped(self):
        self.running = False
        self.show_state()
        if self.restart:
            self.restart = False
            self.start()

    def pump(self):
        while not self.messages.empty():
            message = self.messages.get()
            if callable(message):
                message()
                continue
            self.text.configure(state="normal")
            self.text.insert("end", f"{time.strftime('%H:%M:%S')}  {message}\n")
            self.text.delete("1.0", "end-400l")
            self.text.see("end")
            self.text.configure(state="disabled")
        self.root.after(100, self.pump)

    def close(self):
        if self.translator:
            self.translator.closed = True
        self.stop()
        self.root.destroy()
        if self.started:
            unload_model(self.s["ollama_url"], self.s["model"])


class AreaPicker:
    def __init__(self, window, picture):
        self.window = window
        self.top = top = tk.Toplevel(window.root)
        top.title(_("Areas to read"))
        top.transient(window.root)
        self.picture = cv2.imdecode(np.frombuffer(base64.b64decode(picture), np.uint8), cv2.IMREAD_COLOR)
        self.ratio = self.picture.shape[1] / self.picture.shape[0]
        self.boxes = [region["box"] for region in window.s["regions"]]
        self.displays = [fit(region["box"], region["display"]) if region["display"] else None for region in window.s["regions"]]
        self.current = self.pending = None
        self.view = (0, 0, 1, 1)
        width = min(top.winfo_screenwidth() * 0.5, top.winfo_screenheight() * 0.6 * self.ratio)
        hint = ttk.Label(top, padding=8, wraplength=round(width), text=_(
            "Drag a rectangle around each part you want translated (yellow). With no rectangle the whole picture is read. "
            "To show the translation of an area somewhere else, choose the area below and drag the place where it should be shown "
            "(blue). The place keeps the proportions of its area. Apply shows the changes in OBS at once and keeps this window open."))
        hint.pack(fill="x")
        hint.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(e.width - 16, 200)))
        buttons = ttk.Frame(top, padding=8)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text=_("Remove last"), command=self.remove_last).pack(side="left")
        ttk.Button(buttons, text=_("Remove all"), command=self.remove_all).pack(side="left", padx=8)
        ttk.Button(buttons, text=_("Apply"), command=self.apply).pack(side="right")
        ttk.Button(buttons, text=_("Cancel"), command=self.close).pack(side="right", padx=8)
        ttk.Button(buttons, text="OK", style="Accent.TButton", command=self.ok).pack(side="right")
        mode = ttk.Frame(top, padding=(8, 8, 8, 0))
        mode.pack(side="bottom", fill="x")
        self.mode = tk.StringVar(value="read")
        ttk.Radiobutton(mode, text=_("Draw areas to read"), variable=self.mode, value="read").pack(side="left")
        ttk.Radiobutton(mode, text=_("Draw where area"), variable=self.mode, value="show").pack(side="left", padx=(16, 4))
        self.which = ttk.Combobox(mode, state="readonly", width=4)
        self.which.pack(side="left")
        ttk.Label(mode, text=_("is shown")).pack(side="left", padx=(4, 12))
        ttk.Button(mode, text=_("Show it where it is read"), command=self.same_place).pack(side="left")
        self.canvas = tk.Canvas(top, width=round(width), height=round(width / self.ratio), highlightthickness=0, cursor="crosshair",
                                bg=COLORS[THEME]["bg"])
        self.canvas.pack(fill="both", expand=True, padx=8)
        self.canvas.bind("<Configure>", self.resize)
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        top.protocol("WM_DELETE_WINDOW", self.close)
        themed(top)
        top.minsize(mode.winfo_reqwidth() + 16, top.winfo_reqheight() - self.canvas.winfo_reqheight() + 240)
        self.previous = window.sample
        window.show_sample("areas")
        top.grab_set()

    # The picture is redrawn after the window stops changing size, at the size that fits and with the proportions of the source.
    def resize(self, event):
        if self.pending:
            self.top.after_cancel(self.pending)
        self.pending = self.top.after(50, self.render)

    def render(self):
        self.pending = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        w = max(min(width, height * self.ratio), 16)
        h = w / self.ratio
        self.view = ((width - w) / 2, (height - h) / 2, w, h)
        small = cv2.resize(self.picture, (round(w), round(h)),
                           interpolation=cv2.INTER_AREA if w < self.picture.shape[1] else cv2.INTER_LINEAR)
        self.image = tk.PhotoImage(data=base64.b64encode(cv2.imencode(".png", small, [cv2.IMWRITE_PNG_COMPRESSION, 1])[1]).decode())
        self.canvas.delete("picture")
        self.canvas.create_image(self.view[0], self.view[1], image=self.image, anchor="nw", tags="picture")
        self.canvas.tag_lower("picture")
        self.draw()

    def on_canvas(self, box):
        x, y, w, h = self.view
        return [x + box[0] * w, y + box[1] * h, x + box[2] * w, y + box[3] * h]

    def point(self, e):
        x, y, w, h = self.view
        return min(max((e.x - x) / w, 0), 1), min(max((e.y - y) / h, 0), 1)

    def selected(self):
        return self.boxes[int(self.which.get()) - 1] if self.which.get() else None

    def rectangle(self, box, number, color, dash=None):
        x0, y0, x1, y1 = self.on_canvas(box)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=3, dash=dash, tags="box")
        self.canvas.create_text(x0 + 7, y0 + 4, text=str(number), anchor="nw", fill=color, font=("Segoe UI", 12, "bold"), tags="box")

    def draw(self):
        self.canvas.delete("box")
        numbers = [str(n) for n in range(1, len(self.boxes) + 1)]
        self.which.configure(values=numbers)
        if self.which.get() not in numbers:
            self.which.set(numbers[-1] if numbers else "")
        reading = self.current if self.mode.get() == "read" else None
        for number, box in enumerate(self.boxes + ([reading] if reading else []), 1):
            self.rectangle(box, number, "#ffcc00")
        for number, (box, shown) in enumerate(zip(self.boxes, self.displays), 1):
            if self.current and self.mode.get() == "show" and str(number) == self.which.get():
                shown = self.current
            if shown:
                a, b = self.on_canvas(box), self.on_canvas(shown)
                self.canvas.create_line((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2,
                                        fill="#33ccff", width=2, arrow="last", tags="box")
                self.rectangle(shown, number, "#33ccff", (6, 4))

    def press(self, e):
        self.start = self.point(e)
        self.current = None

    def drag(self, e):
        (x0, y0), (x, y) = self.start, self.point(e)
        area = self.selected() if self.mode.get() == "show" else None
        if area:
            # The place keeps the proportions of its area, so the translation is never squeezed or stretched.
            w, h = area[2] - area[0], area[3] - area[1]
            s = min(max(abs(x - x0) / w, abs(y - y0) / h), (1 - x0 if x >= x0 else x0) / w, (1 - y0 if y >= y0 else y0) / h)
            x, y = x0 + (s * w if x >= x0 else -s * w), y0 + (s * h if y >= y0 else -s * h)
        self.current = [min(x0, x), min(y0, y), max(x0, x), max(y0, y)]
        self.draw()

    def release(self, e):
        box, self.current = self.current, None
        if box and self.mode.get() == "read" and box[2] - box[0] >= 0.05 and box[3] - box[1] >= 0.03:
            self.boxes.append(box)
            self.displays.append(None)
        elif box and self.mode.get() == "show" and self.selected() and box[2] - box[0] >= 0.01 and box[3] - box[1] >= 0.01:
            self.displays[int(self.which.get()) - 1] = box
        self.draw()

    def same_place(self):
        if self.which.get():
            self.displays[int(self.which.get()) - 1] = None
            self.draw()

    def remove_last(self):
        del self.boxes[-1:]
        del self.displays[-1:]
        self.draw()

    def remove_all(self):
        self.boxes, self.displays = [], []
        self.draw()

    def apply(self):
        before = {tuple(region["box"]): region for region in self.window.s["regions"]}
        regions = []
        for box, shown in zip(self.boxes, self.displays):
            box = [round(v, 3) for v in box]
            old = before.get(tuple(box), {})
            regions.append({"box": box, "style": old.get("style"), "display": [round(v, 3) for v in shown] if shown else None,
                            "overlay": old.get("overlay", 0)})
        self.window.set_regions(regions)
        self.window.show_sample("areas")

    def ok(self):
        self.apply()
        self.close()

    def close(self):
        self.window.show_sample(self.previous if self.window.editor else None)
        self.top.destroy()


class StyleEditor:
    def __init__(self, window):
        self.window = window
        window.editor = self
        self.loading = False
        self.top = top = tk.Toplevel(window.root)
        top.title(_("Look of translations"))
        top.transient(window.root)
        f = ttk.Frame(top, padding=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(11, weight=1)
        count = len(window.s["regions"])
        ttk.Label(f, text=_("Settings for")).grid(row=0, column=0, sticky="w", pady=4)
        self.target = ttk.Combobox(f, state="readonly", values=[_("All areas (default look)") if count else _("Whole picture")]
                                   + [_("Area {n}").format(n=n) for n in range(1, count + 1)])
        self.target.current(0)
        self.target.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.target.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.default = tk.BooleanVar()
        self.default_box = ttk.Checkbutton(f, text=_("Use the default look for this area"), variable=self.default, command=self.switch)
        self.default_box.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(f, text=_("Font")).grid(row=2, column=0, sticky="w", pady=4)
        self.font = ttk.Combobox(f, height=20, values=sorted({name for name in tkfont.families(top) if not name.startswith("@")}))
        self.font.grid(row=2, column=1, sticky="ew", padx=(8, 0))
        for event in ("<<ComboboxSelected>>", "<Return>", "<FocusOut>"):
            self.font.bind(event, lambda e: self.apply())

        ttk.Label(f, text=_("Size")).grid(row=3, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=3, column=1, sticky="w", padx=(8, 0))
        self.fixed = tk.BooleanVar()
        self.auto_size = ttk.Radiobutton(row, text=_("Size of the original text"), variable=self.fixed, value=False, command=self.apply)
        self.auto_size.pack(side="left")
        self.fixed_size = ttk.Radiobutton(row, text=_("Fixed:"), variable=self.fixed, value=True, command=self.apply)
        self.fixed_size.pack(side="left", padx=(12, 4))
        self.size = ttk.Spinbox(row, from_=8, to=150, width=5, command=self.apply)
        self.size.bind("<KeyRelease>", lambda e: self.apply())
        self.size.pack(side="left")
        ttk.Label(row, text=_("px (in a 1080p picture)")).pack(side="left", padx=(4, 0))

        ttk.Label(f, text=_("Style")).grid(row=4, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=4, column=1, sticky="w", padx=(8, 0))
        self.bold, self.italic = tk.BooleanVar(), tk.BooleanVar()
        self.bold_box = ttk.Checkbutton(row, text=_("Bold"), variable=self.bold, command=self.apply)
        self.bold_box.pack(side="left")
        self.italic_box = ttk.Checkbutton(row, text=_("Italic"), variable=self.italic, command=self.apply)
        self.italic_box.pack(side="left", padx=(12, 0))

        ttk.Label(f, text=_("Text colour")).grid(row=5, column=0, sticky="w", pady=4)
        self.color = ttk.Button(f, width=10, compound="left", command=lambda: self.pick("color"))
        self.color.grid(row=5, column=1, sticky="w", padx=(8, 0))

        ttk.Label(f, text=_("Background")).grid(row=6, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=6, column=1, sticky="w", padx=(8, 0))
        self.background = ttk.Button(row, width=10, compound="left", command=lambda: self.pick("background"))
        self.background.pack(side="left")
        ttk.Label(row, text=_("opacity")).pack(side="left", padx=(12, 4))
        self.opacity = ttk.Scale(row, from_=0, to=100, length=180, command=lambda v: self.apply())
        self.opacity.pack(side="left")
        self.percent = ttk.Label(row, width=6)
        self.percent.pack(side="left", padx=(6, 0))

        ttk.Label(f, text=_("Background box")).grid(row=7, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=7, column=1, sticky="w", padx=(8, 0))
        self.padding = ttk.Scale(row, from_=0, to=40, length=180, command=lambda v: self.apply())
        self.padding.pack(side="left")
        self.margin = ttk.Label(row, width=8)
        self.margin.pack(side="left", padx=(6, 0))

        ttk.Label(f, text=_("Shadow around letters")).grid(row=8, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=8, column=1, sticky="w", padx=(8, 0))
        self.shadow = ttk.Scale(row, from_=0, to=20, length=150, command=lambda v: self.apply())
        self.shadow.pack(side="left")
        self.blur = ttk.Label(row, width=6)
        self.blur.pack(side="left", padx=(6, 0))
        ttk.Label(row, text=_("intensity")).pack(side="left", padx=(12, 4))
        self.strength = ttk.Scale(row, from_=0, to=100, length=150, command=lambda v: self.apply())
        self.strength.pack(side="left")
        self.darkness = ttk.Label(row, width=6)
        self.darkness.pack(side="left", padx=(6, 0))

        ttk.Label(f, text=_("Outline")).grid(row=9, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=9, column=1, sticky="w", padx=(8, 0))
        self.outline = ttk.Spinbox(row, from_=0, to=8, width=4, command=self.apply)
        self.outline.bind("<KeyRelease>", lambda e: self.apply())
        self.outline.pack(side="left")
        ttk.Label(row, text=_("px, colour")).pack(side="left", padx=(4, 6))
        self.outline_color = ttk.Button(row, width=10, compound="left", command=lambda: self.pick("outline_color"))
        self.outline_color.pack(side="left")

        ttk.Label(f, text=_("Alignment")).grid(row=10, column=0, sticky="w", pady=4)
        self.align = ttk.Combobox(f, state="readonly", width=14, values=[_(name) for name in ALIGN.values()])
        self.align.bind("<<ComboboxSelected>>", lambda e: self.apply())
        self.align.grid(row=10, column=1, sticky="w", padx=(8, 0))

        self.stage = tk.Frame(f, bg=STAGE, height=110, width=560)
        self.stage.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=(12, 4))
        self.stage.pack_propagate(False)
        self.sample = tk.Label(self.stage, text=_(SAMPLE), padx=10, pady=2)
        self.sample.pack(expand=True)
        ttk.Label(f, text=_("While translating, OBS shows a sample translation with this look as long as this window is open.\n"
                            "Opacity, outline and shadow are shown exactly only in OBS."),
                  foreground=COLORS[THEME]["muted"]).grid(
            row=12, column=0, columnspan=2, sticky="w")
        place = ttk.Frame(top, padding=(16, 0, 16, 10))
        place.pack(fill="x")
        ttk.Label(place, text=_("Shown in OBS source")).pack(side="left")
        self.overlay = ttk.Combobox(place, state="readonly", width=28)
        self.overlay.bind("<<ComboboxSelected>>", lambda e: self.choose_overlay())
        self.overlay.pack(side="left", padx=8)
        self.new_button = ttk.Button(place, text=_("New source..."), command=self.new_overlay)
        self.new_button.pack(side="left")
        self.remove_button = ttk.Button(place, text=_("Remove source"), command=self.remove_overlay)
        self.remove_button.pack(side="left", padx=(8, 0))
        buttons = ttk.Frame(top, padding=(16, 0, 16, 16))
        buttons.pack(fill="x")
        ttk.Button(buttons, text=_("Original look"), command=self.reset).pack(side="left")
        ttk.Button(buttons, text=_("Close"), command=self.close).pack(side="right")
        self.controls = [self.font, self.auto_size, self.fixed_size, self.size, self.bold_box, self.italic_box, self.color,
                         self.background, self.opacity, self.padding, self.shadow, self.strength, self.outline, self.outline_color, self.align]
        top.protocol("WM_DELETE_WINDOW", self.close)
        self.load()
        themed(top)
        top.minsize(top.winfo_reqwidth(), top.winfo_reqheight())

    def area(self):
        return self.target.current() - 1

    def own(self):
        return self.area() < 0 or self.window.s["regions"][self.area()]["style"] is not None

    def style(self):
        return self.window.s["regions"][self.area()]["style"] if self.area() >= 0 and self.own() else self.window.s["style"]

    def load(self):
        self.loading = True
        st = self.style()
        if self.area() < 0:
            self.default_box.state(["disabled"])
            self.default.set(False)
        else:
            self.default_box.state(["!disabled"])
            self.default.set(not self.own())
        self.font.set(st["font"])
        self.fixed.set(st["size"] > 0)
        self.size.set(st["size"] or 36)
        self.bold.set(st["bold"])
        self.italic.set(st["italic"])
        self.opacity.set(st["opacity"] * 100)
        self.padding.set(st["padding"])
        self.shadow.set(st["shadow"])
        self.strength.set(st["shadow_strength"] * 100)
        self.outline.set(st["outline"])
        self.align.set(_(ALIGN[st["align"]]))
        for widget in self.controls:
            widget.state(["!disabled" if self.own() else "disabled"])
        names = [overlay["name"] for overlay in self.window.s["overlays"]]
        self.overlay.configure(values=names)
        if self.area() >= 0:
            self.overlay.current(self.window.s["regions"][self.area()]["overlay"])
        else:
            self.overlay.set(names[0] if not self.window.s["regions"] else _("chosen for each area"))
        for widget in (self.overlay, self.new_button):
            widget.state(["!disabled" if self.area() >= 0 else "disabled"])
        self.remove_button.state(["!disabled" if self.area() >= 0 and self.overlay.current() > 0 else "disabled"])
        self.loading = False
        self.show()

    def choose_overlay(self):
        self.window.s["regions"][self.area()]["overlay"] = self.overlay.current()
        save_settings(self.window.file, self.window.s)
        self.load()

    def new_overlay(self):
        names = [overlay["name"] for overlay in self.window.s["overlays"]]
        name = (ask_text(self.top, _("New OBS source"), _("Name of the new browser source for translations:"),
                         f"Translation overlay {len(names) + 1}") or "").strip()
        if not name:
            return
        if name in names:
            messagebox.showinfo("OBS Screen Translator", _("A source with this name is already in the list."), parent=self.top)
            return
        self.window.s["overlays"].append({"name": name})
        self.window.s["regions"][self.area()]["overlay"] = len(self.window.s["overlays"]) - 1
        self.window.show_look()
        self.load()
        self.window.changed()

    def remove_overlay(self):
        n = self.overlay.current()
        overlays = self.window.s["overlays"]
        if n <= 0 or not messagebox.askyesno("OBS Screen Translator", _('Remove the source "{name}" from OBS? Its areas go back to "{first}".').format(
                name=overlays[n]["name"], first=overlays[0]["name"]), parent=self.top):
            return
        name = overlays.pop(n)["name"]
        for region in self.window.s["regions"]:
            region["overlay"] = 0 if region["overlay"] == n else region["overlay"] - (region["overlay"] > n)
        threading.Thread(target=remove_source, args=(name,), daemon=True).start()
        self.window.show_look()
        self.load()
        self.window.changed()

    def apply(self):
        if self.loading or not self.own():
            return
        st = self.style()
        st.update(font=self.font.get().strip() or st["font"], size=number(self.size.get(), 8, 150, 36) if self.fixed.get() else 0,
                  bold=self.bold.get(), italic=self.italic.get(), opacity=round(float(self.opacity.get())) / 100,
                  padding=round(float(self.padding.get())), shadow=round(float(self.shadow.get())),
                  shadow_strength=round(float(self.strength.get())) / 100,
                  outline=number(self.outline.get(), 0, 8, 0), align=list(ALIGN)[max(self.align.current(), 0)])
        save_settings(self.window.file, self.window.s)
        self.show()

    def pick(self, name):
        chosen = colorchooser.askcolor(self.style()[name], parent=self.top, title=_("Choose a colour"))[1]
        if chosen:
            self.style()[name] = chosen
            save_settings(self.window.file, self.window.s)
            self.show()

    def switch(self):
        region = self.window.s["regions"][self.area()]
        region["style"] = None if self.default.get() else dict(self.window.s["style"])
        save_settings(self.window.file, self.window.s)
        self.load()

    def reset(self):
        if self.own():
            self.style().update(STYLE)
            save_settings(self.window.file, self.window.s)
            self.load()

    def show(self):
        st = self.style()
        for button, name in ((self.color, "color"), (self.background, "background"), (self.outline_color, "outline_color")):
            button.image = tk.PhotoImage(width=16, height=16)
            button.image.put(COLORS[THEME]["line"], to=(0, 0, 16, 16))
            button.image.put(st[name], to=(1, 1, 15, 15))
            button.configure(image=button.image, text=f" {st[name]}")
        self.percent.configure(text=f"{round(st['opacity'] * 100)} %")
        self.margin.configure(text=f"{st['padding']} px")
        self.blur.configure(text=f"{st['shadow']} px")
        self.darkness.configure(text=f"{round(st['shadow_strength'] * 100)} %")
        # Like in OBS, a small box comes in gradually: it reaches its full opacity at 4.
        opacity, stage = st["opacity"] * min(1, st["padding"] / 4), (0x3d, 0x46, 0x50)
        mixed = "#%02x%02x%02x" % tuple(round(int(st["background"][1 + 2 * i:3 + 2 * i], 16) * opacity + stage[i] * (1 - opacity))
                                        for i in range(3))
        self.sample.configure(font=tkfont.Font(family=st["font"], size=-(st["size"] or 36), weight="bold" if st["bold"] else "normal",
                                               slant="italic" if st["italic"] else "roman"), fg=st["color"], bg=mixed,
                              padx=st["padding"], pady=round(st["padding"] / 4))
        self.window.show_look()
        self.window.show_sample(self.area())

    def close(self):
        self.window.show_sample(None)
        self.window.editor = None
        self.top.destroy()


def number(text, low, high, fallback):
    try:
        return min(max(int(float(text)), low), high)
    except ValueError:
        return fallback


class Page:
    def __init__(self, root, title, text):
        top = tk.Toplevel(root)
        top.title(title)
        top.transient(root)
        ttk.Button(top, text=_("Close"), command=top.destroy).pack(side="bottom", anchor="e", padx=16, pady=16)
        frame = ttk.Frame(top, padding=(16, 16, 16, 0))
        frame.pack(fill="both", expand=True)
        colors = COLORS[THEME]
        view = tk.Text(frame, width=92, height=32, wrap="word", padx=14, pady=10, relief="flat", font="SunValleyBodyFont",
                       spacing1=2, spacing3=2, bg=colors["field"], fg=colors["fg"], highlightthickness=1,
                       highlightbackground=colors["line"], highlightcolor=colors["line"], borderwidth=0)
        bar = ttk.Scrollbar(frame, command=view.yview)
        view.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        view.pack(fill="both", expand=True)
        view.tag_configure("heading", font="SunValleySubtitleFont", spacing1=6, spacing3=4)
        view.tag_configure("item", lmargin2=tkfont.Font(root=root, name="SunValleyBodyFont", exists=True).measure("1.  "))
        view.tag_configure("strong", font="SunValleyBodyStrongFont")
        for line in text.split("\n"):
            if line.startswith("# "):
                view.insert("end", line[2:] + "\n", "heading")
                continue
            tags = ("item",) if line.startswith("- ") or re.match(r"\d+\. ", line) else ()
            for n, part in enumerate(re.sub(r"^- ", "•  ", line).split("**")):
                view.insert("end", part, tags + (("strong",) if n % 2 else ()))
            view.insert("end", "\n", tags)
        view.configure(state="disabled")
        themed(top)
        top.minsize(480, 320)


class KeyPicker:
    def __init__(self, window):
        self.window = window
        self.top = top = tk.Toplevel(window.root)
        top.title(_("Show/hide key"))
        top.transient(window.root)
        ttk.Label(top, padding=12, text=_("Press the key that should show and hide the translations: a function key (F1 to F24)\n"
                                          "or a combination with Ctrl or Alt. It works while the game or OBS is in front.")).pack(fill="both", expand=True)
        buttons = ttk.Frame(top, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text=_("No key"), takefocus=False, command=lambda: self.use(None)).pack(side="left")
        ttk.Button(buttons, text=_("Cancel"), takefocus=False, command=top.destroy).pack(side="right")
        top.bind("<KeyPress>", self.press)
        themed(top)
        top.minsize(top.winfo_reqwidth(), top.winfo_reqheight())
        top.grab_set()
        top.focus_set()

    def press(self, e):
        modifiers = (1 if e.state & 0x20000 else 0) | (2 if e.state & 0x4 else 0) | (4 if e.state & 0x1 else 0)
        if e.keycode in (16, 17, 18, 91, 92) or not (112 <= e.keycode <= 135 or modifiers & 3) or (e.keycode, modifiers) == (115, 1):
            return
        names = [name for bit, name in ((2, "Ctrl"), (1, "Alt"), (4, "Shift")) if modifiers & bit]
        self.use({"key": e.keycode, "modifiers": modifiers,
                  "label": "+".join(names + [e.keysym.upper() if len(e.keysym) == 1 else e.keysym])})

    def use(self, hotkey):
        self.top.destroy()
        self.window.set_key(hotkey)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate the on-screen text of an OBS source and draw the translation over the original.")
    parser.add_argument("--settings", default=str(DATA / "settings.json"), help="settings file (created on the first start)")
    parser.add_argument("--preview", action="store_true", help="read one frame from OBS, print texts and translations, save preview.png")
    parser.add_argument("--image", help="like --preview, but read this image file instead of OBS")
    args = parser.parse_args()
    settings_file = pathlib.Path(args.settings).resolve()
    if args.preview or args.image:
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8")
        try:
            asyncio.run(Translator(load_settings(settings_file), settings_file.parent).preview(args.image, settings_file.parent))
        except Problem as e:
            sys.exit(str(e))
    else:
        if sys.platform == "win32":
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        Window(settings_file).root.mainloop()
        os._exit(0)
