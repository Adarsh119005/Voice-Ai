import datetime
import json
import os
import re
import shutil
import tempfile
import threading
import time
import tkinter as tk
import wave
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import numpy as np

try:
    import winsound
except ImportError:
    winsound = None

GEMINI_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICES = [
    "Charon · Informative", "Fenrir · Excitable", "Puck · Upbeat", "Orus · Firm",
    "Enceladus · Breathy", "Algenib · Gravelly", "Iapetus · Clear", "Umbriel · Easy-going",
    "Algieba · Smooth", "Rasalgethi · Informative", "Alnilam · Firm", "Schedar · Even",
    "Achird · Friendly", "Zubenelgenubi · Casual", "Sadachbia · Lively", "Sadaltager · Knowledgeable",
]
EDGE_VOICES = {
    "Guy · US": "en-US-GuyNeural",
    "Christopher · US": "en-US-ChristopherNeural",
    "Eric · US": "en-US-EricNeural",
    "Roger · US": "en-US-RogerNeural",
    "Steffan · US": "en-US-SteffanNeural",
    "Andrew · US": "en-US-AndrewNeural",
    "Brian · US": "en-US-BrianNeural",
    "Ryan · UK": "en-GB-RyanNeural",
    "Thomas · UK": "en-GB-ThomasNeural",
    "William · Australia": "en-AU-WilliamNeural",
    "Liam · Canada": "en-CA-LiamNeural",
    "Connor · Ireland": "en-IE-ConnorNeural",
    "Prabhat · India": "en-IN-PrabhatNeural",
    "Luke · South Africa": "en-ZA-LukeNeural",
    "Mitchell · New Zealand": "en-NZ-MitchellNeural",
    "Wayne · Singapore": "en-SG-WayneNeural",
    "Chilemba · Kenya": "en-KE-ChilembaNeural",
    "Abeo · Nigeria": "en-NG-AbeoNeural",
    "James · Philippines": "en-PH-JamesNeural",
    "Sam · Hong Kong": "en-HK-SamNeural",
}
EDGE_HINDI_VOICES = {
    "Madhur · Hindi (male)": "hi-IN-MadhurNeural",
    "Swara · Hindi (female)": "hi-IN-SwaraNeural",
}
LANGS = {"Auto (Hindi + English)": "auto", "English": "en", "Hindi": "hi"}
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…।॥])\s+")

GEMINI_SR = 24000
BASE = Path(__file__).parent
CONFIG_PATH = BASE / "voice_app_config.json"
VOICE_DIR = BASE / "voices"
AUDIO_EXT = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
PREVIEW_PATH = Path(tempfile.gettempdir()) / "voice_studio_preview.wav"
PIP_NAMES = {"google": "google-genai", "chatterbox": "chatterbox-tts", "torch": "torch", "librosa": "librosa", "edge_tts": "edge-tts"}

BASE_STYLES = {
    "Dramatic": dict(
        gemini="Say this in a deep, cinematic male narrator voice. Slow build-up, dramatic pauses, intensity rising on important words, real emotion",
        emotion=0.9, pace=0.3, temp=0.9, pause=0.5, chunk=180, pitch=-1, speed=0.95),
    "Mysterious": dict(
        gemini="Say this in a low, hushed, mysterious male voice. Slow and suspenseful, with whispers, long pauses, and a haunting tone",
        emotion=0.75, pace=0.2, temp=0.75, pause=0.8, chunk=150, pitch=-2, speed=0.92),
    "Energetic": dict(
        gemini="Say this with high energy and genuine excitement like a hyped anime YouTuber, varied pitch, fast pace, emphasis on key words",
        emotion=0.95, pace=0.5, temp=0.95, pause=0.2, chunk=150, pitch=1, speed=1.1),
    "Romance": dict(
        gemini="Say this in a warm, soft, tender male voice, intimate and affectionate, gentle pace, with a slight smile in the voice",
        emotion=0.6, pace=0.35, temp=0.8, pause=0.5, chunk=200, pitch=-1, speed=0.95),
}

CHARACTERS = [
    ("Deep Narrator", "a deep, warm male audiobook narrator, steady and clear", 0.6, 0.3, 0.7, 0.5, 220, -3, 0.95),
    ("Mystery Man", "a low, slow, suspenseful male voice with long pauses", 0.75, 0.2, 0.75, 0.8, 150, -2, 0.92),
    ("Noir Detective", "a gritty 1940s male noir detective narrating in a tired, low voice", 0.5, 0.25, 0.7, 0.6, 180, -2.5, 0.93),
    ("Trailer God", "an epic male movie-trailer announcer, booming and intense", 1.0, 0.25, 0.8, 0.7, 130, -4, 0.9),
    ("Old Wizard", "a wise, ancient male wizard, slow and magical", 0.7, 0.25, 0.85, 0.6, 170, -1.5, 0.88),
    ("Wise Elder", "a calm grandfatherly male elder sharing wisdom", 0.55, 0.3, 0.75, 0.55, 200, -1, 0.9),
    ("Villain", "a smooth, menacing male villain, quiet and threatening", 0.9, 0.2, 0.85, 0.65, 150, -3, 0.92),
    ("Dark Lord", "a booming, terrifying male dark overlord", 1.0, 0.15, 0.8, 0.9, 120, -5, 0.85),
    ("Hero", "a confident, inspiring male hero", 0.85, 0.35, 0.85, 0.35, 170, -1, 1.0),
    ("News Anchor", "a neutral, professional male news anchor", 0.35, 0.6, 0.6, 0.2, 280, -1, 1.05),
    ("Documentary Sage", "a calm male nature-documentary narrator", 0.45, 0.35, 0.65, 0.4, 260, -1.5, 0.95),
    ("Radio DJ", "a smooth late-night male radio host", 0.8, 0.5, 0.9, 0.2, 200, -1, 1.1),
    ("Bedtime Dad", "a warm, gentle male dad reading a bedtime story", 0.55, 0.3, 0.75, 0.5, 200, -1, 0.9),
    ("Drill Sergeant", "a loud, commanding male drill sergeant", 1.1, 0.55, 0.9, 0.2, 100, -2, 1.1),
    ("Sports Commentator", "a fast, excited male sports commentator", 1.0, 0.6, 0.95, 0.15, 120, 0, 1.15),
    ("Anime Hero", "an energetic male anime protagonist", 0.95, 0.45, 0.95, 0.3, 150, 1, 1.05),
    ("Calm Teacher", "a patient, clear male teacher explaining", 0.4, 0.4, 0.65, 0.4, 240, 0, 0.95),
    ("Street Storyteller", "a casual, expressive male storyteller by a campfire", 0.8, 0.4, 0.9, 0.35, 180, -0.5, 1.0),
    ("Horror Whisper", "a creepy male whisper building slow dread", 0.85, 0.15, 0.85, 1.0, 110, -2, 0.85),
    ("Young Vlogger", "an upbeat young male YouTuber", 0.75, 0.5, 0.9, 0.2, 180, 1.5, 1.1),
]

for _n, _d, _e, _p, _t, _pa, _c, _pi, _s in CHARACTERS:
    BASE_STYLES[_n] = dict(
        gemini=f"Say this as {_d}. Expressive, natural delivery with real emotion",
        emotion=_e, pace=_p, temp=_t, pause=_pa, chunk=_c, pitch=_pi, speed=_s)

LOCAL_KEYS = ("emotion", "pace", "temp", "pause", "chunk", "pitch", "speed")
DEFAULT_STYLES = {k: v["gemini"] for k, v in BASE_STYLES.items()}
DEFAULT_LOCAL_STYLES = {k: {x: v[x] for x in LOCAL_KEYS} for k, v in BASE_STYLES.items()}


def load_config():
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg.setdefault("api_key", "")
    cfg.setdefault("output_dir", str(Path.home() / "Documents" / "VoiceStudio"))
    cfg.setdefault("engine", "gemini")
    cfg.setdefault("voice", GEMINI_VOICES[0])
    cfg["voice"] = next((v for v in GEMINI_VOICES if v.split(" ")[0] == str(cfg["voice"]).split(" ")[0]),
                        GEMINI_VOICES[0])
    cfg.setdefault("edge_voice", next(iter(EDGE_VOICES)))
    if cfg["edge_voice"] not in EDGE_VOICES:
        cfg["edge_voice"] = next(iter(EDGE_VOICES))
    cfg.setdefault("edge_hindi_voice", next(iter(EDGE_HINDI_VOICES)))
    if cfg["edge_hindi_voice"] not in EDGE_HINDI_VOICES:
        cfg["edge_hindi_voice"] = next(iter(EDGE_HINDI_VOICES))
    cfg.setdefault("language", next(iter(LANGS)))
    if cfg["language"] not in LANGS:
        cfg["language"] = next(iter(LANGS))
    cfg.setdefault("local_voice", "")
    cfg.setdefault("styles", dict(DEFAULT_STYLES))
    cfg.setdefault("local_styles", {k: dict(v) for k, v in DEFAULT_LOCAL_STYLES.items()})
    if cfg.get("version") != 2:
        for k, v in DEFAULT_STYLES.items():
            cfg["styles"].setdefault(k, v)
        for k, v in DEFAULT_LOCAL_STYLES.items():
            cfg["local_styles"].setdefault(k, dict(v))
        cfg["version"] = 2
    if not cfg["styles"]:
        cfg["styles"] = dict(DEFAULT_STYLES)
    if not cfg["local_styles"]:
        cfg["local_styles"] = {k: dict(v) for k, v in DEFAULT_LOCAL_STYLES.items()}
    cfg.setdefault("last_style", next(iter(cfg["styles"])))
    cfg.setdefault("last_local_style", next(iter(cfg["local_styles"])))
    cfg.setdefault("speed", 1.0)
    cfg.setdefault("pitch", 0.0)
    return cfg


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def saved_voices():
    if not VOICE_DIR.is_dir():
        return {}
    return {f.stem: f for f in sorted(VOICE_DIR.glob("*")) if f.suffix.lower() in AUDIO_EXT}


def split_text(text, limit=2500):
    chunks, cur = [], ""
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if len(cur) + len(para) + 1 > limit and cur:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{para}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def detect_lang(s):
    return "hi" if DEVANAGARI.search(s) else "en"


def split_by_lang(text, limit=250, mode="auto"):
    """Split text into (lang, chunk) pieces. In auto mode each sentence is tagged
    Hindi (contains Devanagari) or English, and neighbours of the same language
    are merged up to `limit` characters."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for s in SENTENCE_SPLIT.split(line):
            s = s.strip()
            if not s:
                continue
            lang = detect_lang(s) if mode == "auto" else mode
            if out and out[-1][0] == lang and len(out[-1][1]) + len(s) + 1 <= limit:
                out[-1] = (lang, f"{out[-1][1]} {s}")
            else:
                out.append((lang, s))
    return out


def synth(client, voice, style, text):
    from google.genai import types
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{style}:\n\n{text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    return resp.candidates[0].content.parts[0].inline_data.data


def time_stretch(pcm, speed):
    if abs(speed - 1.0) < 0.02 or not pcm:
        return pcm
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    N, Hs, tol = 1024, 512, 256
    Ha = Hs * speed
    win = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / N)).astype(np.float32)
    xp = np.concatenate([np.zeros(tol, np.float32), x, np.zeros(N + 2 * tol, np.float32)])
    n_frames = int(len(x) / Ha) + 1
    out = np.zeros(n_frames * Hs + N, np.float32)
    norm = np.zeros_like(out)
    prev = tol
    out[:N] += xp[prev:prev + N] * win
    norm[:N] += win
    end = N
    for k in range(1, n_frames):
        target = int(tol + k * Ha)
        nat = prev + Hs
        lo = target - tol
        if nat + N > len(xp) or lo + 2 * tol + N > len(xp):
            break
        ref = xp[nat:nat + N]
        region = xp[lo:lo + 2 * tol + N]
        best = lo + int(np.argmax(np.correlate(region, ref, "valid")))
        o = k * Hs
        out[o:o + N] += xp[best:best + N] * win
        norm[o:o + N] += win
        prev = best
        end = o + N
    norm[norm < 1e-3] = 1.0
    y = (out / norm)[:end]
    return np.clip(y, -32768, 32767).astype(np.int16).tobytes()


def process_audio(pcm, sr, pitch, speed):
    if abs(pitch) >= 0.05 and pcm:
        import librosa
        y = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=float(pitch))
        pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    return time_stretch(pcm, speed)


def write_wav(path, pcm, sr):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)


def import_voice(name, src):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", name.strip()) or "voice"
    VOICE_DIR.mkdir(exist_ok=True)
    target = VOICE_DIR / f"{safe}.wav"
    try:
        import librosa
        y, sr = librosa.load(str(src), sr=None, mono=True)
        pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
        write_wav(target, pcm, int(sr))
    except Exception:
        target = VOICE_DIR / f"{safe}{Path(src).suffix.lower()}"
        shutil.copy(src, target)
    return safe


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Studio")
        self.geometry("820x900")
        self.minsize(700, 660)
        self.cfg = load_config()
        self.busy = False
        self.pcm = None
        self.sr = GEMINI_SR
        self.gen_id = 0
        self.cache = None
        self.model = None
        self.model_device = None
        self.cpu_patched = False
        self.chunk_val = 220
        self.updaters = []
        self._build()
        self._on_engine()

    def _slider(self, parent, label, var, lo, hi, step, fmt):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=10, pady=2)
        ttk.Label(row, text=label, width=16).pack(side="left")
        lbl = tk.StringVar()

        def upd(*_):
            lbl.set(fmt.format(round(var.get() / step) * step))

        ttk.Scale(row, from_=lo, to=hi, variable=var, command=upd).pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=lbl, width=8).pack(side="left", padx=6)
        self.updaters.append(upd)
        upd()
        return row

    def _refresh_labels(self):
        for u in self.updaters:
            u()

    def _build(self):
        pad = {"padx": 10, "pady": 4}
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)
        bottom = ttk.Frame(root)
        bottom.pack(side="bottom", fill="x")

        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Engine:", width=16).pack(side="left")
        self.engine_var = tk.StringVar(value=self.cfg["engine"])
        ttk.Radiobutton(row, text="Gemini (online)", value="gemini", variable=self.engine_var,
                        command=self._on_engine).pack(side="left")
        ttk.Radiobutton(row, text="Local clone (Chatterbox)", value="local", variable=self.engine_var,
                        command=self._on_engine).pack(side="left", padx=14)
        ttk.Radiobutton(row, text="Edge voices (free)", value="edge", variable=self.engine_var,
                        command=self._on_engine).pack(side="left")

        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Language:", width=16).pack(side="left")
        self.lang_var = tk.StringVar(value=self.cfg["language"])
        ttk.Combobox(row, textvariable=self.lang_var, values=list(LANGS), state="readonly",
                     width=24).pack(side="left")
        ttk.Label(row, text="Auto = Devanagari sentences in Hindi, the rest in English").pack(side="left", padx=10)

        self.engine_area = ttk.Frame(root)
        self.engine_area.pack(fill="x")

        self.gem_frame = ttk.Frame(self.engine_area)
        row = ttk.Frame(self.gem_frame)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Gemini API key:", width=16).pack(side="left")
        self.key_var = tk.StringVar(value=self.cfg["api_key"])
        ttk.Entry(row, textvariable=self.key_var, show="*").pack(side="left", fill="x", expand=True)
        row = ttk.Frame(self.gem_frame)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Voice:", width=16).pack(side="left")
        self.voice_var = tk.StringVar(value=self.cfg["voice"])
        ttk.Combobox(row, textvariable=self.voice_var, values=GEMINI_VOICES, state="readonly",
                     width=30).pack(side="left")
        ttk.Label(self.gem_frame, text="Gemini detects Hindi or English from the text itself."
                  ).pack(anchor="w", padx=10)

        self.loc_frame = ttk.Frame(self.engine_area)
        row = ttk.Frame(self.loc_frame)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Custom voice:", width=16).pack(side="left")
        self.lvoice_var = tk.StringVar(value=self.cfg["local_voice"])
        self.lvoice_box = ttk.Combobox(row, textvariable=self.lvoice_var, state="readonly", width=24)
        self.lvoice_box.pack(side="left")
        ttk.Button(row, text="+ Add voice from file", command=self.add_voice).pack(side="left", padx=(10, 2))
        ttk.Button(row, text="Remove", command=self.remove_voice).pack(side="left", padx=2)
        ttk.Label(self.loc_frame, text="Tip: for Hindi, a Hindi voice sample gives the most natural accent."
                  ).pack(anchor="w", padx=10)

        self.edge_frame = ttk.Frame(self.engine_area)
        row = ttk.Frame(self.edge_frame)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="English voice:", width=16).pack(side="left")
        self.edge_var = tk.StringVar(value=self.cfg["edge_voice"])
        ttk.Combobox(row, textvariable=self.edge_var, values=list(EDGE_VOICES.keys()), state="readonly",
                     width=30).pack(side="left")
        row = ttk.Frame(self.edge_frame)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Hindi voice:", width=16).pack(side="left")
        self.edge_hi_var = tk.StringVar(value=self.cfg["edge_hindi_voice"])
        ttk.Combobox(row, textvariable=self.edge_hi_var, values=list(EDGE_HINDI_VOICES.keys()),
                     state="readonly", width=30).pack(side="left")
        ttk.Label(self.edge_frame, text="No API key or sample needed. Needs internet. Use Pitch and Speed below to shape the voice."
                  ).pack(anchor="w", padx=10)

        self.style_area = ttk.Frame(root)
        self.style_area.pack(fill="x")
        row = ttk.Frame(self.style_area)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Style:", width=16).pack(side="left")
        self.style_var = tk.StringVar()
        self.style_box = ttk.Combobox(row, textvariable=self.style_var, state="readonly", width=24)
        self.style_box.pack(side="left")
        self.style_box.bind("<<ComboboxSelected>>", lambda e: self._on_style_change())
        ttk.Button(row, text="+ New style", command=self.add_style).pack(side="left", padx=(10, 2))
        ttk.Button(row, text="Save changes", command=self.save_style).pack(side="left", padx=2)
        ttk.Button(row, text="Delete", command=self.delete_style).pack(side="left", padx=2)

        self.panel = ttk.Frame(self.style_area)
        self.panel.pack(fill="x")

        self.gem_panel = ttk.Frame(self.panel)
        ttk.Label(self.gem_panel, text="Style instruction (edit, then Save changes, or + New style to keep as a new option):"
                  ).pack(anchor="w", padx=10)
        self.instr = tk.Text(self.gem_panel, height=4, wrap="word")
        self.instr.pack(fill="x", padx=10, pady=(2, 6))

        self.loc_panel = ttk.Frame(self.panel)
        self.emo_var = tk.DoubleVar(value=0.7)
        self.pace_var = tk.DoubleVar(value=0.3)
        self.temp_var = tk.DoubleVar(value=0.8)
        self.pause_var = tk.DoubleVar(value=0.4)
        self._slider(self.loc_panel, "Emotion:", self.emo_var, 0.2, 1.4, 0.05, "{:.2f}")
        self._slider(self.loc_panel, "Pace (low=slow):", self.pace_var, 0.05, 0.8, 0.05, "{:.2f}")
        self._slider(self.loc_panel, "Randomness:", self.temp_var, 0.4, 1.2, 0.05, "{:.2f}")
        self._slider(self.loc_panel, "Pause between:", self.pause_var, 0.1, 1.2, 0.05, "{:.2f}s")

        ttk.Label(root, text="Paste your text here (Hindi, English, or both):").pack(anchor="w", padx=10)
        frame = ttk.Frame(root)
        frame.pack(fill="both", expand=True, padx=10, pady=(2, 6))
        self.text = tk.Text(frame, wrap="word", undo=True, height=8)
        sb = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.pitch_var = tk.DoubleVar(value=float(self.cfg["pitch"]))
        row = self._slider(bottom, "Pitch:", self.pitch_var, -6, 6, 0.5, "{:+.1f} st")
        ttk.Button(row, text="Reset", width=6, command=lambda: self._set_var(self.pitch_var, 0.0)).pack(side="left")

        self.speed_var = tk.DoubleVar(value=float(self.cfg["speed"]))
        row = self._slider(bottom, "Speed:", self.speed_var, 0.5, 1.5, 0.05, "{:.2f}x")
        ttk.Button(row, text="Reset", width=6, command=lambda: self._set_var(self.speed_var, 1.0)).pack(side="left")

        row = ttk.Frame(bottom)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Save folder:", width=16).pack(side="left")
        self.dir_var = tk.StringVar(value=self.cfg["output_dir"])
        ttk.Entry(row, textvariable=self.dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse...", command=self.browse).pack(side="left", padx=(6, 0))

        row = ttk.Frame(bottom)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="File name:", width=16).pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.name_var).pack(side="left", fill="x", expand=True)
        ttk.Label(row, text=".wav (blank = auto)").pack(side="left", padx=6)

        row = ttk.Frame(bottom)
        row.pack(fill="x", padx=10, pady=8)
        self.gen_btn = ttk.Button(row, text="1. Generate", command=self.generate)
        self.gen_btn.pack(side="left")
        self.play_btn = ttk.Button(row, text="2. Play", command=self.play, state="disabled")
        self.play_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(row, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left")
        self.save_btn = ttk.Button(row, text="3. Save", command=self.save_audio, state="disabled")
        self.save_btn.pack(side="left", padx=6)
        ttk.Button(row, text="Open folder", command=self.open_folder).pack(side="left", padx=6)

        self.status = tk.StringVar(value="Ready. Paste text and press Generate.")
        ttk.Label(bottom, textvariable=self.status, foreground="#555", wraplength=760).pack(anchor="w", padx=10)

    def _set_var(self, var, v):
        var.set(v)
        self._refresh_labels()

    def _speed(self):
        return round(self.speed_var.get() * 20) / 20

    def _pitch(self):
        return round(self.pitch_var.get() * 2) / 2

    def _lang_mode(self):
        return LANGS.get(self.lang_var.get(), "auto")

    def _is_local(self):
        return self.engine_var.get() == "local"

    def _styles(self):
        return self.cfg["local_styles"] if self._is_local() else self.cfg["styles"]

    def _last_key(self):
        return "last_local_style" if self._is_local() else "last_style"

    def _on_engine(self):
        for f in (self.gem_frame, self.loc_frame, self.edge_frame, self.gem_panel, self.loc_panel):
            f.pack_forget()
        self.style_area.pack_forget()
        if self.engine_var.get() == "edge":
            self.edge_frame.pack(fill="x")
            return
        self.style_area.pack(fill="x", after=self.engine_area)
        if self._is_local():
            self.loc_frame.pack(fill="x")
            self.loc_panel.pack(fill="x")
            self._refresh_voices()
        else:
            self.gem_frame.pack(fill="x")
            self.gem_panel.pack(fill="x")
        self._refresh_styles(select=self.cfg[self._last_key()])

    def _refresh_voices(self, select=None):
        names = list(saved_voices().keys())
        self.lvoice_box["values"] = names
        pick = select or self.lvoice_var.get()
        if pick not in names:
            pick = names[0] if names else ""
        self.lvoice_var.set(pick)

    def add_voice(self):
        f = filedialog.askopenfilename(
            title="Choose a voice sample (clean, 10-30 seconds)",
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg"), ("All files", "*.*")])
        if not f:
            return
        name = simpledialog.askstring("Voice name", "Name for this custom voice (e.g. deep_man):",
                                      initialvalue=Path(f).stem, parent=self)
        if not name or not name.strip():
            return
        try:
            safe = import_voice(name, f)
        except Exception as e:
            return messagebox.showerror("Error", str(e))
        self._refresh_voices(select=safe)
        self.status.set(f"Custom voice '{safe}' added.")

    def remove_voice(self):
        name = self.lvoice_var.get()
        path = saved_voices().get(name)
        if not path:
            return
        if messagebox.askyesno("Remove", f"Remove custom voice '{name}'?"):
            try:
                path.unlink()
            except Exception as e:
                return messagebox.showerror("Error", str(e))
            self._refresh_voices()

    def _refresh_styles(self, select=None):
        names = list(self._styles().keys())
        self.style_box["values"] = names
        if select not in names:
            select = names[0]
        self.style_var.set(select)
        self._on_style_change()

    def _on_style_change(self):
        name = self.style_var.get()
        if self._is_local():
            p = self.cfg["local_styles"].get(name)
            if not p:
                return
            self.emo_var.set(p["emotion"])
            self.pace_var.set(p["pace"])
            self.temp_var.set(p["temp"])
            self.pause_var.set(p["pause"])
            self.chunk_val = int(p.get("chunk", 220))
            self.pitch_var.set(p.get("pitch", 0))
            self.speed_var.set(round(p.get("speed", 1.0) * 20) / 20)
            self._refresh_labels()
        else:
            self.instr.delete("1.0", "end")
            self.instr.insert("1.0", self.cfg["styles"].get(name, ""))

    def _local_params(self):
        return dict(emotion=round(self.emo_var.get(), 2), pace=round(self.pace_var.get(), 2),
                    temp=round(self.temp_var.get(), 2), pause=round(self.pause_var.get(), 2),
                    chunk=self.chunk_val, pitch=self._pitch(), speed=self._speed())

    def _current_style_value(self):
        if self._is_local():
            return self._local_params()
        return self.instr.get("1.0", "end").strip()

    def add_style(self):
        name = simpledialog.askstring("New style", "Name for the new style (e.g. Horror):", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._styles() and not messagebox.askyesno(
                "Exists", f"'{name}' already exists. Overwrite it?"):
            return
        value = self._current_style_value()
        if not value:
            return messagebox.showwarning("Empty", "Write the style instruction in the box first.")
        self._styles()[name] = value
        save_config(self.cfg)
        self._refresh_styles(select=name)

    def save_style(self):
        name = self.style_var.get()
        value = self._current_style_value()
        if not name or not value:
            return
        self._styles()[name] = value
        save_config(self.cfg)
        self.status.set(f"Saved changes to '{name}'.")

    def delete_style(self):
        name = self.style_var.get()
        if len(self._styles()) <= 1:
            return messagebox.showinfo("Keep one", "You need at least one style.")
        if messagebox.askyesno("Delete", f"Delete style '{name}'?"):
            del self._styles()[name]
            save_config(self.cfg)
            self._refresh_styles()

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()))
        if d:
            self.dir_var.set(d)

    def open_folder(self):
        d = Path(self.dir_var.get())
        d.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(d)
        else:
            messagebox.showinfo("Folder", str(d))

    def generate(self):
        if self.busy:
            return
        text = self.text.get("1.0", "end").strip()
        if not text:
            return messagebox.showwarning("No text", "Paste some text to speak.")
        engine = self.engine_var.get()
        mode = self._lang_mode()
        if engine == "edge":
            args = (EDGE_VOICES[self.edge_var.get()], EDGE_HINDI_VOICES[self.edge_hi_var.get()], text, mode)
        elif engine == "local":
            name = self.lvoice_var.get()
            path = saved_voices().get(name)
            if not path:
                return messagebox.showwarning("Voice", "Add a custom voice from a file first.")
            args = (str(path), self._local_params(), text, mode)
        else:
            key = self.key_var.get().strip()
            if not key:
                return messagebox.showwarning("API key", "Paste your Gemini API key first.")
            args = (key, self.voice_var.get().split(" ")[0], self.instr.get("1.0", "end").strip(), text)

        self.cfg.update(engine=self.engine_var.get(), api_key=self.key_var.get().strip(),
                        voice=self.voice_var.get(), local_voice=self.lvoice_var.get(),
                        edge_voice=self.edge_var.get(), edge_hindi_voice=self.edge_hi_var.get(),
                        language=self.lang_var.get(),
                        output_dir=self.dir_var.get().strip(), speed=self._speed(), pitch=self._pitch())
        self.cfg[self._last_key()] = self.style_var.get()
        save_config(self.cfg)

        self.stop()
        self.busy = True
        for b in (self.gen_btn, self.play_btn, self.save_btn):
            b.state(["disabled"])
        threading.Thread(target=self._worker, args=(engine, args), daemon=True).start()

    def _set_status(self, msg):
        self.after(0, lambda: self.status.set(msg))

    def _run_gemini(self, key, voice, style, text):
        from google import genai
        client = genai.Client(api_key=key)
        chunks = split_text(text)
        pcm = b""
        for i, chunk in enumerate(chunks, 1):
            self._set_status(f"Generating part {i}/{len(chunks)}... (please wait)")
            pcm += synth(client, voice, style, chunk)
            if i < len(chunks):
                self._set_status(f"Part {i}/{len(chunks)} done. Waiting for free-tier rate limit...")
                time.sleep(31)
        return pcm, GEMINI_SR

    def _load_local_model(self, device):
        import torch
        if self.model is not None and self.model_device == device:
            return self.model
        self._set_status(f"Loading multilingual model on {device} (first run downloads several GB)...")
        if device != "cuda" and not self.cpu_patched:
            orig = torch.load

            def patched(*a, **k):
                k.setdefault("map_location", torch.device("cpu"))
                return orig(*a, **k)

            torch.load = patched
            self.cpu_patched = True
        try:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except ImportError:
            raise RuntimeError(
                "Multilingual Chatterbox not found.\nUpgrade with:\npip install -U chatterbox-tts")
        self.model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        self.model_device = device
        return self.model

    def _run_local(self, voice_path, p, text, mode):
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = self._load_local_model(device)
        chunks = split_by_lang(text, int(p["chunk"]), mode)
        gap = np.zeros(int(p["pause"] * model.sr), np.int16)
        parts = []
        for i, (lang, chunk) in enumerate(chunks, 1):
            label = "Hindi" if lang == "hi" else "English"
            self._set_status(f"Generating part {i}/{len(chunks)} ({label}) on {device}..."
                             + (" CPU is slow, be patient." if device == "cpu" else ""))
            wav = model.generate(chunk, language_id=lang, audio_prompt_path=voice_path,
                                 exaggeration=p["emotion"], cfg_weight=p["pace"],
                                 temperature=p["temp"])
            a = wav.squeeze().detach().cpu().numpy()
            parts.append((np.clip(a, -1, 1) * 32767).astype(np.int16))
            parts.append(gap)
        if len(parts) > 1:
            parts = parts[:-1]
        return np.concatenate(parts).tobytes(), int(model.sr)

    def _run_edge(self, en_voice, hi_voice, text, mode):
        import asyncio
        import edge_tts
        import librosa
        parts = []
        chunks = split_by_lang(text, 1500, mode)
        for i, (lang, chunk) in enumerate(chunks, 1):
            self._set_status(f"Generating part {i}/{len(chunks)} ({'Hindi' if lang == 'hi' else 'English'})...")
            voice_id = hi_voice if lang == "hi" else en_voice
            tmp = Path(tempfile.gettempdir()) / f"voice_studio_edge_{i}.mp3"
            asyncio.run(edge_tts.Communicate(chunk, voice_id).save(str(tmp)))
            y, _ = librosa.load(str(tmp), sr=GEMINI_SR, mono=True)
            parts.append((np.clip(y, -1, 1) * 32767).astype(np.int16))
            tmp.unlink(missing_ok=True)
        return np.concatenate(parts).tobytes(), GEMINI_SR

    def _worker(self, engine, args):
        try:
            runner = {"gemini": self._run_gemini, "local": self._run_local, "edge": self._run_edge}[engine]
            pcm, sr = runner(*args)
            self.pcm, self.sr = pcm, sr
            self.gen_id += 1
            self.cache = None
            self._set_status("Done! Press Play to listen. Change Pitch or Speed anytime, then press Save.")
        except Exception as e:
            self._set_status("Error.")
            self.after(0, lambda err=e: self._error(err))
        finally:
            self.busy = False

            def restore():
                self.gen_btn.state(["!disabled"])
                if self.pcm:
                    self.play_btn.state(["!disabled"])
                    self.save_btn.state(["!disabled"])

            self.after(0, restore)

    def _error(self, err):
        if isinstance(err, ModuleNotFoundError) and err.name:
            top = err.name.split(".")[0]
            msg = f"Missing package: {top}\nInstall it with:\npip install {PIP_NAMES.get(top, top)}"
        else:
            msg = str(err)
        self.status.set("Error.")
        messagebox.showerror("Error", msg)

    def _render(self, done):
        pitch, speed = self._pitch(), self._speed()
        key = (self.gen_id, pitch, speed)
        if self.cache and self.cache[0] == key:
            return done(self.cache[1])
        self.status.set("Processing audio...")
        pcm, sr = self.pcm, self.sr

        def work():
            try:
                out = process_audio(pcm, sr, pitch, speed)
                self.cache = (key, out)
                self.after(0, lambda: done(out))
            except Exception as e:
                self.after(0, lambda err=e: self._error(err))

        threading.Thread(target=work, daemon=True).start()

    def play(self):
        if not self.pcm:
            return
        if winsound is None:
            return messagebox.showinfo("Not supported", "Preview playback works on Windows only. Use Save instead.")
        self.stop()

        def done(out):
            try:
                write_wav(PREVIEW_PATH, out, self.sr)
                winsound.PlaySound(str(PREVIEW_PATH), winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.stop_btn.state(["!disabled"])
                self.status.set(f"Playing: pitch {self._pitch():+.1f}, speed {self._speed():.2f}x ...")
            except Exception as e:
                messagebox.showerror("Playback error", str(e))

        self._render(done)

    def stop(self):
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        self.stop_btn.state(["disabled"])

    def save_audio(self):
        if not self.pcm:
            return
        out_dir = Path(self.dir_var.get().strip())
        name = self.name_var.get().strip() or "voice_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = "".join(c for c in name if c not in '\\/:*?"<>|')
        if name.lower().endswith(".wav"):
            name = name[:-4]
        path = out_dir / f"{name}.wav"
        n = 2
        while path.exists():
            path = out_dir / f"{name}_{n}.wav"
            n += 1

        def done(out):
            try:
                write_wav(path, out, self.sr)
                self.cfg.update(output_dir=str(out_dir), speed=self._speed(), pitch=self._pitch())
                save_config(self.cfg)
                self.status.set(f"Saved: {path}")
                messagebox.showinfo("Saved", f"Saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Save error", str(e))

        self._render(done)


if __name__ == "__main__":
    App().mainloop()