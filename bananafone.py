#!/usr/bin/env python3
import os
import shutil
import subprocess
import threading
import time
import tkinter as tk
import traceback

import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel

APP_NAME = "Bananafone"
CPU_THREADS = min(os.cpu_count() or 4, 8)
LOG_DIR = os.path.expanduser("~/.local/state/bananafone")
LOG_FILE = os.path.join(LOG_DIR, "bananafone.log")
HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")

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
        "label": "Lento",
        "button_color": "#2563EB",
        "text_color": "white",
        "status": "Mais preciso para horario, numeros e frases chatas.",
        "model_name": "medium",
        "ambient_duration": 0.75,
        "chunk_seconds": 0.75,
        "transcribe_kwargs": {
            "language": "pt",
            "beam_size": 5,
            "best_of": 5,
            "temperature": 0.0,
            "condition_on_previous_text": True,
            "vad_filter": True,
            "without_timestamps": True,
        },
    },
}

os.makedirs(LOG_DIR, exist_ok=True)
log_fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.dup2(log_fd, 2)


class DictationApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("520x380")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111827")
        self.root.eval("tk::PlaceWindow . center")

        self.mode_key = "normal"
        self.mode = MODES[self.mode_key]
        self.model = None
        self.model_key_loaded = None
        self.model_loading = False
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.source = None
        self.audio_chunks = []
        self.stop_listening_func = None
        self.is_recording = False
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.transcription_thread = None
        self.refreshing_models = False

        self.build_ui()
        self.setup_bindings()
        self.refresh_cache_status()
        self.select_mode("normal")

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
            text="Carregando modo normal...",
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

        self.mode_label = tk.Label(
            self.root,
            text="Segure o botao abaixo ou use Ctrl+Shift com a janela focada.",
            font=("Helvetica", 10),
            fg="#9CA3AF",
            bg="#111827",
            wraplength=470,
        )
        self.mode_label.pack(pady=(0, 12))

        self.hold_button = tk.Button(
            self.root,
            text="SEGURE PARA FALAR\nCtrl+Shift com foco",
            font=("Helvetica", 15, "bold"),
            width=24,
            height=3,
            bg="#374151",
            fg="#F9FAFB",
            relief=tk.RAISED,
            justify=tk.CENTER,
        )
        self.hold_button.pack(pady=(0, 12))
        self.hold_button.bind("<ButtonPress-1>", self.on_hold_press)
        self.hold_button.bind("<ButtonRelease-1>", self.on_hold_release)

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
        self.refresh_button.config(
            state=tk.DISABLED if self.is_recording or self.model_loading or self.refreshing_models else tk.NORMAL
        )

    def set_hold_button_idle(self):
        self.hold_button.config(
            text="SEGURE PARA FALAR\nCtrl+Shift com foco",
            bg="#374151",
            activebackground="#4B5563",
            state=tk.NORMAL if not self.model_loading else tk.DISABLED,
        )

    def set_hold_button_recording(self):
        self.hold_button.config(
            text="FALANDO...\nSOLTE PARA TRANSCREVER",
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
        self.root.title(f"{APP_NAME} - {self.mode['label']}")
        self.mode_label.config(text=self.mode["status"])
        self.set_mode_button_states()
        self.ensure_model_loaded_async(mode_key)

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
            model = WhisperModel(
                mode["model_name"],
                device="cpu",
                compute_type="int8",
                cpu_threads=CPU_THREADS,
                num_workers=1,
            )
            source = sr.Microphone()
            with source as mic_source:
                self.root.after(0, self.update_status, "Calibrando ruido ambiente...", "#FBBF24")
                self.recognizer.adjust_for_ambient_noise(
                    mic_source,
                    duration=mode["ambient_duration"],
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

    def on_hold_press(self, _event):
        self.start_recording()

    def on_hold_release(self, _event):
        self.stop_recording()

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
        if self.ctrl_pressed and self.shift_pressed:
            self.start_recording()

    def maybe_stop_hotkey_recording(self):
        if self.is_recording and not (self.ctrl_pressed and self.shift_pressed):
            self.stop_recording()

    def start_recording(self):
        if self.is_recording or self.model_loading or self.model is None or self.source is None:
            return

        self.audio_chunks = []
        self.is_recording = True
        self.set_mode_button_states()
        self.set_hold_button_recording()
        self.update_status(f"Gravando em {self.mode['label']}. Solte para transcrever.", "#34D399")
        self.stop_listening_func = self.recognizer.listen_in_background(
            self.source,
            self.audio_callback,
            phrase_time_limit=self.mode["chunk_seconds"],
        )

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        if self.stop_listening_func:
            self.stop_listening_func(wait_for_stop=True)
            self.stop_listening_func = None

        self.hold_button.config(text="TRANSCREVENDO...", bg="#1D4ED8", state=tk.DISABLED)
        self.update_status(f"Transcrevendo com modo {self.mode['label']}...", "#60A5FA")
        self.transcription_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.transcription_thread.start()

    def audio_callback(self, recognizer, audio):
        del recognizer
        if self.is_recording:
            self.audio_chunks.append(audio.get_raw_data())

    def process_audio(self):
        if not self.audio_chunks:
            self.root.after(0, self.after_no_audio)
            return

        with self.source as mic_source:
            sample_rate = mic_source.SAMPLE_RATE
            sample_width = mic_source.SAMPLE_WIDTH

        raw_data = b"".join(self.audio_chunks)
        audio = sr.AudioData(raw_data, sample_rate, sample_width)

        try:
            started = time.time()
            audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = self.model.transcribe(audio_np, **self.mode["transcribe_kwargs"])
            text = " ".join(segment.text.strip() for segment in segments).strip()
            elapsed = time.time() - started

            if not text:
                raise sr.UnknownValueError()

            self.copy_to_clipboard(text)
            self.root.after(0, self.after_transcription_success, text, elapsed, info.language_probability)
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

    def get_model_cache_path(self, model_name):
        return os.path.join(HF_CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")

    def is_model_cached(self, model_name):
        return os.path.isdir(self.get_model_cache_path(model_name))

    def refresh_cache_status(self):
        small = "ok" if self.is_model_cached("small") else "faltando"
        medium = "ok" if self.is_model_cached("medium") else "faltando"
        self.cache_label.config(text=f"Modelos: small {small} | medium {medium}")

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
