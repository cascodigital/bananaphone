#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import threading
import time
import tkinter as tk
import traceback
import audioop
import json
import urllib.error
import urllib.request
import uuid
import wave
from io import BytesIO

import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel

APP_NAME = "Bananafone"
APP_VERSION = "1.3"
CPU_THREADS = min(os.cpu_count() or 4, 8)
LOG_DIR = os.path.expanduser("~/.local/state/bananafone")
LOG_FILE = os.path.join(LOG_DIR, "bananafone.log")
CONFIG_DIR = os.path.expanduser("~/.config/bananafone")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
DEFAULT_OPENAI_MODEL = os.environ.get("BANANAFONE_OPENAI_MODEL", "gpt-4o-mini-transcribe")
DEFAULT_OPENAI_TEXT_MODEL = os.environ.get("BANANAFONE_OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIPT_URL = os.environ.get(
    "BANANAFONE_OPENAI_TRANSCRIPT_URL",
    "https://api.openai.com/v1/audio/transcriptions",
)
OPENAI_CHAT_URL = os.environ.get(
    "BANANAFONE_OPENAI_CHAT_URL",
    "https://api.openai.com/v1/chat/completions",
)
OPENAI_KEY_FILE = os.environ.get(
    "BANANAFONE_OPENAI_KEY_FILE",
    "/home/aristofeles/ai/config/ai-keys.md",
)
OPENAI_KEY_FILES = [
    OPENAI_KEY_FILE,
    os.path.expanduser("~/ai/config/ai-keys.md"),
    os.path.expanduser("~/.config/bananafone/ai-keys.md"),
]
AUTO_STOP_SILENCE_SECONDS = float(os.environ.get("BANANAFONE_AUTO_STOP_SILENCE_SECONDS", "4.0"))
MIN_SPEECH_SECONDS = float(os.environ.get("BANANAFONE_MIN_SPEECH_SECONDS", "0.35"))
SILENCE_RMS_MULTIPLIER = float(os.environ.get("BANANAFONE_SILENCE_RMS_MULTIPLIER", "1.35"))

MODES = {
    "fast": {
        "label": "Fast",
        "button_color": "#F59E0B",
        "text_color": "black",
        "status": "Rapido para texto livre. Menos preciso em numeros.",
        "model_name": "small",
        "ambient_duration": 0.30,
        "chunk_seconds": 0.60,
        "transcribe_kwargs": {
            "language": "pt",
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": False,
            "without_timestamps": True,
        },
    },
    "normal": {
        "label": "Normal",
        "button_color": "#10B981",
        "text_color": "black",
        "status": "Equilibrio entre velocidade e entendimento.",
        "model_name": "medium",
        "ambient_duration": 0.45,
        "chunk_seconds": 0.75,
        "transcribe_kwargs": {
            "language": "pt",
            "beam_size": 2,
            "best_of": 2,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": True,
            "without_timestamps": True,
        },
    },
    "slow": {
        "label": "API",
        "button_color": "#2563EB",
        "text_color": "white",
        "status": "Mais preciso via nuvem para horario, numeros e frases chatas.",
        "backend": "openai",
        "api_model": DEFAULT_OPENAI_MODEL,
        "ambient_duration": 0.75,
        "prompt": "Transcreva em pt-BR com foco em fidelidade de numeros, horarios, nomes e termos tecnicos.",
    },
}

OUTPUT_TARGETS = {
    "en": {
        "label": "EN",
        "status": "Saida em ingles natural.",
        "button_color": "#E5E7EB",
        "text_color": "black",
    },
    "pt-BR": {
        "label": "PT-BR",
        "status": "Saida em portugues brasileiro fiel.",
        "button_color": "#E5E7EB",
        "text_color": "black",
    },
    "pt-PT": {
        "label": "PT-PT",
        "status": "Saida adaptada para portugues de Portugal.",
        "button_color": "#E5E7EB",
        "text_color": "black",
    },
}

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)
log_fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.dup2(log_fd, 2)


class DictationApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("520x430")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111827")
        self.root.eval("tk::PlaceWindow . center")

        self.settings = self.load_settings()
        self.default_mode_key = self.settings.get("default_mode", "slow")
        self.default_output_target = self.settings.get("default_output", "en")
        self.mode_key = self.default_mode_key
        self.mode = MODES[self.mode_key]
        self.model = None
        self.model_key_loaded = None
        self.model_loading = False
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.source = None
        self.audio_chunks = []
        self.is_recording = False
        self.stop_requested = False
        self.recording_thread = None
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.hotkey_recording = False
        self.transcription_thread = None
        self.refreshing_models = False
        self.energy_floor = 0
        self.capture_sample_rate = 16000
        self.capture_sample_width = 2
        self.output_target = self.default_output_target

        self.build_ui()
        self.setup_bindings()
        self.refresh_cache_status()
        self.set_output_target(self.output_target, update_status=False)
        self.select_mode(self.mode_key)

    def build_ui(self):
        self.title_label = tk.Label(
            self.root,
            text="BANANAFONE",
            font=("Helvetica", 20, "bold"),
            fg="#F9FAFB",
            bg="#111827",
        )
        self.title_label.pack(pady=(16, 6))

        self.status_label = tk.Label(
            self.root,
            text="Carregando modo API...",
            font=("Helvetica", 12),
            fg="#D1D5DB",
            bg="#111827",
            wraplength=470,
        )
        self.status_label.pack(pady=(0, 10))

        self.selector_frame = tk.Frame(self.root, bg="#111827")
        self.selector_frame.pack(pady=(0, 10))

        self.mode_buttons = {}
        for column, mode_key in enumerate(("fast", "normal", "slow")):
            mode = MODES[mode_key]
            button = tk.Button(
                self.selector_frame,
                text=mode["label"],
                font=("Helvetica", 13, "bold"),
                width=11,
                bg=mode["button_color"],
                fg=mode["text_color"],
                command=lambda key=mode_key: self.select_mode(key),
            )
            button.grid(row=0, column=column, padx=6, pady=4)
            self.mode_buttons[mode_key] = button

        self.output_frame = tk.Frame(self.root, bg="#111827")
        self.output_frame.pack(pady=(0, 10))

        self.output_buttons = {}
        for column, target_key in enumerate(("en", "pt-BR", "pt-PT")):
            target = OUTPUT_TARGETS[target_key]
            button = tk.Button(
                self.output_frame,
                text=target["label"],
                font=("Helvetica", 11, "bold"),
                width=8,
                bg=target["button_color"],
                fg=target["text_color"],
                command=lambda key=target_key: self.set_output_target(key),
            )
            button.grid(row=0, column=column, padx=5, pady=2)
            self.output_buttons[target_key] = button

        self.tools_frame = tk.Frame(self.root, bg="#111827")
        self.tools_frame.pack(pady=(0, 8))

        self.refresh_button = tk.Button(
            self.tools_frame,
            text="Baixar / Atualizar modelos",
            font=("Helvetica", 10, "bold"),
            bg="#E5E7EB",
            fg="black",
            command=self.refresh_models,
        )
        self.refresh_button.grid(row=0, column=0, padx=6)

        self.cache_label = tk.Label(
            self.tools_frame,
            text="Modelos: verificando...",
            font=("Helvetica", 9),
            fg="#9CA3AF",
            bg="#111827",
        )
        self.cache_label.grid(row=0, column=1, padx=6)

        self.defaults_frame = tk.Frame(self.root, bg="#111827")
        self.defaults_frame.pack(pady=(0, 8))

        self.save_defaults_button = tk.Button(
            self.defaults_frame,
            text="Tornar atual o padrao",
            font=("Helvetica", 10, "bold"),
            bg="#D1FAE5",
            fg="black",
            command=self.save_current_as_default,
        )
        self.save_defaults_button.grid(row=0, column=0, padx=6)

        self.defaults_label = tk.Label(
            self.defaults_frame,
            text="Padrao: carregando...",
            font=("Helvetica", 9),
            fg="#9CA3AF",
            bg="#111827",
        )
        self.defaults_label.grid(row=0, column=1, padx=6)

        self.mode_label = tk.Label(
            self.root,
            text="Clique para falar. Para sozinho apos silencio. Ctrl+Shift continua no modo segurar.",
            font=("Helvetica", 10),
            fg="#9CA3AF",
            bg="#111827",
            wraplength=470,
        )
        self.mode_label.pack(pady=(0, 12))

        self.hold_button = tk.Button(
            self.root,
            text="PRESSIONE PARA FALAR\nPara sozinho no silencio",
            font=("Helvetica", 15, "bold"),
            width=24,
            height=3,
            bg="#374151",
            fg="#F9FAFB",
            relief=tk.RAISED,
            justify=tk.CENTER,
            command=self.on_main_button_click,
        )
        self.hold_button.pack(pady=(0, 12))

        self.result_text = tk.Text(
            self.root,
            height=7,
            width=56,
            font=("Helvetica", 10),
            bg="#1F2937",
            fg="#F9FAFB",
            state=tk.DISABLED,
        )
        self.result_text.pack(pady=(0, 8))

    def setup_bindings(self):
        self.root.bind_all("<KeyPress-Control_L>", self.on_ctrl_press)
        self.root.bind_all("<KeyRelease-Control_L>", self.on_ctrl_release)
        self.root.bind_all("<KeyPress-Control_R>", self.on_ctrl_press)
        self.root.bind_all("<KeyRelease-Control_R>", self.on_ctrl_release)
        self.root.bind_all("<KeyPress-Shift_L>", self.on_shift_press)
        self.root.bind_all("<KeyRelease-Shift_L>", self.on_shift_release)
        self.root.bind_all("<KeyPress-Shift_R>", self.on_shift_press)
        self.root.bind_all("<KeyRelease-Shift_R>", self.on_shift_release)

    def update_status(self, text, color="#F9FAFB"):
        self.status_label.config(text=text, fg=color)

    def set_mode_button_states(self):
        for key, button in self.mode_buttons.items():
            relief = tk.SUNKEN if key == self.mode_key else tk.RAISED
            button.config(
                relief=relief,
                state=tk.NORMAL if not (self.is_recording or self.model_loading or self.refreshing_models) else tk.DISABLED,
            )
        for key, button in self.output_buttons.items():
            relief = tk.SUNKEN if key == self.output_target else tk.RAISED
            button.config(
                relief=relief,
                state=tk.NORMAL if not (self.is_recording or self.model_loading or self.refreshing_models) else tk.DISABLED,
            )
        self.refresh_button.config(
            state=tk.DISABLED if self.is_recording or self.model_loading or self.refreshing_models else tk.NORMAL
        )
        self.save_defaults_button.config(
            state=tk.DISABLED if self.is_recording or self.model_loading or self.refreshing_models else tk.NORMAL
        )

    def set_hold_button_idle(self):
        self.hold_button.config(
            text="PRESSIONE PARA FALAR\nPara sozinho no silencio",
            bg="#374151",
            activebackground="#4B5563",
            state=tk.NORMAL if not self.model_loading else tk.DISABLED,
        )

    def set_hold_button_recording(self):
        self.hold_button.config(
            text="FALANDO...\nCLIQUE PARA PARAR",
            bg="#DC2626",
            activebackground="#EF4444",
            state=tk.NORMAL,
        )

    def set_result_text(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def select_mode(self, mode_key):
        if self.is_recording or self.model_loading:
            return
        self.mode_key = mode_key
        self.mode = MODES[mode_key]
        self.root.title(f"{APP_NAME} {APP_VERSION} - {self.mode['label']}")
        self.mode_label.config(text=self.mode["status"])
        self.refresh_defaults_label()
        self.set_mode_button_states()
        self.ensure_model_loaded_async(mode_key)

    def set_output_target(self, target_key, update_status=True):
        if self.is_recording or self.model_loading or target_key not in OUTPUT_TARGETS:
            return
        self.output_target = target_key
        target = OUTPUT_TARGETS[target_key]
        if update_status:
            self.mode_label.config(text=target["status"])
        self.refresh_defaults_label()
        self.set_mode_button_states()

    def refresh_defaults_label(self):
        default_mode_label = MODES.get(self.default_mode_key, MODES["slow"])["label"]
        default_output_label = OUTPUT_TARGETS.get(self.default_output_target, OUTPUT_TARGETS["en"])["label"]
        self.defaults_label.config(text=f"Padrao: {default_mode_label} + {default_output_label}")

    def load_settings(self):
        if not os.path.isfile(SETTINGS_FILE):
            return {}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
                settings = json.load(handle)
        except Exception:
            return {}

        default_mode = settings.get("default_mode", "slow")
        default_output = settings.get("default_output", "en")
        if default_mode not in MODES:
            default_mode = "slow"
        if default_output not in OUTPUT_TARGETS:
            default_output = "en"
        return {
            "default_mode": default_mode,
            "default_output": default_output,
        }

    def write_settings(self):
        settings = {
            "default_mode": self.default_mode_key,
            "default_output": self.default_output_target,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)

    def save_current_as_default(self):
        self.default_mode_key = self.mode_key
        self.default_output_target = self.output_target
        self.write_settings()
        self.refresh_defaults_label()
        self.update_status(
            f"Padrao salvo: {self.mode['label']} + {OUTPUT_TARGETS[self.output_target]['label']}",
            "#34D399",
        )

    def ensure_model_loaded_async(self, mode_key):
        if self.model_key_loaded == mode_key and self.model is not None:
            self.update_status(f"Modo {self.mode['label']} pronto.", "#34D399")
            self.set_hold_button_idle()
            self.refresh_cache_status()
            return

        self.model_loading = True
        self.update_status(f"Carregando modo {MODES[mode_key]['label']}...", "#FBBF24")
        self.hold_button.config(text="CARREGANDO...\nsofrimento local", bg="#6B7280", state=tk.DISABLED)
        self.set_mode_button_states()
        threading.Thread(target=self.load_mode_resources, args=(mode_key,), daemon=True).start()

    def load_mode_resources(self, mode_key):
        try:
            mode = MODES[mode_key]
            started = time.time()
            source = sr.Microphone()
            with source as mic_source:
                self.root.after(0, self.update_status, "Calibrando ruido ambiente...", "#FBBF24")
                self.recognizer.adjust_for_ambient_noise(
                    mic_source,
                    duration=mode["ambient_duration"],
                )
                self.energy_floor = self.recognizer.energy_threshold

            if mode.get("backend") == "openai":
                self.require_openai_key()
                model = {"backend": "openai", "api_model": mode["api_model"]}
            else:
                model = WhisperModel(
                    mode["model_name"],
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=CPU_THREADS,
                    num_workers=1,
                )

            self.model = model
            self.source = source
            self.model_key_loaded = mode_key
            elapsed = time.time() - started
            self.root.after(0, self.finish_loading_mode, mode_key, elapsed)
        except Exception as exc:
            self.root.after(0, self.fail_loading_mode, str(exc))

    def finish_loading_mode(self, mode_key, elapsed):
        self.model_loading = False
        self.mode_key = mode_key
        self.mode = MODES[mode_key]
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.refresh_cache_status()
        self.update_status(f"Modo {self.mode['label']} pronto em {elapsed:.1f}s.", "#34D399")

    def fail_loading_mode(self, error_text):
        self.model_loading = False
        self.set_mode_button_states()
        self.hold_button.config(text="ERRO AO CARREGAR\nverifique o log", bg="#7F1D1D", state=tk.DISABLED)
        self.update_status(f"Erro ao carregar: {error_text}", "#F87171")

    def on_main_button_click(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def on_ctrl_press(self, _event):
        self.ctrl_pressed = True
        self.maybe_start_hotkey_recording()

    def on_ctrl_release(self, _event):
        self.ctrl_pressed = False
        self.maybe_stop_hotkey_recording()

    def on_shift_press(self, _event):
        self.shift_pressed = True
        self.maybe_start_hotkey_recording()

    def on_shift_release(self, _event):
        self.shift_pressed = False
        self.maybe_stop_hotkey_recording()

    def maybe_start_hotkey_recording(self):
        if self.ctrl_pressed and self.shift_pressed and not self.hotkey_recording:
            self.hotkey_recording = True
            self.start_recording()

    def maybe_stop_hotkey_recording(self):
        if self.hotkey_recording and not (self.ctrl_pressed and self.shift_pressed):
            self.hotkey_recording = False
            self.stop_recording()

    def start_recording(self):
        if self.is_recording or self.model_loading or self.model is None or self.source is None:
            return

        self.audio_chunks = []
        self.is_recording = True
        self.stop_requested = False
        self.set_mode_button_states()
        self.set_hold_button_recording()
        self.update_status(
            f"Gravando em {self.mode['label']}. Para sozinho apos {AUTO_STOP_SILENCE_SECONDS:.0f}s de silencio.",
            "#34D399",
        )
        self.recording_thread = threading.Thread(target=self.capture_audio_loop, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_requested = True
        self.hotkey_recording = False

        self.hold_button.config(text="TRANSCREVENDO...", bg="#1D4ED8", state=tk.DISABLED)
        self.update_status(f"Transcrevendo com modo {self.mode['label']}...", "#60A5FA")
        self.transcription_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.transcription_thread.start()

    def capture_audio_loop(self):
        try:
            with self.source as mic_source:
                sample_rate = mic_source.SAMPLE_RATE
                sample_width = mic_source.SAMPLE_WIDTH
                chunk_size = mic_source.CHUNK
                self.capture_sample_rate = sample_rate
                self.capture_sample_width = sample_width
                silence_deadline = None
                speech_frames = 0

                while self.is_recording and not self.stop_requested:
                    chunk = mic_source.stream.read(chunk_size)
                    self.audio_chunks.append(chunk)

                    rms = audioop.rms(chunk, sample_width)
                    threshold = max(self.energy_floor * SILENCE_RMS_MULTIPLIER, 120)

                    if rms >= threshold:
                        speech_frames += 1
                        silence_deadline = time.time() + AUTO_STOP_SILENCE_SECONDS
                    elif speech_frames > 0 and silence_deadline and time.time() >= silence_deadline:
                        self.root.after(0, self.stop_recording)
                        return

            min_chunks = max(1, int((sample_rate * MIN_SPEECH_SECONDS) / chunk_size))
            if speech_frames < min_chunks:
                self.audio_chunks = []
        except Exception as exc:
            self.root.after(0, self.handle_capture_failure, f"Erro de captura: {str(exc)[:60]}")

    def process_audio(self):
        if not self.audio_chunks:
            self.root.after(0, self.after_no_audio)
            return

        try:
            raw_data = b"".join(self.audio_chunks)
            audio = sr.AudioData(raw_data, self.capture_sample_rate, self.capture_sample_width)
            started = time.time()
            audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            if self.mode.get("backend") == "openai":
                text, language_probability = self.transcribe_with_openai(audio_data)
            else:
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                segments, info = self.model.transcribe(audio_np, **self.mode["transcribe_kwargs"])
                text = " ".join(segment.text.strip() for segment in segments).strip()
                language_probability = info.language_probability
            if not text:
                raise sr.UnknownValueError()

            output_text = self.transform_output_text(text)
            elapsed = time.time() - started
            if not output_text:
                raise RuntimeError("Conversao retornou texto vazio")
            self.copy_to_clipboard(output_text)
            self.root.after(0, self.after_transcription_success, output_text, elapsed, language_probability)
        except sr.UnknownValueError:
            self.root.after(0, self.after_transcription_error, "Nao entendi esse gorjeio.")
        except Exception as exc:
            self.root.after(0, self.after_transcription_error, f"Erro: {str(exc)[:60]}")

    def after_no_audio(self):
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status("Nada foi capturado. Tente de novo.", "#F87171")

    def after_transcription_success(self, text, elapsed, language_probability):
        confidence = f"{language_probability:.2f}" if language_probability is not None else "n/a"
        self.set_result_text(text)
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(
            f"Copiado em {elapsed:.1f}s. Confianca PT: {confidence}",
            "#34D399",
        )

    def after_transcription_error(self, error_text):
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(error_text, "#F87171")

    def handle_capture_failure(self, error_text):
        self.is_recording = False
        self.stop_requested = False
        self.hotkey_recording = False
        self.audio_chunks = []
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(error_text, "#F87171")

    def get_model_cache_path(self, model_name):
        return os.path.join(HF_CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")

    def is_model_cached(self, model_name):
        return os.path.isdir(self.get_model_cache_path(model_name))

    def refresh_cache_status(self):
        small = "ok" if self.is_model_cached("small") else "faltando"
        medium = "ok" if self.is_model_cached("medium") else "faltando"
        self.cache_label.config(text=f"Modelos: small {small} | medium {medium} | API nuvem ok")

    def refresh_models(self):
        if self.model_loading or self.is_recording or self.refreshing_models:
            return

        self.refreshing_models = True
        self.refresh_button.config(state=tk.DISABLED, text="Baixando...")
        self.update_status("Baixando ou atualizando modelos locais...", "#FBBF24")
        threading.Thread(target=self.refresh_models_worker, daemon=True).start()

    def refresh_models_worker(self):
        results = []
        try:
            for model_name in ("small", "medium"):
                started = time.time()
                WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=CPU_THREADS,
                    num_workers=1,
                )
                results.append(f"{model_name} {time.time() - started:.1f}s")
            self.root.after(0, self.finish_refresh_models, results)
        except Exception as exc:
            self.root.after(0, self.fail_refresh_models, str(exc))

    def require_openai_key(self):
        if self.get_openai_api_key():
            return
        raise RuntimeError("OPENAI_API_KEY ausente. Configure a chave da API.")

    def get_openai_api_key(self):
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key.strip()

        for key_file in dict.fromkeys(OPENAI_KEY_FILES):
            if not os.path.isfile(key_file):
                continue

            try:
                with open(key_file, "r", encoding="utf-8") as handle:
                    for line in handle:
                        if "OpenAI (Speech):" in line and "sk-" in line:
                            return line.split("`")[1].strip()
                with open(key_file, "r", encoding="utf-8") as handle:
                    for line in handle:
                        if "OpenAI (RAG):" in line and "sk-" in line:
                            return line.split("`")[1].strip()
            except Exception:
                continue
        return None

    def transcribe_with_openai(self, pcm_audio):
        api_key = self.get_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY ausente")

        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_audio)

        boundary = f"bananafone-{uuid.uuid4().hex}"
        body = self.build_multipart_body(
            boundary,
            fields={
                "model": self.mode["api_model"],
                "language": "pt",
                "prompt": self.mode.get("prompt", ""),
                "response_format": "json",
                "temperature": "0",
            },
            files={
                "file": ("bananafone.wav", wav_buffer.getvalue(), "audio/wav"),
            },
        )
        request = urllib.request.Request(
            OPENAI_TRANSCRIPT_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {details[:180]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Falha de rede: {exc.reason}")

        text = (payload.get("text") or "").strip()
        language = payload.get("language")
        confidence = 1.0 if language == "pt" else None
        return text, confidence

    def transform_output_text(self, text):
        if self.output_target == "pt-BR":
            return text

        api_key = self.get_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY ausente para converter a saida")

        if self.output_target == "pt-PT":
            system_prompt = (
                "You convert dictated Brazilian Portuguese into natural European Portuguese. "
                "Preserve meaning, names, numbers, times, technical terms, and message intent. "
                "Fix obvious dictation artifacts. Output only the final text."
            )
        else:
            system_prompt = (
                "You convert dictated Brazilian Portuguese into natural, professional English. "
                "Preserve meaning, names, numbers, times, technical terms, and message intent. "
                "Fix obvious dictation artifacts and produce text a human would actually send. "
                "Output only the final English text."
            )

        payload = {
            "model": DEFAULT_OPENAI_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
        }
        request = urllib.request.Request(
            OPENAI_CHAT_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI text HTTP {exc.code}: {details[:160]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Falha de rede no texto: {exc.reason}")

        return (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def build_multipart_body(self, boundary, fields, files):
        chunks = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )

        for name, (filename, content, content_type) in files.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    (
                        f'Content-Disposition: form-data; name="{name}"; '
                        f'filename="{filename}"\r\n'
                    ).encode("utf-8"),
                    f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                    content,
                    b"\r\n",
                ]
            )

        chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(chunks)

    def finish_refresh_models(self, results):
        self.refreshing_models = False
        self.refresh_button.config(state=tk.NORMAL, text="Baixar / Atualizar modelos")
        self.refresh_cache_status()
        self.update_status(f"Modelos prontos: {', '.join(results)}", "#34D399")
        self.set_mode_button_states()

    def fail_refresh_models(self, error_text):
        self.refreshing_models = False
        self.refresh_button.config(state=tk.NORMAL, text="Baixar / Atualizar modelos")
        self.refresh_cache_status()
        self.update_status(f"Falha ao baixar/atualizar: {error_text}", "#F87171")
        self.set_mode_button_states()

    def copy_to_clipboard(self, text):
        commands = []
        system = platform.system().lower()
        if system == "windows" and shutil.which("powershell.exe"):
            commands.append(["powershell.exe", "-NoProfile", "-Command", "$input | Set-Clipboard"])
        elif system == "darwin" and shutil.which("pbcopy"):
            commands.append(["pbcopy"])

        if os.environ.get("XDG_SESSION_TYPE") == "wayland" and shutil.which("wl-copy"):
            commands.append(["wl-copy"])
        if shutil.which("xclip"):
            commands.append(["xclip", "-selection", "clipboard"])

        for command in commands:
            try:
                process = subprocess.Popen(command, stdin=subprocess.PIPE)
                process.communicate(text.encode("utf-8"), timeout=2)
                if process.returncode == 0:
                    return
            except Exception:
                continue


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = DictationApp(root)
        root.mainloop()
    except Exception:
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write("\n[FATAL] Bananafone failed before or during GUI startup\n")
            traceback.print_exc(file=log)
        raise
