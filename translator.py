import argparse
import asyncio
import base64
import difflib
import hashlib
import json
import os
import pathlib
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import types
import urllib.request
from tkinter import ttk

import cv2
import numpy as np
import websockets
from rapidocr import RapidOCR

VERSION = "0.2.0"
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
reader = None


class Problem(Exception):
    pass


def load_settings(path):
    stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    settings = {**DEFAULTS, **stored}
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


def obs_websocket_config():
    for base in (os.environ.get("APPDATA"), "~/.config", "~/Library/Application Support"):
        path = pathlib.Path(base or "").expanduser() / "obs-studio/plugin_config/obs-websocket/config.json"
        if base and path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    raise Problem("OBS WebSocket settings not found. Start OBS once and enable Tools > WebSocket Server Settings > Enable WebSocket server.")


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
    await obs.ws.close()
    return sorted(i["inputName"] for i in inputs if not re.search("audio|wasapi|pulse|alsa|browser|text", i["inputKind"]))


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

    def ollama(self, path, body=None, timeout=60):
        request = urllib.request.Request(self.s["ollama_url"] + path, data=body and json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(request, timeout=timeout)

    def prepare_model(self):
        try:
            self.ollama("/api/version").close()
        except OSError:
            program = shutil.which("ollama") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            if not os.path.exists(program):
                raise Problem("Ollama is not installed. Get it from https://ollama.com/download, install it and press Start again.")
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
        r = text_reader(self.s)(frame)
        lines = []
        for box, text, score in zip(r.boxes, r.txts, r.scores) if r.txts else ():
            x0, y0, x1, y1 = float(box[:, 0].min() / w), float(box[:, 1].min() / h), float(box[:, 0].max() / w), float(box[:, 1].max() / h)
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
            if (await obs.request("GetInputSettings", inputName=name))["inputSettings"].get("url", "").split("&opacity")[0] != url:
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
        obs = await OBS().connect()
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
                                "centered": t.centered} for t in shown]})

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

    async def preview(self, image, folder):
        self.prepare_model()
        frame = cv2.imdecode(np.fromfile(image, np.uint8), cv2.IMREAD_COLOR) if image else await self.frame(await OBS().connect())
        h, w = frame.shape[:2]
        text_reader(self.s)
        started = time.perf_counter()
        blocks = self.read(frame)
        log(f"reading took {(time.perf_counter() - started) * 1000:.0f} ms, {len(blocks)} texts")
        for b in blocks:
            cv2.rectangle(frame, (int(b.box[0] * w), int(b.box[1] * h)), (int(b.box[2] * w), int(b.box[3] * h)), (0, 255, 0), 2)
            log(f"  {b.text}\n    -> {self.translate([b.text])[0] or '(no translation)'}")
        (folder / "preview.png").write_bytes(cv2.imencode(".png", frame)[1])
        log(f"frame with the detected texts: {folder / 'preview.png'}")


class Window:
    def __init__(self, settings_file):
        global log
        self.file = settings_file
        self.s = load_settings(settings_file)
        self.messages = queue.Queue()
        self.loop = self.task = None
        self.restart = False
        log = self.messages.put
        self.labels = {f"{name} ({code})": code for code, name in LANGUAGES.items()}
        names = sorted(self.labels)

        self.root = root = tk.Tk()
        root.title(f"OBS Screen Translator {VERSION}")
        root.minsize(620, 420)
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
        self.button = ttk.Button(top, text="Start", command=self.toggle)
        self.button.grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.status = ttk.Label(top, text="Stopped")
        self.status.grid(row=3, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(10, 0))
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
        for box in (self.source, self.target, self.obs_source):
            box.bind("<<ComboboxSelected>>", self.changed)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.pump)
        self.refresh()

    def refresh(self):
        def work():
            try:
                names = asyncio.run(obs_video_sources())
                self.messages.put(lambda: self.obs_source.configure(values=names))
                if not self.s["obs_source"]:
                    log("Choose the game source and press Start.")
            except Problem as e:
                log(str(e))
            except (OSError, websockets.WebSocketException):
                log("OBS is not running or its WebSocket server is off. Start OBS and press Refresh.")
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
        self.button.configure(text="Stop")
        self.status.configure(text=f"{self.source.get()} → {self.target.get()}")
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        self.loop = asyncio.new_event_loop()
        self.task = self.loop.create_task(Translator(dict(self.s), self.file.parent).serve())
        try:
            self.loop.run_until_complete(self.task)
        except asyncio.CancelledError:
            pass
        except Problem as e:
            log(str(e))
        except OSError as e:
            log(f"Could not start: {e}")
        finally:
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
        self.stop()
        self.root.destroy()


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
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        Window(settings_file).root.mainloop()
        os._exit(0)
