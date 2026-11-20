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
import urllib.request
import webbrowser
from tkinter import colorchooser, font as tkfont, messagebox, ttk

import cv2
import numpy as np
import sv_ttk
import websockets
from rapidocr import RapidOCR

VERSION = "0.6.0"
PROJECT = "https://github.com/Sl0vakistan/obs-screen-translator"
FROZEN = getattr(sys, "frozen", False)
HERE = pathlib.Path(sys._MEIPASS) if FROZEN else pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get("APPDATA", HERE)) / "OBS Screen Translator" if FROZEN else HERE
LANGUAGES = json.loads((HERE / "languages.json").read_text(encoding="utf-8"))
STYLE = {"font": "Segoe UI Semibold", "size": 0, "bold": False, "italic": False, "color": "#ffffff", "background": "#000000",
         "opacity": 0.85, "outline": 0, "outline_color": "#000000", "align": "auto"}
ALIGN = {"auto": "Automatic", "left": "Left", "center": "Centre", "right": "Right"}
SAMPLE = "This is how the translations will look"
DEFAULTS = {
    "obs_source": "",
    "scenes": [],
    "overlays": [{"name": "Translation overlay"}],
    "create_overlay_source": True,
    "source_language": "en",
    "target_language": "sk",
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
- A graphics card with about 8 GB of free memory for the translation model, and about 10 GB of free disk space.

# First start
1. Start OBS once, then this program. The order does not matter: the program waits for OBS.
2. If the WebSocket server in OBS is off, the program asks to turn it on. Close OBS when it says so and start OBS again. The previous OBS setting is kept in a backup file.
3. If Ollama is missing, the program asks to download it from ollama.com (1.9 GB) and install it. Ollama runs the translation model. After its installation Ollama opens a window of its own with commands for a terminal: close it, the translator does not need them (see Ollama below).
4. On the first Start the translation model (8.1 GB) is downloaded, once. The window shows the progress and says "translation model ready" when it can translate.

# Setting up
- Languages: the language of the game and the language of your viewers. The target starts as the language of Windows.
- Game > Source in OBS: the source with the game. A single capture card in the scene that is on air is chosen by itself.
- Game > Areas to read: optional rectangles around the parts to translate, for example the subtitles. With none the whole picture is read. For each area you can also draw where its translation is shown, if not over the original text.
- On screen > Look: font, size, colours, background, outline and alignment. One look for all areas, or a look of its own for any area. While the editor is open, a sample translation is shown in OBS. Each area can also be shown in an OBS source of its own: New source... adds another browser source, which you can move, show and hide in OBS on its own.
- On screen > Show/hide key: one key that shows and hides all translation sources from any window, also from a Stream Deck.
- Start translating when this program opens: no need to press Start next time.

Then press Start. A browser source named Translation overlay appears in the scene that is on air. Keep it above the game.

# During the stream
- Hiding a translation source in OBS stops reading the areas shown in it. With all of them hidden, for example with the show/hide key, reading and translating pause.
- Changing a language or an area while translating restarts the translation by itself.
- Keep this window open. Closing it removes the translations from the picture and unloads the translation model from the graphics card.

# Ollama
Ollama is a free program that runs the translation model on this PC. The translator only sends it text; nothing leaves your computer.
- You do not have to start Ollama or type anything in a terminal. Start in this window starts Ollama in the background when it is not running and downloads the model when it is missing.
- After its installation Ollama opens its own window, Launch, saying "Copy a command and run it in your terminal", with commands such as ollama launch claude. Those start AI coding tools and have nothing to do with the translator. Close that window; Ollama keeps running in the background.
- Installing it by hand: run OllamaSetup.exe from ollama.com/download. It needs no account and no administrator rights.
- Is it running? Open http://127.0.0.1:11434 in a browser: it says "Ollama is running".
- Downloading the model before a stream: press Start once and wait for "translation model ready".
- Less than about 8 GB of free graphics memory: use the smaller model, which translates noticeably worse. Help > Open the settings folder, open settings.json in Notepad, change translategemma:12b to translategemma:4b (3.3 GB, about 2.7 GB of graphics memory) and start the program again.
- Little space on drive C: Ollama keeps the models in .ollama\\models in your user folder. To keep them elsewhere, open Ollama from the Start menu and set Model location in its Settings to a folder on another drive, best before the model is downloaded.
- Ollama on another PC: there, turn on Expose Ollama to the network in Ollama's Settings and allow Ollama through the Windows firewall. Here, set ollama_url in settings.json to http://<address of that PC>:11434. Translations then take about a third of a second longer.

# When something does not work
- "Waiting for OBS": OBS is not running, or its WebSocket server is off (Tools > WebSocket Server Settings in OBS).
- "Ollama did not start": open Ollama from the Start menu, wait for its icon next to the clock and press Start again.
- The download of the model stopped: check the internet connection and the free disk space, then press Start again. The download continues where it stopped.
- Translations take several seconds: the model does not fit into the graphics memory, for example next to a demanding game. Use translategemma:4b (see Ollama).
- No translations on screen: the translation source (Translation overlay, or one you added) is hidden, is not in the scene that is on air, or sits inside a nested scene.
- Moving text stays untranslated until it stands still for a moment. This is on purpose: it skips signs and number plates.
- The first translation after a break is late: the model is being loaded, which takes about 12 seconds.
- Cyrillic, Arabic, Korean and other scripts are not read yet. Latin script and Chinese are.
"""
reader = None
THEME = "light"
COLORS = {"dark": {"bg": "#1c1c1c", "fg": "#fafafa", "field": "#232323", "line": "#3a3a3a", "muted": "#a0a0a0"},
          "light": {"bg": "#fafafa", "fg": "#1c1c1c", "field": "#ffffff", "line": "#e0e0e0", "muted": "#5f5f5f"}}


class Problem(Exception):
    pass


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


def themed(window):
    window.configure(bg=COLORS[THEME]["bg"])
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
    top.resizable(False, False)
    top.transient(parent)
    result = {}
    frame = ttk.Frame(top, padding=16)
    frame.pack(fill="both")
    ttk.Label(frame, text=prompt).pack(anchor="w")
    entry = ttk.Entry(frame, width=42)
    entry.insert(0, initial)
    entry.pack(fill="x", pady=(8, 14))
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x")

    def done(value):
        result["value"] = value
        top.destroy()
    ttk.Button(buttons, text="Cancel", command=lambda: done(None)).pack(side="right")
    ttk.Button(buttons, text="OK", style="Accent.TButton", command=lambda: done(entry.get())).pack(side="right", padx=(0, 8))
    entry.bind("<Return>", lambda e: done(entry.get()))
    entry.focus_set()
    entry.select_range(0, "end")
    themed(top)
    top.grab_set()
    parent.wait_window(top)
    return result.get("value")


def changes():
    text = (HERE / "CHANGELOG.md").read_text(encoding="utf-8")
    section = re.search(rf"^## {re.escape(VERSION)} .*?$(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
    lines = []
    for line in section.strip().splitlines():
        if lines and lines[-1] and line and not line.startswith("- "):
            lines[-1] += " " + line.strip()
        else:
            lines.append(line)
    body = "**".join(part.replace("*", "").replace("`", "") for part in "\n".join(lines).split("**"))
    return f"# What's new in {VERSION}\n{body}\n\nThe changes of every version: {PROJECT}/blob/main/CHANGELOG.md"


def system_language():
    if sys.platform == "win32":
        kernel = ctypes.windll.kernel32
        for number in (kernel.GetUserDefaultLCID(), kernel.GetUserDefaultUILanguage()):
            code = (locale.windows_locale.get(number) or "").split("_")[0]
            if code in LANGUAGES and code != DEFAULTS["source_language"]:
                return code
    return DEFAULTS["target_language"]


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
                log("text reader ready (graphics card)")
                return reader
            except Exception as e:
                log(f"reading text on the graphics card failed ({e}); using the processor")
        reader = RapidOCR(params=base)
        reader(warmup)
        log("text reader ready (processor)")
    return reader


def obs_websocket_file():
    files = [pathlib.Path(base).expanduser() / "obs-studio/plugin_config/obs-websocket/config.json"
             for base in (os.environ.get("APPDATA"), "~/.config", "~/Library/Application Support") if base]
    return next((f for f in files if f.exists()), files[0])


def obs_websocket_config():
    file = obs_websocket_file()
    if not file.exists():
        raise Problem("OBS WebSocket settings not found. Start OBS once and enable Tools > WebSocket Server Settings > Enable WebSocket server.")
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
        if not ask("Ollama, the program that runs the translation model, is not installed.\n\n"
                   f"Download it from ollama.com ({total / 1e9:.1f} GB) and install it now?"):
            raise Problem("Ollama is not installed. Get it from https://ollama.com/download, install it and press Start again.")
        setup = pathlib.Path(tempfile.gettempdir()) / "OllamaSetup.exe"
        log("downloading Ollama...")
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
        raise Problem("The downloaded Ollama installer is not signed by Ollama, so it was not started. "
                      "Install Ollama yourself from https://ollama.com/download and press Start again.")
    log("installing Ollama...")
    failed = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]).returncode
    setup.unlink()
    if failed:
        raise Problem("Installing Ollama failed. Install it yourself from https://ollama.com/download and press Start again.")
    log("Ollama is installed. It may open a window of its own with commands for a terminal: close it, the translator does not need them.")


async def obs_picture(source):
    obs = await OBS().connect()
    data = (await obs.request("GetSourceScreenshot", sourceName=source, imageFormat="png", imageWidth=960))["imageData"]
    await obs.ws.close()
    return data.split(",", 1)[1]


def same_text(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85


def same_place(a, b):
    return abs(a[0] + a[2] - b[0] - b[2]) < 0.012 and abs(a[1] - b[1]) < 0.006


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

    def ollama(self, path, body=None, timeout=60):
        request = urllib.request.Request(self.s["ollama_url"] + path, data=body and json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(request, timeout=timeout)

    def prepare_model(self):
        log("preparing the translation model, this can take a while...")
        try:
            self.ollama("/api/version").close()
        except OSError:
            program = shutil.which("ollama") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            if not os.path.exists(program):
                install_ollama()
                program = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            log("starting Ollama...")
            subprocess.Popen([program, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for _ in range(30):
                time.sleep(1)
                try:
                    self.ollama("/api/version").close()
                    break
                except OSError:
                    pass
            else:
                raise Problem("Ollama did not start. Start it yourself and press Start again.")
        with self.ollama("/api/tags") as response:
            installed = [m["name"] for m in json.loads(response.read())["models"]]
        if self.s["model"] not in installed:
            log(f"downloading the translation model {self.s['model']} (several gigabytes, once)...")
            shown = -10
            with self.ollama("/api/pull", {"model": self.s["model"]}, timeout=None) as response:
                for line in response:
                    step = json.loads(line)
                    if step.get("error"):
                        raise Problem(f"The model could not be downloaded: {step['error']}")
                    percent = 100 * step.get("completed", 0) // step["total"] if step.get("total") else None
                    if percent is not None and percent >= shown + 10:
                        shown = percent
                        log(f"  {percent} %")
        hello = self.translate(["Hello there."])[0]
        log(f"translation model ready: {self.s['model']} | {hello} | {len(self.cache)} cached translations"
            f" | {'direct connection to the model' if self.direct else 'through Ollama'}")

    # visible: the translation sources shown in OBS; areas whose source is hidden are not read.
    def read(self, frame, visible=None):
        h, w = frame.shape[:2]
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
        lines = []
        for box, text, score in zip(r.boxes, r.txts, r.scores) if r.txts else ():
            middle = (box[:, 1].min() + box[:, 1].max()) / 2
            start, _, left, top, region = min(strips, key=lambda s: max(s[0] - middle, middle - s[1], 0))
            x0, y0 = float((box[:, 0].min() + left) / w), float((box[:, 1].min() - start + top) / h)
            x1, y1 = float((box[:, 0].max() + left) / w), float((box[:, 1].max() - start + top) / h)
            if score >= self.s["min_score"] and (y1 - y0) * 1080 >= self.s["min_height"] and re.search(r"[^\W\d_]{3}", text):
                lines.append((y0, x0, x1, y1, " ".join(text.split()), region))
        blocks = []
        for y0, x0, x1, y1, text, region in sorted(lines, key=lambda line: line[:5]):
            lh = y1 - y0
            lw = lh * h / w
            for b in blocks:
                px0, py0, px1, py1 = b["last"]
                if (py0 + 0.5 * (py1 - py0) < y0 < py1 + 0.6 * lh and 0.7 < lh / (py1 - py0) < 1.4
                        and (abs(x0 - px0) < 1.5 * lw or abs(x0 + x1 - px0 - px1) < 3 * lw)):
                    b["lines"].append(text)
                    b["centered"] += abs(x0 + x1 - px0 - px1) < 2 * abs(x0 - px0)
                    b["box"] = [min(b["box"][0], x0), b["box"][1], max(b["box"][2], x1), y1]
                    b["last"] = (x0, y0, x1, y1)
                    break
            else:
                blocks.append({"lines": [text], "box": [x0, y0, x1, y1], "last": (x0, y0, x1, y1), "centered": 0, "region": region})
        return [types.SimpleNamespace(text=" ".join(b["lines"]), box=b["box"], rows=len(b["lines"]), region=b["region"],
                                      line_height=(b["box"][3] - b["box"][1]) / len(b["lines"]),
                                      centered=b["centered"] > 0 if len(b["lines"]) > 1 else abs(b["box"][0] + b["box"][2] - 1) < 0.04)
                for b in blocks]

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
            raise Problem("the program is closing")
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

    # An area can show its translations elsewhere: the boxes are moved and scaled from where they are read to where they are shown.
    def place(self, n, box, line_height):
        region = self.region(n)
        if not region or not region["display"]:
            return box, line_height
        (a0, b0, a1, b1), (c0, d0, c1, d1) = region["box"], region["display"]
        sx, sy = (c1 - c0) / (a1 - a0), (d1 - d0) / (b1 - b0)
        return [c0 + (box[0] - a0) * sx, d0 + (box[1] - b0) * sy, c0 + (box[2] - a0) * sx, d0 + (box[3] - b0) * sy], line_height * sy

    # While the look editor is open, a sample translation shows the chosen look in OBS.
    def sample_items(self):
        if self.sample is None:
            return []
        region = self.region(self.sample)
        box = (region["display"] or region["box"]) if region else [0.2, 0.8, 0.8, 0.86]
        middle, height = (box[1] + box[3]) / 2, min(0.034, box[3] - box[1])
        return [{"id": "sample", "text": SAMPLE, "box": [box[0] + 0.01, middle - height / 2, box[2] - 0.01, middle + height / 2],
                 "rows": 1, "line_height": height, "centered": True, "style": self.style(self.sample), "overlay": self.overlay(self.sample)}]

    def tidy(self, text, translation):
        translation = " ".join(translation.split())
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
            log(f"translation failed: {e}")
            return [None] * len(texts)

    async def frame(self, obs):
        d = (await obs.request("GetSourceScreenshot", sourceName=self.s["obs_source"], imageFormat="jpg", imageWidth=1920,
                               imageCompressionQuality=85))["imageData"]
        return cv2.imdecode(np.frombuffer(base64.b64decode(d.split(",", 1)[1]), np.uint8), cv2.IMREAD_COLOR)

    async def prepare_overlays(self, obs):
        video = await obs.request("GetVideoSettings")
        existing = {i["inputName"]: i["inputKind"] for i in (await obs.request("GetInputList"))["inputs"]}
        for n, overlay in enumerate(self.s["overlays"]):
            name = overlay["name"]
            if existing.get(name, "browser_source") != "browser_source":
                raise Problem(f'OBS already has a source named "{name}" that is not a browser source. In Look of translations, '
                              f'remove this translation source and add one with another name.')
            url = (HERE / "overlay.html").as_uri() + (f"?scale={video['baseWidth'] / 1920:g}&ws=ws://127.0.0.1:{self.s['port']}"
                                                      f"&overlay={n}&v={VERSION}")
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
            log(f'added the browser source "{name}" to: {", ".join(scenes)}')

    async def visible_overlays(self, obs):
        try:
            scene = (await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]
            shown = {i["sourceName"] for i in (await obs.request("GetSceneItemList", sceneName=scene))["sceneItems"] if i["sceneItemEnabled"]}
        except RuntimeError:
            return set()
        return {n for n, overlay in enumerate(self.s["overlays"]) if overlay["name"] in shown}

    async def run(self, publish):
        self.obs = obs = await OBS().connect()
        log("connected to OBS")
        if self.s["create_overlay_source"]:
            await self.prepare_overlays(obs)
        loop = asyncio.get_running_loop()
        tracks = []
        state = types.SimpleNamespace(job=None, n=0, error=None, dirty=False, active=None)

        def send():
            shown = [t for t in tracks if t.stable and t.translation]
            for t in shown:
                if not t.logged:
                    t.logged = True
                    log(f"{time.monotonic() - t.since:.2f} s  {t.text}\n          {t.translation}")
            items = []
            for t in shown:
                box, line_height = self.place(t.region, t.box, t.line_height)
                items.append({"id": t.id, "text": t.translation, "box": box, "rows": t.rows, "line_height": line_height,
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
                log("translating" if active else "paused (no translation source is shown in the current scene)")
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
                    log(f"screenshot failed: {e}")
                state.error, blocks = str(e), []
            now = time.monotonic()
            unmatched = []
            for b in blocks:
                t = next((t for t in tracks if t.seen != now and (
                    same_text(b.text, t.text) and same_place(b.box, t.box)
                    or not t.sentence and overlap(b.box, t.box) and (key(t.text) in key(b.text) or key(b.text) in key(t.text)))), None)
                if t:
                    t.seen, t.stable = now, True
                else:
                    unmatched.append(b)
            for b in unmatched:
                t = next((t for t in tracks if t.seen != now and same_text(b.text, t.text)), None)
                if t:
                    t.seen, t.stable, t.box = now, False, b.box
                else:
                    tracks[:] = [t for t in tracks if t.seen == now or not overlap(t.box, b.box)]
                    state.n += 1
                    words = re.findall(r"[^\W\d_]+", b.text)
                    tracks.append(types.SimpleNamespace(id=state.n, text=b.text, box=b.box, rows=b.rows, line_height=b.line_height,
                                                        centered=b.centered, region=b.region, seen=now, since=started, stable=False,
                                                        translation=self.cache.get(key(b.text)), logged=False,
                                                        sentence=sum(not x.isupper() for x in words) >= 2))
            tracks[:] = [t for t in tracks if now - t.seen <= self.s["linger"]]
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
                    log("OBS is not reachable, retrying in 3 s")
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
        global log, ask
        self.file = settings_file
        self.s = load_settings(settings_file)
        self.messages = queue.Queue()
        self.loop = self.task = self.translator = self.retry = self.said = self.websocket = self.listener = None
        self.editor = self.sample = None
        self.restart = self.looking = self.started = False
        log = self.messages.put
        ask = self.ask
        self.labels = {f"{name} ({code})": code for code, name in LANGUAGES.items()}
        names = sorted(self.labels)

        global THEME
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
        muted = COLORS[THEME]["muted"]
        page = ttk.Frame(root, padding=(22, 16, 22, 20))
        page.pack(fill="both", expand=True)
        head = ttk.Frame(page)
        head.pack(fill="x")
        ttk.Label(head, text="OBS Screen Translator", font="SunValleyTitleFont").pack(side="left")
        ttk.Label(head, text=VERSION, font="SunValleyCaptionFont", foreground=muted).pack(side="left", anchor="s", padx=10, pady=(0, 7))
        help_button = ttk.Menubutton(head, text="Help")
        help_button.pack(side="right")
        menu = tk.Menu(help_button, tearoff=False)
        menu.add_command(label="Installation and setup", command=lambda: Page(root, "Installation and setup", GUIDE))
        menu.add_command(label=f"What's new in {VERSION}", command=lambda: Page(root, f"What's new in {VERSION}", changes()))
        menu.add_command(label="Details", command=self.details)
        menu.add_separator()
        menu.add_command(label="Open the settings folder", command=lambda: os.startfile(self.file.parent))
        menu.add_command(label="Project page", command=lambda: webbrowser.open(PROJECT))
        help_button.configure(menu=menu)
        ttk.Label(page, text="Live translation of the text in an OBS source, drawn over the original.", foreground=muted).pack(anchor="w")

        def card(title):
            ttk.Label(page, text=title, font="SunValleyBodyStrongFont").pack(anchor="w", pady=(16, 6))
            frame = ttk.Frame(page, style="Card.TFrame", padding=(16, 10))
            frame.pack(fill="x")
            frame.columnconfigure(1, weight=1)
            return frame

        def line(frame, n, label, widget, button=None):
            ttk.Label(frame, text=label, width=17).grid(row=n, column=0, sticky="w", pady=5)
            widget.grid(row=n, column=1, columnspan=1 if button else 2, sticky="ew", padx=(8, 0))
            if button:
                button.grid(row=n, column=2, sticky="ew", padx=(12, 0))

        languages = card("Languages")
        self.source = ttk.Combobox(languages, values=names, state="readonly")
        line(languages, 0, "Translate from", self.source)
        self.target = ttk.Combobox(languages, values=names, state="readonly")
        line(languages, 1, "Translate to", self.target)
        game = card("Game")
        self.obs_source = ttk.Combobox(game)
        line(game, 0, "Source in OBS", self.obs_source, ttk.Button(game, text="Refresh", width=10, command=self.refresh))
        self.area = ttk.Label(game)
        line(game, 1, "Areas to read", self.area, ttk.Button(game, text="Choose...", width=10, command=self.choose_area))
        screen = card("On screen")
        self.look_label = ttk.Label(screen, wraplength=440)
        line(screen, 0, "Look", self.look_label, ttk.Button(screen, text="Edit...", width=10,
                                                            command=lambda: self.editor.top.lift() if self.editor else StyleEditor(self)))
        self.key = ttk.Label(screen)
        line(screen, 1, "Show/hide key", self.key, ttk.Button(screen, text="Set...", width=10, command=lambda: KeyPicker(self)))
        self.auto = tk.BooleanVar(value=self.s["start_automatically"])
        ttk.Checkbutton(screen, text="Start translating when this program opens", variable=self.auto, style="Switch.TCheckbutton",
                        command=self.remember).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 4))
        action = ttk.Frame(page)
        action.pack(fill="x", pady=(18, 0))
        self.button = ttk.Button(action, text="Start", width=14, style="Accent.TButton", command=self.toggle)
        self.button.pack(side="left")
        self.status = ttk.Label(action, text="Stopped", foreground=muted)
        self.status.pack(side="left", padx=14)
        ttk.Label(page, text="Activity", font="SunValleyBodyStrongFont").pack(anchor="w", pady=(16, 6))
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

        self.source.set(next(label for label, code in self.labels.items() if code == self.s["source_language"]))
        self.target.set(next(label for label, code in self.labels.items() if code == self.s["target_language"]))
        self.obs_source.set(self.s["obs_source"])
        self.show_area()
        self.show_look()
        for box in (self.source, self.target, self.obs_source):
            box.bind("<<ComboboxSelected>>", self.changed)
        root.protocol("WM_DELETE_WINDOW", self.close)
        themed(root)
        root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
        root.after(100, self.pump)
        self.listen_for_key()
        self.refresh()

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
            return "Waiting for OBS. Install OBS Studio from https://obsproject.com and start it."
        if file.exists() and json.loads(file.read_text(encoding="utf-8-sig")).get("server_enabled"):
            return "Waiting for OBS. Start it; if it is running, check Tools > WebSocket Server Settings > Enable WebSocket server."
        if self.websocket is None:
            self.websocket = ask("The WebSocket server in OBS is turned off. The translator needs it to get the picture of the game "
                                 "and to show the translations.\n\nTurn it on now? The current OBS setting is kept in a backup file.")
        if not self.websocket:
            return "The WebSocket server in OBS is off. Turn it on in OBS: Tools > WebSocket Server Settings > Enable WebSocket server."
        if obs_running():
            return "Close OBS now: its WebSocket server will be turned on as soon as OBS is closed."
        enable_obs_websocket()
        return "The WebSocket server in OBS is turned on. Start OBS."

    def found(self, names, suggestion):
        self.looking = False
        if self.said:
            log("OBS found.")
        self.said = None
        self.obs_source.configure(values=names)
        if not self.s["obs_source"] and suggestion:
            self.obs_source.set(suggestion)
            self.changed()
            log(f'Game source chosen automatically: "{suggestion}". Pick another one in the list if this is not the game.')
        if not self.s["obs_source"]:
            log("Choose the game source and press Start.")
        elif self.auto.get() and not self.started and not self.loop:
            self.toggle()

    def details(self):
        folder = pathlib.Path(sys.executable).parent if FROZEN else HERE
        Page(self.root, "Details", f"""# OBS Screen Translator {VERSION}
Live translation of on-screen text for streamers. The text in an OBS source is read, translated by a language model on this PC and drawn over the original. Nothing leaves your computer.

Free and open source under the MIT License. Project page: {PROJECT}

# Vibe-coded
The idea, the testing and every decision come from a streamer who is not a programmer. All of the code was written by an AI coding assistant (Claude, by Anthropic). Nobody has reviewed it line by line.

# How it works
1. Four times a second the program asks OBS for a picture of the game source.
2. RapidOCR finds and reads the text, on the graphics card through DirectML or on the processor.
3. TranslateGemma, run by Ollama, translates new text. Every translation is stored, so text seen before appears at once.
4. The browser source draws each translation where the original text is.

# On this PC
Settings: {short_path(self.file)}
Stored translations: cache_*.json in {short_path(self.file.parent)}
OBS WebSocket settings: {short_path(obs_websocket_file())}
Ollama: {self.s['ollama_url']}, model {self.s['model']}
Text is read on: {'the graphics card (the processor if that fails)' if self.s['ocr_on_gpu'] else 'the processor'}
Overlay connection: ws://127.0.0.1:{self.s['port']}

# Third-party software
The program bundles Python, RapidOCR with the PP-OCR models, ONNX Runtime with DirectML, OpenCV, NumPy, websockets and other packages, each under its own license. See {short_path(folder / 'THIRD_PARTY_NOTICES.md')} and the licenses folder next to the program.
""")

    def show_look(self):
        st = self.s["style"]
        own = sum(1 for region in self.s["regions"] if region["style"])
        sources = len(self.s["overlays"])
        size = f"{st['size']}\u00a0px" if st["size"] else "size of the original"
        text = f"{st['font']}, {size}, background {round(st['opacity'] * 100)}\u00a0%"
        more = [f"{own} area{'s' if own > 1 else ''} with a look of its own"] if own else []
        more += [f"{sources} OBS sources"] if sources > 1 else []
        self.look_label.configure(text=text + ("\n" + ", ".join(more) if more else ""))

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
        self.key.configure(text=self.s["hotkey"]["label"] if self.s["hotkey"] else "None")
        if self.s["hotkey"]:
            self.listener = threading.Thread(target=self.listen, args=(self.s["hotkey"],), daemon=True)
            self.listener.start()

    def listen(self, hotkey):
        user = ctypes.windll.user32
        if not user.RegisterHotKey(None, 1, hotkey["modifiers"] | 0x4000, hotkey["key"]):
            log(f'The key {hotkey["label"]} is taken by another program. Set another one.')
            return
        message = ctypes.wintypes.MSG()
        while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == 0x0312:
                try:
                    if asyncio.run(toggle_overlays([overlay["name"] for overlay in self.s["overlays"]])) is None:
                        log("There is nothing to show or hide yet. Press Start first.")
                except (Problem, OSError, websockets.WebSocketException):
                    log("The key was pressed, but OBS is not reachable.")
        user.UnregisterHotKey(None, 1)

    def show_area(self):
        count = len(self.s["regions"])
        moved = sum(1 for region in self.s["regions"] if region["display"])
        text = "Whole picture" if not count else "1 area" if count == 1 else f"{count} areas"
        self.area.configure(text=text + (f", {moved} shown elsewhere" if moved else ""))
        if self.editor:
            self.editor.close()

    def choose_area(self):
        source = self.obs_source.get().strip()
        if not source:
            log("Choose the game source in OBS first.")
            return

        def work():
            try:
                picture = asyncio.run(obs_picture(source))
                self.messages.put(lambda: AreaPicker(self, picture))
            except Problem as e:
                log(str(e))
            except (OSError, RuntimeError, websockets.WebSocketException) as e:
                log(f"Could not get a picture from OBS: {e}")
        threading.Thread(target=work, daemon=True).start()

    def changed(self, _=None):
        self.s.update(source_language=self.labels[self.source.get()], target_language=self.labels[self.target.get()],
                      obs_source=self.obs_source.get().strip())
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
                log("Choose the game source in OBS first.")
                return
            self.start()

    def start(self):
        self.started = True
        self.button.configure(text="Stop")
        self.status.configure(text=f"{self.source.get()} → {self.target.get()}")
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
            log(f"Could not start: {e}")
        finally:
            rest = asyncio.all_tasks(self.loop)
            for task in rest:
                task.cancel()
            if rest:
                self.loop.run_until_complete(asyncio.wait(rest))
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
            self.loop = None
            self.messages.put(self.stopped)

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.task.cancel)

    def stopped(self):
        self.button.configure(text="Start")
        self.status.configure(text="Stopped")
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
            # keep_alive 0 unloads the model, so the graphics card is free right away instead of after the keep-alive time.
            body = json.dumps({"model": self.s["model"], "keep_alive": 0}).encode()
            try:
                urllib.request.urlopen(urllib.request.Request(self.s["ollama_url"] + "/api/generate", data=body,
                                                              headers={"Content-Type": "application/json"}), timeout=5).close()
            except OSError:
                pass


class AreaPicker:
    def __init__(self, window, picture):
        self.window = window
        self.top = top = tk.Toplevel(window.root)
        top.title("Areas to read")
        top.resizable(False, False)
        top.transient(window.root)
        self.image = tk.PhotoImage(data=picture)
        self.w, self.h = self.image.width(), self.image.height()
        ttk.Label(top, padding=8, text="Drag a rectangle around each part you want translated (yellow). With no rectangle the whole "
                                       "picture is read.\nTo show the translation of an area somewhere else, choose the area below and "
                                       "drag the place where it should be shown (blue).").pack(anchor="w")
        self.canvas = tk.Canvas(top, width=self.w, height=self.h, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(padx=8)
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        scale = lambda box: [box[0] * self.w, box[1] * self.h, box[2] * self.w, box[3] * self.h]
        self.boxes = [scale(region["box"]) for region in window.s["regions"]]
        self.displays = [scale(region["display"]) if region["display"] else None for region in window.s["regions"]]
        self.current = None
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        mode = ttk.Frame(top, padding=(8, 8, 8, 0))
        mode.pack(fill="x")
        self.mode = tk.StringVar(value="read")
        ttk.Radiobutton(mode, text="Draw areas to read", variable=self.mode, value="read").pack(side="left")
        ttk.Radiobutton(mode, text="Draw where area", variable=self.mode, value="show").pack(side="left", padx=(16, 4))
        self.which = ttk.Combobox(mode, state="readonly", width=4)
        self.which.pack(side="left")
        ttk.Label(mode, text="is shown").pack(side="left", padx=(4, 12))
        ttk.Button(mode, text="Show it where it is read", command=self.same_place).pack(side="left")
        buttons = ttk.Frame(top, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Use", command=self.use).pack(side="left")
        ttk.Button(buttons, text="Remove last", command=self.remove_last).pack(side="left", padx=8)
        ttk.Button(buttons, text="Remove all", command=self.remove_all).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=top.destroy).pack(side="right")
        self.draw()
        themed(top)
        top.grab_set()

    def draw(self):
        self.canvas.delete("box")
        numbers = [str(n) for n in range(1, len(self.boxes) + 1)]
        self.which.configure(values=numbers)
        if numbers and self.which.get() not in numbers:
            self.which.set(numbers[-1])
        drawing = self.current if self.mode.get() == "read" else None
        for number, box in enumerate(self.boxes + ([drawing] if drawing else []), 1):
            self.canvas.create_rectangle(*box, outline="#ffcc00", width=3, tags="box")
            self.canvas.create_text(box[0] + 7, box[1] + 4, text=str(number), anchor="nw", fill="#ffcc00",
                                    font=("Segoe UI", 12, "bold"), tags="box")
        for number, (box, shown) in enumerate(zip(self.boxes, self.displays), 1):
            if self.current and self.mode.get() == "show" and str(number) == self.which.get():
                shown = self.current
            if shown:
                self.canvas.create_line((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (shown[0] + shown[2]) / 2, (shown[1] + shown[3]) / 2,
                                        fill="#33ccff", width=2, arrow="last", tags="box")
                self.canvas.create_rectangle(*shown, outline="#33ccff", width=3, dash=(6, 4), tags="box")
                self.canvas.create_text(shown[0] + 7, shown[1] + 4, text=str(number), anchor="nw", fill="#33ccff",
                                        font=("Segoe UI", 12, "bold"), tags="box")

    def press(self, e):
        self.start = (e.x, e.y)

    def drag(self, e):
        x, y = min(max(e.x, 0), self.w), min(max(e.y, 0), self.h)
        self.current = [min(self.start[0], x), min(self.start[1], y), max(self.start[0], x), max(self.start[1], y)]
        self.draw()

    def release(self, _):
        big = self.current and self.current[2] - self.current[0] >= 0.05 * self.w and self.current[3] - self.current[1] >= 0.03 * self.h
        if big and self.mode.get() == "read":
            self.boxes.append(self.current)
            self.displays.append(None)
        elif big and self.which.get():
            self.displays[int(self.which.get()) - 1] = self.current
        self.current = None
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

    def use(self):
        before = {tuple(region["box"]): region for region in self.window.s["regions"]}
        unscale = lambda b: [round(b[0] / self.w, 3), round(b[1] / self.h, 3), round(b[2] / self.w, 3), round(b[3] / self.h, 3)]
        regions = []
        for box, shown in zip(self.boxes, self.displays):
            box = unscale(box)
            old = before.get(tuple(box), {})
            regions.append({"box": box, "style": old.get("style"), "display": unscale(shown) if shown else None, "overlay": old.get("overlay", 0)})
        self.window.s["regions"] = regions
        self.top.destroy()
        self.window.show_area()
        self.window.show_look()
        self.window.changed()


class StyleEditor:
    def __init__(self, window):
        self.window = window
        window.editor = self
        self.loading = False
        self.top = top = tk.Toplevel(window.root)
        top.title("Look of translations")
        top.resizable(False, False)
        top.transient(window.root)
        f = ttk.Frame(top, padding=16)
        f.pack(fill="both")
        f.columnconfigure(1, weight=1)
        count = len(window.s["regions"])
        ttk.Label(f, text="Settings for").grid(row=0, column=0, sticky="w", pady=4)
        self.target = ttk.Combobox(f, state="readonly",
                                   values=["All areas (default look)" if count else "Whole picture"] + [f"Area {n}" for n in range(1, count + 1)])
        self.target.current(0)
        self.target.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.target.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.default = tk.BooleanVar()
        self.default_box = ttk.Checkbutton(f, text="Use the default look for this area", variable=self.default, command=self.switch)
        self.default_box.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(f, text="Font").grid(row=2, column=0, sticky="w", pady=4)
        self.font = ttk.Combobox(f, height=20, values=sorted({name for name in tkfont.families(top) if not name.startswith("@")}))
        self.font.grid(row=2, column=1, sticky="ew", padx=(8, 0))
        for event in ("<<ComboboxSelected>>", "<Return>", "<FocusOut>"):
            self.font.bind(event, lambda e: self.apply())

        ttk.Label(f, text="Size").grid(row=3, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=3, column=1, sticky="w", padx=(8, 0))
        self.fixed = tk.BooleanVar()
        self.auto_size = ttk.Radiobutton(row, text="Size of the original text", variable=self.fixed, value=False, command=self.apply)
        self.auto_size.pack(side="left")
        self.fixed_size = ttk.Radiobutton(row, text="Fixed:", variable=self.fixed, value=True, command=self.apply)
        self.fixed_size.pack(side="left", padx=(12, 4))
        self.size = ttk.Spinbox(row, from_=8, to=150, width=5, command=self.apply)
        self.size.bind("<KeyRelease>", lambda e: self.apply())
        self.size.pack(side="left")
        ttk.Label(row, text="px (in a 1080p picture)").pack(side="left", padx=(4, 0))

        ttk.Label(f, text="Style").grid(row=4, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=4, column=1, sticky="w", padx=(8, 0))
        self.bold, self.italic = tk.BooleanVar(), tk.BooleanVar()
        self.bold_box = ttk.Checkbutton(row, text="Bold", variable=self.bold, command=self.apply)
        self.bold_box.pack(side="left")
        self.italic_box = ttk.Checkbutton(row, text="Italic", variable=self.italic, command=self.apply)
        self.italic_box.pack(side="left", padx=(12, 0))

        ttk.Label(f, text="Text colour").grid(row=5, column=0, sticky="w", pady=4)
        self.color = ttk.Button(f, width=10, compound="left", command=lambda: self.pick("color"))
        self.color.grid(row=5, column=1, sticky="w", padx=(8, 0))

        ttk.Label(f, text="Background").grid(row=6, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=6, column=1, sticky="w", padx=(8, 0))
        self.background = ttk.Button(row, width=10, compound="left", command=lambda: self.pick("background"))
        self.background.pack(side="left")
        ttk.Label(row, text="opacity").pack(side="left", padx=(12, 4))
        self.opacity = ttk.Scale(row, from_=0, to=100, length=180, command=lambda v: self.apply())
        self.opacity.pack(side="left")
        self.percent = ttk.Label(row, width=6)
        self.percent.pack(side="left", padx=(6, 0))

        ttk.Label(f, text="Outline").grid(row=7, column=0, sticky="w", pady=4)
        row = ttk.Frame(f)
        row.grid(row=7, column=1, sticky="w", padx=(8, 0))
        self.outline = ttk.Spinbox(row, from_=0, to=8, width=4, command=self.apply)
        self.outline.bind("<KeyRelease>", lambda e: self.apply())
        self.outline.pack(side="left")
        ttk.Label(row, text="px, colour").pack(side="left", padx=(4, 6))
        self.outline_color = ttk.Button(row, width=10, compound="left", command=lambda: self.pick("outline_color"))
        self.outline_color.pack(side="left")

        ttk.Label(f, text="Alignment").grid(row=8, column=0, sticky="w", pady=4)
        self.align = ttk.Combobox(f, state="readonly", width=14, values=list(ALIGN.values()))
        self.align.bind("<<ComboboxSelected>>", lambda e: self.apply())
        self.align.grid(row=8, column=1, sticky="w", padx=(8, 0))

        self.stage = tk.Frame(f, bg="#3d4650", height=110, width=560)
        self.stage.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(12, 4))
        self.stage.pack_propagate(False)
        self.sample = tk.Label(self.stage, text=SAMPLE, padx=10, pady=2)
        self.sample.pack(expand=True)
        ttk.Label(f, text="While translating, OBS shows a sample translation with this look as long as this window is open.\n"
                          "Opacity and outline are shown exactly only in OBS.", foreground=COLORS[THEME]["muted"]).grid(
            row=10, column=0, columnspan=2, sticky="w")
        place = ttk.Frame(top, padding=(16, 0, 16, 10))
        place.pack(fill="x")
        ttk.Label(place, text="Shown in OBS source").pack(side="left")
        self.overlay = ttk.Combobox(place, state="readonly", width=28)
        self.overlay.bind("<<ComboboxSelected>>", lambda e: self.choose_overlay())
        self.overlay.pack(side="left", padx=8)
        self.new_button = ttk.Button(place, text="New source...", command=self.new_overlay)
        self.new_button.pack(side="left")
        self.remove_button = ttk.Button(place, text="Remove source", command=self.remove_overlay)
        self.remove_button.pack(side="left", padx=(8, 0))
        buttons = ttk.Frame(top, padding=(16, 0, 16, 16))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Original look", command=self.reset).pack(side="left")
        ttk.Button(buttons, text="Close", command=self.close).pack(side="right")
        self.controls = [self.font, self.auto_size, self.fixed_size, self.size, self.bold_box, self.italic_box, self.color,
                         self.background, self.opacity, self.outline, self.outline_color, self.align]
        top.protocol("WM_DELETE_WINDOW", self.close)
        self.load()
        themed(top)

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
        self.outline.set(st["outline"])
        self.align.set(ALIGN[st["align"]])
        for widget in self.controls:
            widget.state(["!disabled" if self.own() else "disabled"])
        names = [overlay["name"] for overlay in self.window.s["overlays"]]
        self.overlay.configure(values=names)
        if self.area() >= 0:
            self.overlay.current(self.window.s["regions"][self.area()]["overlay"])
        else:
            self.overlay.set(names[0] if not self.window.s["regions"] else "chosen for each area")
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
        name = (ask_text(self.top, "New OBS source", "Name of the new browser source for translations:",
                         f"Translation overlay {len(names) + 1}") or "").strip()
        if not name:
            return
        if name in names:
            messagebox.showinfo("OBS Screen Translator", "A source with this name is already in the list.", parent=self.top)
            return
        self.window.s["overlays"].append({"name": name})
        self.window.s["regions"][self.area()]["overlay"] = len(self.window.s["overlays"]) - 1
        self.window.show_look()
        self.load()
        self.window.changed()

    def remove_overlay(self):
        n = self.overlay.current()
        overlays = self.window.s["overlays"]
        if n <= 0 or not messagebox.askyesno("OBS Screen Translator", f'Remove the source "{overlays[n]["name"]}" from OBS? Its areas go '
                                             f'back to "{overlays[0]["name"]}".', parent=self.top):
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
                  outline=number(self.outline.get(), 0, 8, 0), align=list(ALIGN)[max(self.align.current(), 0)])
        save_settings(self.window.file, self.window.s)
        self.show()

    def pick(self, name):
        chosen = colorchooser.askcolor(self.style()[name], parent=self.top, title="Choose a colour")[1]
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
        stage = (0x3d, 0x46, 0x50)
        mixed = "#%02x%02x%02x" % tuple(round(int(st["background"][1 + 2 * i:3 + 2 * i], 16) * st["opacity"] + stage[i] * (1 - st["opacity"]))
                                        for i in range(3))
        self.sample.configure(font=tkfont.Font(family=st["font"], size=-(st["size"] or 36), weight="bold" if st["bold"] else "normal",
                                               slant="italic" if st["italic"] else "roman"), fg=st["color"], bg=mixed)
        self.window.show_look()
        self.window.sample = self.area()
        if self.window.translator:
            self.window.translator.sample = self.area()

    def close(self):
        self.window.sample = None
        if self.window.translator:
            self.window.translator.sample = None
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
            for n, part in enumerate(re.sub(r"^- ", "\u2022  ", line).split("**")):
                view.insert("end", part, tags + (("strong",) if n % 2 else ()))
            view.insert("end", "\n", tags)
        view.configure(state="disabled")
        ttk.Button(top, text="Close", command=top.destroy).pack(anchor="e", padx=16, pady=16)
        themed(top)


class KeyPicker:
    def __init__(self, window):
        self.window = window
        self.top = top = tk.Toplevel(window.root)
        top.title("Show/hide key")
        top.resizable(False, False)
        top.transient(window.root)
        ttk.Label(top, padding=12, text="Press the key that should show and hide the translations: a function key (F1 to F24)\n"
                                        "or a combination with Ctrl or Alt. It works while the game or OBS is in front.").pack()
        buttons = ttk.Frame(top, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="No key", takefocus=False, command=lambda: self.use(None)).pack(side="left")
        ttk.Button(buttons, text="Cancel", takefocus=False, command=top.destroy).pack(side="right")
        top.bind("<KeyPress>", self.press)
        themed(top)
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
