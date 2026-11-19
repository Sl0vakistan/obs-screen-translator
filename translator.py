import argparse
import asyncio
import base64
import difflib
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import types
import urllib.request

import cv2
import numpy as np
import websockets
from rapidocr import RapidOCR
from rapidocr.utils.typings import EngineType

HERE = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description="Translate the on-screen text of an OBS source and draw the translation over the original.")
parser.add_argument("--settings", default=str(HERE / "settings.json"), help="settings file (default: settings.json next to this script)")
parser.add_argument("--preview", action="store_true", help="read one frame from OBS, print texts and translations, save preview.png")
parser.add_argument("--image", help="like --preview, but read this image file instead of OBS")
ARGS = parser.parse_args()
SETTINGS = pathlib.Path(ARGS.settings).resolve()
if not SETTINGS.exists():
    sys.exit(f"{SETTINGS} not found. Copy settings.example.json to settings.json and set obs_source to the name of your game source.")
S = json.loads(SETTINGS.read_text(encoding="utf-8"))
SRC, DST = S["source_language"], S["target_language"]
PROMPT = (f"You are a professional {SRC['name']} ({SRC['code']}) to {DST['name']} ({DST['code']}) translator. "
          f"Your goal is to accurately convey the meaning and nuances of the original {SRC['name']} text while adhering to "
          f"{DST['name']} grammar, vocabulary, and cultural sensitivities. {S['context']}\n"
          f"Produce only the {DST['name']} translation, without any additional explanations or commentary. "
          f"Please translate the following {SRC['name']} text into {DST['name']}:\n\n\n")
CACHE = SETTINGS.parent / f"cache_{hashlib.md5((S['model'] + PROMPT).encode()).hexdigest()[:8]}.json"
cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

ocr = RapidOCR(params={"Global.use_cls": False, "Global.log_level": "error", "Det.limit_type": "max", "Det.limit_side_len": 1280,
                       "EngineConfig.onnxruntime.intra_op_num_threads": S["ocr_threads"],
                       **({"Det.engine_type": EngineType.TORCH, "Rec.engine_type": EngineType.TORCH, "EngineConfig.torch.use_cuda": True}
                          if S["ocr_on_gpu"] else {})})


def key(text):
    return re.sub(r"\W", "", text.lower())


def read(frame):
    h, w = frame.shape[:2]
    r = ocr(frame)
    lines = []
    for box, text, score in zip(r.boxes, r.txts, r.scores) if r.txts else ():
        x0, y0, x1, y1 = float(box[:, 0].min() / w), float(box[:, 1].min() / h), float(box[:, 0].max() / w), float(box[:, 1].max() / h)
        if score >= S["min_score"] and (y1 - y0) * 1080 >= S["min_height"] and re.search(r"[^\W\d_]{3}", text):
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


def ollama(path, body=None):
    request = urllib.request.Request(S["ollama_url"] + path, data=body and json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def ask_model(text):
    return ollama("/api/chat", {"model": S["model"], "messages": [{"role": "user", "content": PROMPT + text}], "stream": False,
                                "keep_alive": "30m", "options": {"temperature": 0, "num_predict": 400, "num_ctx": 2048}})["message"]["content"]


def tidy(text, translation):
    translation = " ".join(translation.split())
    if translation.endswith(".") and not text.endswith("."):
        translation = translation[:-1]
    if text.isupper():
        translation = translation.upper()
    return "" if key(translation) == key(text) or len(translation) > 3 * len(text) + 20 else translation


def translate(texts):
    try:
        if len(texts) > 1:
            answers = [x for x in ask_model("\n".join(texts)).split("\n") if x.strip()]
            if len(answers) == len(texts):
                return [tidy(a, b) for a, b in zip(texts, answers)]
        return [tidy(a, ask_model(a)) for a in texts]
    except Exception as e:
        print("translation failed:", e)
        return [None] * len(texts)


def start_ollama():
    try:
        ollama("/api/version")
    except OSError:
        print("starting Ollama...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(30):
            time.sleep(1)
            try:
                ollama("/api/version")
                break
            except OSError:
                pass
    print("translation model ready:", S["model"], "|", translate(["Hello there."])[0], f"| {len(cache)} cached translations")


def obs_websocket_config():
    for base in (os.environ.get("APPDATA"), "~/.config", "~/Library/Application Support"):
        path = pathlib.Path(base or "").expanduser() / "obs-studio/plugin_config/obs-websocket/config.json"
        if base and path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    sys.exit("OBS WebSocket settings not found. Start OBS once and enable Tools > WebSocket Server Settings > Enable WebSocket server.")


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

    async def frame(self):
        d = (await self.request("GetSourceScreenshot", sourceName=S["obs_source"], imageFormat="jpg", imageWidth=1920,
                                imageCompressionQuality=85))["imageData"]
        return cv2.imdecode(np.frombuffer(base64.b64decode(d.split(",", 1)[1]), np.uint8), cv2.IMREAD_COLOR)


async def create_overlay_source(obs):
    name = S["overlay_source"]
    if any(i["inputName"] == name for i in (await obs.request("GetInputList"))["inputs"]):
        return
    video = await obs.request("GetVideoSettings")
    scenes = S["scenes"] or [(await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]]
    url = (HERE / "overlay.html").as_uri() + f"?scale={video['baseWidth'] / 1920:g}&ws=ws://127.0.0.1:{S['port']}"
    await obs.request("CreateInput", sceneName=scenes[0], inputName=name, inputKind="browser_source",
                      inputSettings={"url": url, "width": video["baseWidth"], "height": video["baseHeight"], "shutdown": False,
                                     "restart_when_active": False})
    for scene in scenes[1:]:
        await obs.request("CreateSceneItem", sceneName=scene, sourceName=name)
    print(f'added the browser source "{name}" to: {", ".join(scenes)}')


async def overlay_visible(obs):
    try:
        scene = (await obs.request("GetCurrentProgramScene"))["currentProgramSceneName"]
        item = (await obs.request("GetSceneItemId", sceneName=scene, sourceName=S["overlay_source"]))["sceneItemId"]
        return (await obs.request("GetSceneItemEnabled", sceneName=scene, sceneItemId=item))["sceneItemEnabled"]
    except RuntimeError:
        return False


def same_text(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85


def same_place(a, b):
    return abs(a[0] + a[2] - b[0] - b[2]) < 0.012 and abs(a[1] - b[1]) < 0.006


def overlap(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w > 0 and h > 0 and w * h > 0.3 * min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


async def run(publish):
    obs = await OBS().connect()
    print("connected to OBS")
    if S["create_overlay_source"]:
        await create_overlay_source(obs)
    loop = asyncio.get_running_loop()
    tracks = []
    state = types.SimpleNamespace(job=None, n=0, error=None, dirty=False, active=None)

    def send():
        shown = [t for t in tracks if t.stable and t.translation]
        for t in shown:
            if not t.logged:
                t.logged = True
                print(f"{time.strftime('%H:%M:%S')}  {time.monotonic() - t.since:.2f} s  {t.text}\n{'':17s}{t.translation}")
        publish({"items": [{"id": t.id, "text": t.translation, "box": t.box, "rows": t.rows, "line_height": t.line_height,
                            "centered": t.centered} for t in shown]})

    def done(batch, translations):
        state.job = None
        for t, translation in zip(batch, translations):
            t.translation = translation or ""
            if translation is not None:
                cache[key(t.text)] = translation
                state.dirty = True
        next_job()
        send()

    def next_job():
        for t in tracks:
            if t.translation is None:
                t.translation = cache.get(key(t.text))
        waiting = sorted((t for t in tracks if t.translation is None and (t.stable or t.sentence)),
                         key=lambda t: (not t.stable, not t.sentence, -t.line_height))
        if waiting and not state.job:
            batch = waiting[:1] if waiting[0].sentence else list({key(t.text): t for t in waiting if not t.sentence}.values())[:12]
            state.job = loop.run_in_executor(None, translate, [t.text for t in batch])
            state.job.add_done_callback(lambda f: done(batch, f.result()))

    while True:
        started = time.monotonic()
        active = await overlay_visible(obs)
        if active != state.active:
            state.active = active
            print(time.strftime("%H:%M:%S"), "translating" if active else "paused (the overlay source is hidden or not in the current scene)")
        if not active:
            tracks.clear()
            send()
            await asyncio.sleep(0.5)
            continue
        try:
            blocks = await loop.run_in_executor(None, read, await obs.frame())
            state.error = None
        except RuntimeError as e:
            if str(e) != state.error:
                print("screenshot failed:", e)
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
                                                    translation=cache.get(key(b.text)), logged=False,
                                                    sentence=sum(not x.isupper() for x in words) >= 2))
        tracks[:] = [t for t in tracks if now - t.seen <= S["linger"]]
        next_job()
        send()
        if state.dirty:
            state.dirty = False
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
        await asyncio.sleep(max(0, S["interval"] - (time.monotonic() - started)))


async def main():
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

    async with websockets.serve(client, "127.0.0.1", S["port"]):
        while True:
            try:
                await run(publish)
            except (OSError, websockets.ConnectionClosed):
                publish({"items": []})
                print("OBS is not reachable, retrying in 3 s")
                await asyncio.sleep(3)


async def preview(image):
    frame = cv2.imdecode(np.fromfile(image, np.uint8), cv2.IMREAD_COLOR) if image else await (await OBS().connect()).frame()
    h, w = frame.shape[:2]
    started = time.perf_counter()
    blocks = read(frame)
    print(f"OCR {(time.perf_counter() - started) * 1000:.0f} ms, {len(blocks)} texts")
    for b in blocks:
        cv2.rectangle(frame, (int(b.box[0] * w), int(b.box[1] * h)), (int(b.box[2] * w), int(b.box[3] * h)), (0, 255, 0), 2)
        print(f"  {b.text}\n    -> {translate([b.text])[0] or '(no translation)'}")
    (SETTINGS.parent / "preview.png").write_bytes(cv2.imencode(".png", frame)[1])
    print("frame with the detected texts:", SETTINGS.parent / "preview.png")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    start_ollama()
    warmup = np.zeros((1080, 1920, 3), np.uint8)
    cv2.putText(warmup, "Warming up the text reader", (500, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    print("text reader ready:", read(warmup)[0].text)
    asyncio.run(preview(ARGS.image) if ARGS.preview or ARGS.image else main())
