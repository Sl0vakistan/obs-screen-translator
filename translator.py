import argparse
import asyncio
import base64
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
from tkinter import messagebox, ttk

import cv2
import numpy as np
import websockets
from rapidocr import RapidOCR

VERSION = "0.5.0"
PROJECT = "https://github.com/Sl0vakistan/obs-screen-translator"
FROZEN = getattr(sys, "frozen", False)
HERE = pathlib.Path(sys._MEIPASS) if FROZEN else pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get("APPDATA", HERE)) / "OBS Screen Translator" if FROZEN else HERE
LANGUAGES = json.loads((HERE / "languages.json").read_text(encoding="utf-8"))
DEFAULTS = {
    "obs_source": "",
    "scenes": [],
    "overlay_source": "Translation overlay",
    "create_overlay_source": True,
    "source_language": "en",
    "target_language": "sk",
    "regions": [],
    "start_automatically": False,
    "hotkey": None,
    "opacity": 0.85,
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
GUIDE = """# What you need
- Windows 10 or 11 and OBS Studio from obsproject.com.
- A graphics card with about 8 GB of free memory for the translation model, and about 10 GB of free disk space.

# First start
1. Start OBS once, then this program. The order does not matter: the program waits for OBS.
2. If the WebSocket server in OBS is off, the program asks to turn it on. Close OBS when it says so and start OBS again. The previous OBS setting is kept in a backup file.
3. If Ollama is missing, the program asks to download it from ollama.com and install it. Ollama runs the translation model.
4. On the first Start the translation model (8.1 GB) is downloaded, once.

# Setting up
- Translate from / Translate to: the language of the game and the language of your viewers. The target starts as the language of Windows.
- Game source in OBS: the source with the game. A single capture card in the scene that is on air is chosen by itself.
- Area to read: optional rectangles around the parts to translate, for example the subtitles. With none the whole picture is read.
- Background opacity: how dark the box behind a translation is, from none to solid black.
- Show/hide key: one key that shows and hides the translations from any window, also from a Stream Deck.
- Start translating when this program opens: no need to press Start next time.

Then press Start. A browser source named Translation overlay appears in the scene that is on air. Keep it above the game.

# During the stream
- Hiding the Translation overlay source in OBS, or pressing the show/hide key, pauses reading and translating.
- Changing a language or an area while translating restarts the translation by itself.
- Keep this window open. Closing it removes the translations from the picture and unloads the translation model from the graphics card.

# When something does not work
- "Waiting for OBS": OBS is not running, or its WebSocket server is off (Tools > WebSocket Server Settings in OBS).
- No translations on screen: the Translation overlay source is hidden, is not in the scene that is on air, or sits inside a nested scene.
- Moving text stays untranslated until it stands still for a moment. This is on purpose: it skips signs and number plates.
- The first translation after a break is late: the model is being loaded, which takes about 12 seconds.
- Cyrillic, Arabic, Korean and other scripts are not read yet. Latin script and Chinese are.
"""
reader = None


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
    settings = {**DEFAULTS, **stored}
    single = settings.pop("region", None)
    if single and single != [0, 0, 1, 1] and not settings["regions"]:
        settings["regions"] = [single]
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


async def toggle_overlay(name):
    obs = await OBS().connect()
    scenes = [(await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]]
    scenes += [s["sceneName"] for s in (await obs.request("GetSceneList"))["scenes"] if s["sceneName"] != scenes[0]]
    shown = None
    for scene in scenes:
        try:
            item = (await obs.request("GetSceneItemId", sceneName=scene, sourceName=name))["sceneItemId"]
        except RuntimeError:
            continue
        if shown is None:
            shown = not (await obs.request("GetSceneItemEnabled", sceneName=scene, sceneItemId=item))["sceneItemEnabled"]
        await obs.request("SetSceneItemEnabled", sceneName=scene, sceneItemId=item, sceneItemEnabled=shown)
    await obs.ws.close()
    return shown


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
        log(f"translation model ready: {self.s['model']} | {self.translate(['Hello there.'])[0]} | {len(self.cache)} cached translations")

    def read(self, frame):
        h, w = frame.shape[:2]
        picture, strips = frame, [(0, h, 0, 0)]
        if self.s["regions"]:
            areas = [tuple(int(a * b) for a, b in zip(region, (w, h, w, h))) for region in self.s["regions"]]
            picture = np.zeros((sum(b - t for l, t, r, b in areas) + 16 * (len(areas) - 1), max(r - l for l, t, r, b in areas), 3), np.uint8)
            strips, y = [], 0
            for l, t, r, b in areas:
                picture[y:y + b - t, :r - l] = frame[t:b, l:r]
                strips.append((y, y + b - t, l, t))
                y += b - t + 16
        r = text_reader(self.s)(picture)
        lines = []
        for box, text, score in zip(r.boxes, r.txts, r.scores) if r.txts else ():
            middle = (box[:, 1].min() + box[:, 1].max()) / 2
            start, _, left, top = min(strips, key=lambda s: max(s[0] - middle, middle - s[1], 0))
            x0, y0 = float((box[:, 0].min() + left) / w), float((box[:, 1].min() - start + top) / h)
            x1, y1 = float((box[:, 0].max() + left) / w), float((box[:, 1].max() - start + top) / h)
            if score >= self.s["min_score"] and (y1 - y0) * 1080 >= self.s["min_height"] and re.search(r"[^\W\d_]{3}", text):
                lines.append((y0, x0, x1, y1, " ".join(text.split())))
        blocks = []
        for y0, x0, x1, y1, text in sorted(lines):
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
                blocks.append({"lines": [text], "box": [x0, y0, x1, y1], "last": (x0, y0, x1, y1), "centered": 0})
        return [types.SimpleNamespace(text=" ".join(b["lines"]), box=b["box"], rows=len(b["lines"]),
                                      line_height=(b["box"][3] - b["box"][1]) / len(b["lines"]),
                                      centered=b["centered"] > 0 if len(b["lines"]) > 1 else abs(b["box"][0] + b["box"][2] - 1) < 0.04)
                for b in blocks]

    def ask_model(self, text):
        if self.closed:
            raise Problem("the program is closing")
        body = {"model": self.s["model"], "messages": [{"role": "user", "content": self.prompt + text}], "stream": False,
                "keep_alive": "30m", "options": {"temperature": 0, "num_predict": 400, "num_ctx": 2048}}
        with self.ollama("/api/chat", body) as response:
            return json.loads(response.read())["message"]["content"]

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

    async def prepare_overlay(self, obs):
        name = self.s["overlay_source"]
        video = await obs.request("GetVideoSettings")
        url = (HERE / "overlay.html").as_uri() + f"?scale={video['baseWidth'] / 1920:g}&ws=ws://127.0.0.1:{self.s['port']}"
        if any(i["inputName"] == name for i in (await obs.request("GetInputList"))["inputs"]):
            if (await obs.request("GetInputSettings", inputName=name))["inputSettings"].get("url", "") != url:
                await obs.request("SetInputSettings", inputName=name, inputSettings={"url": url})
            return
        scenes = self.s["scenes"] or [(await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]]
        await obs.request("CreateInput", sceneName=scenes[0], inputName=name, inputKind="browser_source",
                          inputSettings={"url": url, "width": video["baseWidth"], "height": video["baseHeight"], "shutdown": False,
                                         "restart_when_active": False})
        for scene in scenes[1:]:
            await obs.request("CreateSceneItem", sceneName=scene, sourceName=name)
        log(f'added the browser source "{name}" to: {", ".join(scenes)}')

    async def overlay_visible(self, obs):
        try:
            scene = (await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]
            item = (await obs.request("GetSceneItemId", sceneName=scene, sourceName=self.s["overlay_source"]))["sceneItemId"]
            return (await obs.request("GetSceneItemEnabled", sceneName=scene, sceneItemId=item))["sceneItemEnabled"]
        except RuntimeError:
            return False

    async def run(self, publish):
        self.obs = obs = await OBS().connect()
        log("connected to OBS")
        if self.s["create_overlay_source"]:
            await self.prepare_overlay(obs)
        loop = asyncio.get_running_loop()
        tracks = []
        state = types.SimpleNamespace(job=None, n=0, error=None, dirty=False, active=None)

        def send():
            shown = [t for t in tracks if t.stable and t.translation]
            for t in shown:
                if not t.logged:
                    t.logged = True
                    log(f"{time.monotonic() - t.since:.2f} s  {t.text}\n          {t.translation}")
            publish({"items": [{"id": t.id, "text": t.translation, "box": t.box, "rows": t.rows, "line_height": t.line_height,
                                "centered": t.centered} for t in shown], "opacity": self.s["opacity"]})

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
            active = await self.overlay_visible(obs)
            if active != state.active:
                state.active = active
                log("translating" if active else "paused (the overlay source is hidden or not in the current scene)")
            if not active:
                tracks.clear()
                send()
                await asyncio.sleep(0.5)
                continue
            try:
                blocks = await loop.run_in_executor(None, self.read, await self.frame(obs))
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
                                                        centered=b.centered, seen=now, since=started, stable=False,
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
        for x0, y0, x1, y1 in self.s["regions"]:
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
        self.restart = self.looking = self.started = False
        log = self.messages.put
        ask = self.ask
        self.labels = {f"{name} ({code})": code for code, name in LANGUAGES.items()}
        names = sorted(self.labels)

        self.root = root = tk.Tk()
        root.title(f"OBS Screen Translator {VERSION}")
        root.minsize(620, 420)
        bar = tk.Menu(root)
        menu = tk.Menu(bar, tearoff=False)
        menu.add_command(label="Installation and setup", command=lambda: Page(root, "Installation and setup", GUIDE))
        menu.add_command(label="Details", command=self.details)
        menu.add_separator()
        menu.add_command(label="Open the settings folder", command=lambda: os.startfile(self.file.parent))
        menu.add_command(label="Project page", command=lambda: webbrowser.open(PROJECT))
        bar.add_cascade(label="Help", menu=menu)
        root.configure(menu=bar)
        top = ttk.Frame(root, padding=12)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Translate from").grid(row=0, column=0, sticky="w", pady=4)
        self.source = ttk.Combobox(top, values=names, state="readonly")
        self.source.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        ttk.Label(top, text="Translate to").grid(row=1, column=0, sticky="w", pady=4)
        self.target = ttk.Combobox(top, values=names, state="readonly")
        self.target.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        ttk.Label(top, text="Game source in OBS").grid(row=2, column=0, sticky="w", pady=4)
        self.obs_source = ttk.Combobox(top)
        self.obs_source.grid(row=2, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(top, text="Refresh", command=self.refresh).grid(row=2, column=2, padx=(8, 0))
        ttk.Label(top, text="Area to read").grid(row=3, column=0, sticky="w", pady=4)
        self.area = ttk.Label(top)
        self.area.grid(row=3, column=1, sticky="w", padx=(8, 0))
        ttk.Button(top, text="Choose...", command=self.choose_area).grid(row=3, column=2, padx=(8, 0))
        ttk.Label(top, text="Background opacity").grid(row=4, column=0, sticky="w", pady=4)
        self.percent = ttk.Label(top)
        self.percent.grid(row=4, column=2, padx=(8, 0))
        self.opacity = ttk.Scale(top, from_=0, to=100, command=self.shade)
        self.opacity.grid(row=4, column=1, sticky="ew", padx=(8, 0))
        for event in ("<ButtonRelease-1>", "<KeyRelease>"):
            self.opacity.bind(event, lambda e: save_settings(self.file, self.s))
        ttk.Label(top, text="Show/hide key").grid(row=5, column=0, sticky="w", pady=4)
        self.key = ttk.Label(top)
        self.key.grid(row=5, column=1, sticky="w", padx=(8, 0))
        ttk.Button(top, text="Set...", command=lambda: KeyPicker(self)).grid(row=5, column=2, padx=(8, 0))
        self.auto = tk.BooleanVar(value=self.s["start_automatically"])
        ttk.Checkbutton(top, text="Start translating when this program opens", variable=self.auto,
                        command=self.remember).grid(row=6, column=0, columnspan=3, sticky="w", pady=4)
        self.button = ttk.Button(top, text="Start", command=self.toggle)
        self.button.grid(row=7, column=0, sticky="w", pady=(10, 0))
        self.status = ttk.Label(top, text="Stopped")
        self.status.grid(row=7, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(10, 0))
        frame = ttk.Frame(root, padding=(12, 0, 12, 12))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, height=14, wrap="word", state="disabled")
        bar = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        self.source.set(next(label for label, code in self.labels.items() if code == self.s["source_language"]))
        self.target.set(next(label for label, code in self.labels.items() if code == self.s["target_language"]))
        self.obs_source.set(self.s["obs_source"])
        self.opacity.set(self.s["opacity"] * 100)
        self.shade(self.s["opacity"] * 100)
        self.show_area()
        for box in (self.source, self.target, self.obs_source):
            box.bind("<<ComboboxSelected>>", self.changed)
        root.protocol("WM_DELETE_WINDOW", self.close)
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

    def shade(self, value):
        self.s["opacity"] = round(float(value)) / 100
        self.percent.configure(text=f"{round(float(value))} %")
        if self.translator:
            self.translator.s["opacity"] = self.s["opacity"]

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
                    if asyncio.run(toggle_overlay(self.s["overlay_source"])) is None:
                        log("There is nothing to show or hide yet. Press Start first.")
                except (Problem, OSError, websockets.WebSocketException):
                    log("The key was pressed, but OBS is not reachable.")
        user.UnregisterHotKey(None, 1)

    def show_area(self):
        count = len(self.s["regions"])
        self.area.configure(text="Whole picture" if not count else "1 area" if count == 1 else f"{count} areas")

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
        top.title("Area to read")
        top.resizable(False, False)
        top.transient(window.root)
        self.image = tk.PhotoImage(data=picture)
        self.w, self.h = self.image.width(), self.image.height()
        ttk.Label(top, text="Drag a rectangle around each part you want translated. With no rectangle the whole picture is read.",
                  padding=8).pack(anchor="w")
        self.canvas = tk.Canvas(top, width=self.w, height=self.h, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(padx=8)
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")
        self.boxes = [[x0 * self.w, y0 * self.h, x1 * self.w, y1 * self.h] for x0, y0, x1, y1 in window.s["regions"]]
        self.current = None
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        buttons = ttk.Frame(top, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Use", command=self.use).pack(side="left")
        ttk.Button(buttons, text="Remove last", command=self.remove_last).pack(side="left", padx=8)
        ttk.Button(buttons, text="Remove all", command=self.remove_all).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=top.destroy).pack(side="right")
        self.draw()
        top.grab_set()

    def draw(self):
        self.canvas.delete("box")
        for number, box in enumerate(self.boxes + ([self.current] if self.current else []), 1):
            self.canvas.create_rectangle(*box, outline="#ffcc00", width=3, tags="box")
            self.canvas.create_text(box[0] + 7, box[1] + 4, text=str(number), anchor="nw", fill="#ffcc00",
                                    font=("Segoe UI", 12, "bold"), tags="box")

    def press(self, e):
        self.start = (e.x, e.y)

    def drag(self, e):
        x, y = min(max(e.x, 0), self.w), min(max(e.y, 0), self.h)
        self.current = [min(self.start[0], x), min(self.start[1], y), max(self.start[0], x), max(self.start[1], y)]
        self.draw()

    def release(self, _):
        if self.current and self.current[2] - self.current[0] >= 0.05 * self.w and self.current[3] - self.current[1] >= 0.03 * self.h:
            self.boxes.append(self.current)
        self.current = None
        self.draw()

    def remove_last(self):
        del self.boxes[-1:]
        self.draw()

    def remove_all(self):
        self.boxes = []
        self.draw()

    def use(self):
        self.window.s["regions"] = [[round(x0 / self.w, 3), round(y0 / self.h, 3), round(x1 / self.w, 3), round(y1 / self.h, 3)]
                                    for x0, y0, x1, y1 in self.boxes]
        self.top.destroy()
        self.window.show_area()
        self.window.changed()


class Page:
    def __init__(self, root, title, text):
        top = tk.Toplevel(root)
        top.title(title)
        top.transient(root)
        frame = ttk.Frame(top, padding=(12, 12, 12, 0))
        frame.pack(fill="both", expand=True)
        view = tk.Text(frame, width=96, height=34, wrap="word", padx=10, pady=6, relief="flat", font=("Segoe UI", 10),
                       spacing1=2, spacing3=2)
        bar = ttk.Scrollbar(frame, command=view.yview)
        view.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        view.pack(fill="both", expand=True)
        view.tag_configure("heading", font=("Segoe UI", 12, "bold"), spacing1=4, spacing3=4)
        for line in text.split("\n"):
            heading = line.startswith("# ")
            view.insert("end", (line[2:] if heading else line) + "\n", "heading" if heading else ())
        view.configure(state="disabled")
        ttk.Button(top, text="Close", command=top.destroy).pack(anchor="e", padx=12, pady=12)


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
