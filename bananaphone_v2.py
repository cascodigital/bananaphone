#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
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

APP_NAME = "BananaPhone"
APP_VERSION = "2.1-dev"
CPU_THREADS = min(os.cpu_count() or 4, 8)
LOG_DIR = os.path.expanduser("~/.local/state/bananafone")
LOG_FILE = os.path.join(LOG_DIR, "bananaphone_v2.log")
CONFIG_DIR = os.path.expanduser("~/.config/bananafone")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings_v2.json")
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
DEFAULT_SILENCE_TIMEOUT = os.environ.get("BANANAPHONE_V2_SILENCE_TIMEOUT", "4")
SILENCE_TIMEOUT_OPTIONS = ("4", "7", "10", "off")
MIN_SPEECH_SECONDS = float(os.environ.get("BANANAFONE_MIN_SPEECH_SECONDS", "0.35"))
SILENCE_RMS_MULTIPLIER = float(os.environ.get("BANANAFONE_SILENCE_RMS_MULTIPLIER", "1.35"))
SELECTED_BG = "#111827"
SELECTED_FG = "#F9FAFB"
SELECTED_RING = "#60A5FA"
UNSELECTED_RING = "#9CA3AF"

LANGUAGES = {
    "en": {
        "label": "EN",
        "name": "English",
        "dictation_name": "English",
        "button_color": "#E5E7EB",
        "text_color": "black",
    },
    "pt": {
        "label": "PT",
        "name": "Brazilian Portuguese",
        "dictation_name": "Brazilian Portuguese",
        "button_color": "#D1FAE5",
        "text_color": "black",
    },
    "es": {
        "label": "ES",
        "name": "Spanish",
        "dictation_name": "Spanish",
        "button_color": "#FEF3C7",
        "text_color": "black",
    },
}

OUTPUT_TARGETS = {
    "en": {"label": "EN", "button_color": "#E5E7EB", "text_color": "black"},
    "pt": {"label": "PT", "button_color": "#D1FAE5", "text_color": "black"},
    "es": {"label": "ES", "button_color": "#FEF3C7", "text_color": "black"},
}

MODE_CHOICES = {
    "Normal": "normal",
    "API": "slow",
    "Jira Mode": "jira",
}

LANGUAGE_CHOICES = {
    "English": "en",
    "Portuguese": "pt",
    "Spanish": "es",
}

MODE_LABELS = {value: key for key, value in MODE_CHOICES.items() if value != "jira"}
LANGUAGE_LABELS = {value: key for key, value in LANGUAGE_CHOICES.items()}

MODES = {
    "fast": {
        "label": "Fast",
        "button_color": "#F59E0B",
        "text_color": "black",
        "status": "Fast local transcription. Less precise with numbers.",
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
        "status": "Balanced local transcription.",
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
        "status": "Cloud transcription for higher precision.",
        "backend": "openai",
        "api_model": DEFAULT_OPENAI_MODEL,
        "ambient_duration": 0.75,
        "prompt": "Transcribe with high fidelity for numbers, times, names, and technical terms.",
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
        self.root.geometry("680x760")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111827")
        self.root.eval("tk::PlaceWindow . center")

        self.settings = self.load_settings()
        self.default_mode_key = self.settings.get("default_mode", "slow")
        self.default_input_language = self.settings.get("default_input_language", "en")
        self.default_output_target = self.settings.get("default_output", "en")
        self.default_jira_mode = self.settings.get("default_jira_mode", False)
        self.silence_timeout_setting = self.settings.get("silence_timeout", DEFAULT_SILENCE_TIMEOUT)
        self.configured_api_key = self.settings.get("api_key", "")
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
        self.input_language = self.default_input_language
        self.output_target = self.default_output_target
        self.jira_mode = self.default_jira_mode
        self.jira_raw_notes = []
        self.generating_jira = False

        self.build_ui()
        self.setup_bindings()
        self.refresh_cache_status()
        self.set_input_language(self.input_language, update_status=False)
        self.set_output_target(self.output_target, update_status=False)
        self.refresh_output_panel()
        if self.jira_mode:
            self.mode_key = "slow"
            self.mode = MODES[self.mode_key]
        self.select_mode(self.mode_key)

    def build_ui(self):
        self.title_label = tk.Label(
            self.root,
            text="BANANAPHONE",
            font=("Helvetica", 20, "bold"),
            fg="#F9FAFB",
            bg="#111827",
        )
        self.title_label.pack(pady=(16, 6))

        self.status_label = tk.Label(
            self.root,
            text="Loading API mode...",
            font=("Helvetica", 12),
            fg="#D1D5DB",
            bg="#111827",
            wraplength=560,
        )
        self.status_label.pack(pady=(0, 10))

        self.route_frame = tk.Frame(self.root, bg="#172033", highlightthickness=1, highlightbackground="#334155")
        self.route_frame.pack(fill=tk.X, padx=34, pady=(2, 14))

        self.mode_buttons = {}
        self.input_buttons = {}
        self.output_buttons = {}

        self.engine_var = tk.StringVar(value="Jira Mode" if self.jira_mode else MODE_LABELS.get(self.mode_key, "API"))
        self.input_var = tk.StringVar(value=LANGUAGE_LABELS.get(self.input_language, "English"))
        self.output_var = tk.StringVar(value=LANGUAGE_LABELS.get(self.output_target, "English"))

        for column, (label, variable, values, handler) in enumerate(
            (
                ("Engine", self.engine_var, tuple(MODE_CHOICES.keys()), self.on_engine_selected),
                ("Input", self.input_var, tuple(LANGUAGE_CHOICES.keys()), self.on_input_selected),
                ("Output", self.output_var, tuple(LANGUAGE_CHOICES.keys()), self.on_output_selected),
            )
        ):
            group = tk.Frame(self.route_frame, bg="#172033")
            group.grid(row=0, column=column, padx=12, pady=12, sticky="ew")
            tk.Label(
                group,
                text=label,
                font=("Helvetica", 9, "bold"),
                fg="#94A3B8",
                bg="#172033",
            ).pack(anchor="w", pady=(0, 4))
            combo = ttk.Combobox(
                group,
                textvariable=variable,
                values=values,
                width=14,
                state="readonly",
                font=("Helvetica", 10),
            )
            combo.pack(fill=tk.X)
            combo.bind("<<ComboboxSelected>>", handler)
            if label == "Engine":
                self.engine_combo = combo
            elif label == "Input":
                self.input_combo = combo
            else:
                self.output_combo = combo

        for column in range(3):
            self.route_frame.grid_columnconfigure(column, weight=1)

        self.route_label = tk.Label(
            self.root,
            text="Click to talk. Auto-stops after silence. Ctrl+Shift still works while focused.",
            font=("Helvetica", 10),
            fg="#9CA3AF",
            bg="#111827",
            wraplength=560,
        )
        self.route_label.pack(pady=(0, 12))

        self.hold_button = tk.Button(
            self.root,
            text="PRESS TO TALK\nAuto-stops after silence",
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
            height=6,
            width=74,
            font=("Helvetica", 10),
            bg="#1F2937",
            fg="#F9FAFB",
            state=tk.DISABLED,
        )
        self.result_text.pack(pady=(0, 12))

        self.jira_frame = tk.Frame(self.root, bg="#111827")

        self.jira_actions_frame = tk.Frame(self.jira_frame, bg="#111827")
        self.jira_actions_frame.pack(fill=tk.X, pady=(0, 6))

        self.generate_jira_button = tk.Button(
            self.jira_actions_frame,
            text="Generate JIRA",
            font=("Helvetica", 9, "bold"),
            width=14,
            bg="#BFDBFE",
            fg="black",
            command=self.generate_jira_from_notes,
        )
        self.generate_jira_button.pack(side=tk.LEFT, padx=(0, 6))

        self.clear_notes_button = tk.Button(
            self.jira_actions_frame,
            text="Clear Notes",
            font=("Helvetica", 9, "bold"),
            width=12,
            bg="#FEE2E2",
            fg="black",
            command=self.clear_jira_notes,
        )
        self.clear_notes_button.pack(side=tk.LEFT, padx=(0, 6))

        self.copy_customer_button = tk.Button(
            self.jira_actions_frame,
            text="Copy Customer",
            font=("Helvetica", 9, "bold"),
            width=14,
            bg="#E5E7EB",
            fg="black",
            command=self.copy_customer_comment,
        )
        self.copy_customer_button.pack(side=tk.RIGHT, padx=(6, 0))

        self.copy_internal_button = tk.Button(
            self.jira_actions_frame,
            text="Copy Internal",
            font=("Helvetica", 9, "bold"),
            width=14,
            bg="#E5E7EB",
            fg="black",
            command=self.copy_internal_note,
        )
        self.copy_internal_button.pack(side=tk.RIGHT, padx=(6, 0))

        style = ttk.Style()
        style.configure("Banana.TNotebook", background="#111827", borderwidth=0)
        style.configure("Banana.TNotebook.Tab", padding=(12, 5))

        self.jira_notebook = ttk.Notebook(self.jira_frame, style="Banana.TNotebook")
        self.jira_notebook.pack(fill=tk.BOTH, expand=False)

        self.raw_notes_tab = tk.Frame(self.jira_notebook, bg="#111827")
        self.customer_tab = tk.Frame(self.jira_notebook, bg="#111827")
        self.internal_tab = tk.Frame(self.jira_notebook, bg="#111827")

        self.jira_notebook.add(self.raw_notes_tab, text="Raw Notes")
        self.jira_notebook.add(self.customer_tab, text="Customer")
        self.jira_notebook.add(self.internal_tab, text="Internal")

        self.raw_notes_text = tk.Text(
            self.raw_notes_tab,
            height=8,
            width=74,
            font=("Helvetica", 10),
            bg="#1F2937",
            fg="#F9FAFB",
            state=tk.DISABLED,
        )
        self.raw_notes_text.pack(pady=(2, 8))

        self.customer_text = tk.Text(
            self.customer_tab,
            height=8,
            width=74,
            font=("Helvetica", 10),
            bg="#1F2937",
            fg="#F9FAFB",
            state=tk.DISABLED,
        )
        self.customer_text.pack(pady=(2, 8))

        self.internal_text = tk.Text(
            self.internal_tab,
            height=8,
            width=74,
            font=("Helvetica", 10),
            bg="#1F2937",
            fg="#F9FAFB",
            state=tk.DISABLED,
        )
        self.internal_text.pack(pady=(2, 8))

        self.bottom_frame = tk.Frame(self.root, bg="#111827")
        self.bottom_frame.pack(fill=tk.X, padx=28, pady=(0, 8))

        self.bottom_status_frame = tk.Frame(self.bottom_frame, bg="#111827")
        self.bottom_status_frame.pack(fill=tk.X, pady=(0, 8))

        self.cache_label = tk.Label(
            self.bottom_status_frame,
            text="Models: checking...",
            font=("Helvetica", 9),
            fg="#9CA3AF",
            bg="#111827",
            anchor="center",
        )
        self.cache_label.pack()

        self.bottom_actions_frame = tk.Frame(self.bottom_frame, bg="#111827")
        self.bottom_actions_frame.pack()

        self.save_defaults_button = tk.Button(
            self.bottom_actions_frame,
            text="Set Default",
            font=("Helvetica", 10, "bold"),
            width=11,
            bg="#D1FAE5",
            fg="black",
            command=self.save_current_as_default,
        )
        self.save_defaults_button.grid(row=0, column=0, padx=6)

        self.settings_button = tk.Button(
            self.bottom_actions_frame,
            text="Settings",
            font=("Helvetica", 10, "bold"),
            width=11,
            bg="#DBEAFE",
            fg="black",
            command=self.open_settings_window,
        )
        self.settings_button.grid(row=0, column=1, padx=6)

        self.defaults_label = tk.Label(
            self.root,
            text="Default: loading...",
            font=("Helvetica", 9),
            fg="#9CA3AF",
            bg="#111827",
        )
        self.defaults_label.pack(pady=(0, 8))

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

    def config_refresh_button(self, **kwargs):
        button = getattr(self, "refresh_button", None)
        if button is not None and button.winfo_exists():
            button.config(**kwargs)

    def on_engine_selected(self, _event=None):
        choice = MODE_CHOICES.get(self.engine_var.get(), "slow")
        if choice == "jira":
            self.set_jira_mode(True)
        else:
            if self.jira_mode:
                self.set_jira_mode(False, update_engine=False)
            self.select_mode(choice)

    def on_input_selected(self, _event=None):
        self.set_input_language(LANGUAGE_CHOICES.get(self.input_var.get(), "en"))

    def on_output_selected(self, _event=None):
        self.set_output_target(LANGUAGE_CHOICES.get(self.output_var.get(), "en"))

    def style_choice_button(self, button, selected, normal_bg, normal_fg, state):
        if selected:
            button.config(
                bg=SELECTED_BG,
                fg=SELECTED_FG,
                activebackground="#1F2937",
                activeforeground=SELECTED_FG,
                relief=tk.SOLID,
                bd=3,
                highlightthickness=3,
                highlightbackground=SELECTED_RING,
                highlightcolor=SELECTED_RING,
                state=state,
            )
        else:
            button.config(
                bg=normal_bg,
                fg=normal_fg,
                activebackground=normal_bg,
                activeforeground=normal_fg,
                relief=tk.RAISED,
                bd=1,
                highlightthickness=1,
                highlightbackground=UNSELECTED_RING,
                highlightcolor=UNSELECTED_RING,
                state=state,
            )

    def set_mode_button_states(self):
        busy = self.is_recording or self.model_loading or self.refreshing_models or self.generating_jira
        for key, button in self.mode_buttons.items():
            state = tk.NORMAL if not busy else tk.DISABLED
            if self.jira_mode and key != "slow":
                state = tk.DISABLED
            mode = MODES[key]
            self.style_choice_button(button, key == self.mode_key, mode["button_color"], mode["text_color"], state)
        for key, button in self.input_buttons.items():
            language = LANGUAGES[key]
            self.style_choice_button(
                button,
                key == self.input_language,
                language["button_color"],
                language["text_color"],
                tk.NORMAL if not busy else tk.DISABLED,
            )
        for key, button in self.output_buttons.items():
            target = OUTPUT_TARGETS[key]
            self.style_choice_button(
                button,
                key == self.output_target,
                target["button_color"],
                target["text_color"],
                tk.NORMAL if not busy else tk.DISABLED,
            )
        state = tk.DISABLED if busy else tk.NORMAL
        combo_state = tk.DISABLED if busy else "readonly"
        self.engine_combo.config(state=combo_state)
        self.input_combo.config(state=combo_state)
        self.output_combo.config(state=combo_state)
        self.config_refresh_button(state=state)
        self.save_defaults_button.config(state=state)
        self.settings_button.config(state=state)
        self.generate_jira_button.config(state=state)
        self.clear_notes_button.config(state=state)
        self.copy_customer_button.config(state=state)
        self.copy_internal_button.config(state=state)

    def set_hold_button_idle(self):
        self.hold_button.config(
            text=self.idle_button_text(),
            bg="#374151",
            activebackground="#4B5563",
            state=tk.NORMAL if not self.model_loading else tk.DISABLED,
        )

    def set_hold_button_recording(self):
        self.hold_button.config(
            text="LISTENING...\nCLICK TO STOP",
            bg="#DC2626",
            activebackground="#EF4444",
            state=tk.NORMAL,
        )

    def set_result_text(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def set_text_widget(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def set_jira_text(self, customer_comment, internal_note):
        self.set_text_widget(self.customer_text, customer_comment)
        self.set_text_widget(self.internal_text, internal_note)

    def refresh_raw_notes_text(self):
        self.set_text_widget(self.raw_notes_text, "\n\n".join(self.jira_raw_notes))

    def copy_customer_comment(self):
        text = self.customer_text.get("1.0", tk.END).strip()
        if text:
            self.copy_to_clipboard(text)
            self.update_status("Customer Comment copied.", "#34D399")

    def copy_internal_note(self):
        text = self.internal_text.get("1.0", tk.END).strip()
        if text:
            self.copy_to_clipboard(text)
            self.update_status("Internal Note copied.", "#34D399")

    def clear_jira_notes(self):
        self.jira_raw_notes = []
        self.refresh_raw_notes_text()
        self.set_jira_text("", "")
        self.jira_notebook.select(self.raw_notes_tab)
        self.update_status("JIRA notes cleared.", "#34D399")

    def add_jira_note(self, text):
        note = text.strip()
        if not note:
            return
        self.jira_raw_notes.append(note)
        self.refresh_raw_notes_text()
        self.jira_notebook.select(self.raw_notes_tab)

    def generate_jira_from_notes(self):
        if self.is_recording or self.model_loading or self.refreshing_models or self.generating_jira:
            return
        notes = "\n\n".join(self.jira_raw_notes).strip()
        if not notes:
            self.update_status("No Raw Notes to generate JIRA output.", "#FBBF24")
            return
        if not self.get_openai_api_key():
            self.update_status("JIRA MODE requires an OpenAI API key. Open Settings.", "#FBBF24")
            return

        self.generating_jira = True
        self.set_mode_button_states()
        self.hold_button.config(text="GENERATING JIRA...", bg="#1D4ED8", state=tk.DISABLED)
        self.update_status("Generating Customer Comment and Internal Note...", "#60A5FA")
        threading.Thread(target=self.generate_jira_worker, args=(notes,), daemon=True).start()

    def generate_jira_worker(self, notes):
        try:
            started = time.time()
            output = self.transform_to_jira(notes)
            elapsed = time.time() - started
            customer_comment = output.get("customer_comment", "").strip()
            internal_note = output.get("internal_note", "").strip()
            if not customer_comment:
                raise RuntimeError("JIRA output returned empty Customer Comment")
            self.copy_to_clipboard(customer_comment)
            self.root.after(0, self.finish_generate_jira, customer_comment, internal_note, elapsed)
        except Exception as exc:
            self.root.after(0, self.fail_generate_jira, str(exc)[:80])

    def finish_generate_jira(self, customer_comment, internal_note, elapsed):
        self.generating_jira = False
        self.set_jira_text(customer_comment, internal_note)
        self.jira_notebook.select(self.customer_tab)
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(f"Customer Comment copied in {elapsed:.1f}s.", "#34D399")

    def fail_generate_jira(self, error_text):
        self.generating_jira = False
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(f"JIRA generation error: {error_text}", "#F87171")

    def refresh_output_panel(self):
        if self.jira_mode:
            self.result_text.pack_forget()
            self.jira_frame.pack(pady=(0, 8))
        else:
            self.jira_frame.pack_forget()
            self.result_text.pack(pady=(0, 12))

    def select_mode(self, mode_key):
        if self.is_recording or self.model_loading:
            return
        if self.jira_mode and mode_key != "slow":
            return
        self.mode_key = mode_key
        self.mode = MODES[mode_key]
        if hasattr(self, "engine_var"):
            self.engine_var.set("Jira Mode" if self.jira_mode else MODE_LABELS.get(mode_key, "API"))
        self.root.title(f"{APP_NAME} {APP_VERSION} - {self.mode['label']}")
        self.route_label.config(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_mode_button_states()
        self.ensure_model_loaded_async(mode_key)

    def set_jira_mode(self, enabled, update_engine=True):
        if self.is_recording or self.model_loading or self.refreshing_models:
            return
        self.jira_mode = enabled
        if update_engine:
            self.engine_var.set("Jira Mode" if enabled else MODE_LABELS.get(self.mode_key, "API"))
        self.refresh_output_panel()
        self.route_label.config(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_hold_button_idle()
        self.set_mode_button_states()
        if enabled:
            if not self.get_openai_api_key():
                self.update_status("JIRA MODE requires an OpenAI API key. Open Settings.", "#FBBF24")
            if self.mode_key != "slow":
                self.select_mode("slow")

    def toggle_jira_mode(self):
        self.set_jira_mode(not self.jira_mode)

    def set_input_language(self, language_key, update_status=True):
        if self.is_recording or self.model_loading or language_key not in LANGUAGES:
            return
        self.input_language = language_key
        if hasattr(self, "input_var"):
            self.input_var.set(LANGUAGE_LABELS.get(language_key, "English"))
        if update_status:
            self.route_label.config(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_mode_button_states()

    def set_output_target(self, target_key, update_status=True):
        if self.is_recording or self.model_loading or target_key not in OUTPUT_TARGETS:
            return
        self.output_target = target_key
        if hasattr(self, "output_var"):
            self.output_var.set(LANGUAGE_LABELS.get(target_key, "English"))
        if update_status:
            self.route_label.config(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_mode_button_states()

    def refresh_defaults_label(self):
        default_mode_label = MODES.get(self.default_mode_key, MODES["slow"])["label"]
        input_label = LANGUAGES.get(self.default_input_language, LANGUAGES["en"])["label"]
        output_label = OUTPUT_TARGETS.get(self.default_output_target, OUTPUT_TARGETS["en"])["label"]
        jira_label = " + JIRA" if self.default_jira_mode else ""
        self.defaults_label.config(text=f"Default: {default_mode_label} + {input_label} -> {output_label}{jira_label}")

    def idle_button_text(self):
        if self.jira_mode:
            return "ADD NOTE\nJIRA MODE"
        if self.silence_timeout_seconds() is None:
            return "PRESS TO TALK\nClick again to stop"
        return "PRESS TO TALK\nAuto-stops after silence"

    def current_route_status(self):
        input_name = LANGUAGES[self.input_language]["name"]
        output_name = LANGUAGES[self.output_target]["name"]
        mode_label = " | JIRA MODE" if self.jira_mode else ""
        timeout = self.silence_timeout_label()
        return f"{self.mode['status']} | Input: {input_name} | Output: {output_name}{mode_label} | Silence: {timeout}"

    def source_language(self):
        return self.input_language

    def target_language(self):
        return self.output_target

    def load_settings(self):
        if not os.path.isfile(SETTINGS_FILE):
            return {}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
                settings = json.load(handle)
        except Exception:
            return {}

        default_mode = settings.get("default_mode", "slow")
        default_input_language = settings.get("default_input_language", "en")
        default_output = settings.get("default_output", "en")
        default_jira_mode = bool(settings.get("default_jira_mode", False))
        if default_output == "jira":
            default_output = "en"
            default_jira_mode = True
        silence_timeout = str(settings.get("silence_timeout", DEFAULT_SILENCE_TIMEOUT)).lower()
        if default_mode not in MODES:
            default_mode = "slow"
        if default_mode == "fast":
            default_mode = "normal"
        if default_input_language not in LANGUAGES:
            default_input_language = "en"
        if default_output not in OUTPUT_TARGETS:
            default_output = "en"
        if default_jira_mode:
            default_mode = "slow"
        if silence_timeout not in SILENCE_TIMEOUT_OPTIONS:
            silence_timeout = DEFAULT_SILENCE_TIMEOUT
        return {
            "default_mode": default_mode,
            "default_input_language": default_input_language,
            "default_output": default_output,
            "default_jira_mode": default_jira_mode,
            "silence_timeout": silence_timeout,
            "api_key": settings.get("api_key", "").strip(),
        }

    def write_settings(self):
        settings = {
            "default_mode": self.default_mode_key,
            "default_input_language": self.default_input_language,
            "default_output": self.default_output_target,
            "default_jira_mode": self.default_jira_mode,
            "silence_timeout": self.silence_timeout_setting,
            "api_key": self.configured_api_key,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)

    def save_current_as_default(self):
        self.default_mode_key = self.mode_key
        self.default_input_language = self.input_language
        self.default_output_target = self.output_target
        self.default_jira_mode = self.jira_mode
        self.write_settings()
        self.refresh_defaults_label()
        jira_label = " + JIRA" if self.jira_mode else ""
        self.update_status(
            f"Default saved: {self.mode['label']} + {self.input_language.upper()} -> {self.output_target.upper()}{jira_label}",
            "#34D399",
        )

    def silence_timeout_seconds(self):
        if self.silence_timeout_setting == "off":
            return None
        return float(self.silence_timeout_setting)

    def silence_timeout_label(self):
        timeout = self.silence_timeout_seconds()
        return "Off" if timeout is None else f"{timeout:.0f}s"

    def open_settings_window(self):
        if self.is_recording or self.model_loading or self.refreshing_models:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("BananaPhone Settings")
        dialog.geometry("500x330")
        dialog.configure(bg="#111827")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Silence timeout",
            font=("Helvetica", 10, "bold"),
            fg="#F9FAFB",
            bg="#111827",
        ).pack(anchor="w", padx=18, pady=(18, 6))

        silence_var = tk.StringVar(value=self.silence_timeout_setting)
        timeout_frame = tk.Frame(dialog, bg="#111827")
        timeout_frame.pack(anchor="w", padx=18, pady=(0, 14))
        for value, label in (("4", "4s"), ("7", "7s"), ("10", "10s"), ("off", "Off")):
            tk.Radiobutton(
                timeout_frame,
                text=label,
                value=value,
                variable=silence_var,
                font=("Helvetica", 10),
                fg="#F9FAFB",
                bg="#111827",
                selectcolor="#1F2937",
                activebackground="#111827",
                activeforeground="#F9FAFB",
            ).pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(
            dialog,
            text="OpenAI API key",
            font=("Helvetica", 10, "bold"),
            fg="#F9FAFB",
            bg="#111827",
        ).pack(anchor="w", padx=18, pady=(0, 6))

        key_var = tk.StringVar(value=self.configured_api_key)
        key_entry = tk.Entry(dialog, textvariable=key_var, show="*", width=58, font=("Helvetica", 10))
        key_entry.pack(anchor="w", padx=18, pady=(0, 8))

        hint = tk.Label(
            dialog,
            text="Stored only in ~/.config/bananafone/settings_v2.json. Env/file fallback still works.",
            font=("Helvetica", 9),
            fg="#9CA3AF",
            bg="#111827",
            wraplength=440,
        )
        hint.pack(anchor="w", padx=18, pady=(0, 18))

        tk.Label(
            dialog,
            text="Local models",
            font=("Helvetica", 10, "bold"),
            fg="#F9FAFB",
            bg="#111827",
        ).pack(anchor="w", padx=18, pady=(0, 6))

        models_frame = tk.Frame(dialog, bg="#111827")
        models_frame.pack(anchor="w", padx=18, pady=(0, 18))

        self.refresh_button = tk.Button(
            models_frame,
            text="Download Models",
            font=("Helvetica", 10, "bold"),
            bg="#E5E7EB",
            fg="black",
            command=self.refresh_models,
        )
        self.refresh_button.pack(side=tk.LEFT)

        buttons = tk.Frame(dialog, bg="#111827")
        buttons.pack(anchor="e", padx=18)

        def save_settings():
            self.silence_timeout_setting = silence_var.get()
            self.configured_api_key = key_var.get().strip()
            self.write_settings()
            self.route_label.config(text=self.current_route_status())
            self.set_hold_button_idle()
            self.update_status("Settings saved.", "#34D399")
            dialog.destroy()
            if self.mode.get("backend") == "openai" and self.model is None:
                self.ensure_model_loaded_async(self.mode_key)

        tk.Button(
            buttons,
            text="Cancel",
            font=("Helvetica", 10, "bold"),
            bg="#E5E7EB",
            fg="black",
            command=dialog.destroy,
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            buttons,
            text="Save",
            font=("Helvetica", 10, "bold"),
            bg="#D1FAE5",
            fg="black",
            command=save_settings,
        ).pack(side=tk.LEFT)

    def ensure_model_loaded_async(self, mode_key):
        if self.model_key_loaded == mode_key and self.model is not None:
            self.update_status(f"{self.mode['label']} mode ready.", "#34D399")
            self.set_hold_button_idle()
            self.refresh_cache_status()
            return

        self.model_loading = True
        self.update_status(f"Loading {MODES[mode_key]['label']} mode...", "#FBBF24")
        self.hold_button.config(text="LOADING...\nlocal suffering", bg="#6B7280", state=tk.DISABLED)
        self.set_mode_button_states()
        threading.Thread(target=self.load_mode_resources, args=(mode_key,), daemon=True).start()

    def load_mode_resources(self, mode_key):
        try:
            mode = MODES[mode_key]
            started = time.time()
            source = sr.Microphone()
            with source as mic_source:
                self.root.after(0, self.update_status, "Calibrating ambient noise...", "#FBBF24")
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
        self.update_status(f"{self.mode['label']} mode ready in {elapsed:.1f}s.", "#34D399")

    def fail_loading_mode(self, error_text):
        self.model_loading = False
        self.set_mode_button_states()
        self.hold_button.config(text="LOAD ERROR\ncheck the log", bg="#7F1D1D", state=tk.DISABLED)
        self.update_status(f"Load error: {error_text}", "#F87171")

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
        timeout = self.silence_timeout_seconds()
        if self.jira_mode:
            status = "Recording JIRA note. It will be added to Raw Notes."
        elif timeout is None:
            status = f"Recording in {self.mode['label']} mode. Click again to stop."
        else:
            status = f"Recording in {self.mode['label']} mode. Auto-stops after {timeout:.0f}s of silence."
        self.update_status(status, "#34D399")
        self.recording_thread = threading.Thread(target=self.capture_audio_loop, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_requested = True
        self.hotkey_recording = False

        self.hold_button.config(text="TRANSCRIBING...", bg="#1D4ED8", state=tk.DISABLED)
        self.update_status(f"Transcribing with {self.mode['label']} mode...", "#60A5FA")
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

                    timeout = self.silence_timeout_seconds()
                    if rms >= threshold:
                        speech_frames += 1
                        silence_deadline = time.time() + timeout if timeout is not None else None
                    elif timeout is not None and speech_frames > 0 and silence_deadline and time.time() >= silence_deadline:
                        self.root.after(0, self.stop_recording)
                        return

            min_chunks = max(1, int((sample_rate * MIN_SPEECH_SECONDS) / chunk_size))
            if speech_frames < min_chunks:
                self.audio_chunks = []
        except Exception as exc:
            self.root.after(0, self.handle_capture_failure, f"Capture error: {str(exc)[:60]}")

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
                transcribe_kwargs = dict(self.mode["transcribe_kwargs"])
                transcribe_kwargs["language"] = self.source_language()
                segments, info = self.model.transcribe(audio_np, **transcribe_kwargs)
                text = " ".join(segment.text.strip() for segment in segments).strip()
                language_probability = info.language_probability
            if not text:
                raise sr.UnknownValueError()

            if self.jira_mode:
                output_text = text
            else:
                output_text = self.transform_output_text(text)
            elapsed = time.time() - started
            if not output_text:
                raise RuntimeError("Text conversion returned empty output")

            if self.jira_mode:
                result = {"raw_note": output_text}
            else:
                self.copy_to_clipboard(output_text)
                result = output_text
            self.root.after(0, self.after_transcription_success, result, elapsed, language_probability)
        except sr.UnknownValueError:
            self.root.after(0, self.after_transcription_error, "Could not understand the audio.")
        except Exception as exc:
            self.root.after(0, self.after_transcription_error, f"Error: {str(exc)[:60]}")

    def after_no_audio(self):
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status("No audio captured. Try again.", "#F87171")

    def after_transcription_success(self, text, elapsed, language_probability):
        confidence = f"{language_probability:.2f}" if language_probability is not None else "n/a"
        source_label = self.source_language().upper()
        if isinstance(text, dict) and "raw_note" in text:
            self.add_jira_note(text.get("raw_note", ""))
            copied_label = "Raw Note added"
        elif isinstance(text, dict):
            self.set_jira_text(text.get("customer_comment", ""), text.get("internal_note", ""))
            copied_label = "Customer Comment copied"
        else:
            self.set_result_text(text)
            copied_label = "Copied"
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(
            f"{copied_label} in {elapsed:.1f}s. {source_label} confidence: {confidence}",
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
        small = "ok" if self.is_model_cached("small") else "missing"
        medium = "ok" if self.is_model_cached("medium") else "missing"
        self.cache_label.config(text=f"Models: small {small} | medium {medium} | API cloud")

    def refresh_models(self):
        if self.model_loading or self.is_recording or self.refreshing_models:
            return

        self.refreshing_models = True
        self.config_refresh_button(state=tk.DISABLED, text="Downloading...")
        self.update_status("Downloading or updating local models...", "#FBBF24")
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
        raise RuntimeError("OPENAI_API_KEY missing. Configure the API key.")

    def get_openai_api_key(self):
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key.strip()
        if self.configured_api_key:
            return self.configured_api_key.strip()

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
            raise RuntimeError("OPENAI_API_KEY missing")

        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_audio)

        boundary = f"bananafone-{uuid.uuid4().hex}"
        source_language = self.source_language()
        source_label = LANGUAGES[source_language]["dictation_name"]
        prompt = (
            f"Transcribe {source_label} with high fidelity for numbers, times, names, "
            "technical terms, and dictated punctuation."
        )
        body = self.build_multipart_body(
            boundary,
            fields={
                "model": self.mode["api_model"],
                "language": source_language,
                "prompt": prompt,
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
            raise RuntimeError(f"Network failure: {exc.reason}")

        text = (payload.get("text") or "").strip()
        language = payload.get("language")
        confidence = 1.0 if language == source_language else None
        return text, confidence

    def transform_output_text(self, text):
        source_language = self.source_language()
        target_language = self.target_language()

        if source_language == target_language:
            return text

        api_key = self.get_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing for text conversion")

        source_name = LANGUAGES[source_language]["name"]
        target_name = LANGUAGES[target_language]["name"]
        system_prompt = (
            f"You convert dictated {source_name} into natural, professional {target_name}. "
            "Preserve meaning, names, numbers, times, technical terms, and message intent. "
            "Fix obvious dictation artifacts and produce text a human would actually send. "
            f"Output only the final {target_name} text."
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
            raise RuntimeError(f"Text network failure: {exc.reason}")

        return (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def transform_to_jira(self, text):
        api_key = self.get_openai_api_key()
        if not api_key:
            raise RuntimeError("JIRA output requires an OpenAI API key")

        source_name = LANGUAGES[self.input_language]["name"]
        language_name = LANGUAGES[self.output_target]["name"]
        system_prompt = (
            f"You turn dictated ticket notes from {source_name} into clean Jira documentation in {language_name}. "
            "Return strict JSON only, with keys customer_comment and internal_note. "
            "customer_comment is public-facing, concise, professional, empathetic, and non-technical. "
            "internal_note is private for IT support, direct, technical, and includes the issue, "
            "investigation, actions taken, result, and any follow-up needed. "
            "Do not invent facts. If the dictated note is not enough for a final resolution, write a "
            "progress update instead of pretending the ticket is closed."
        )

        payload = {
            "model": DEFAULT_OPENAI_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
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
            raise RuntimeError(f"OpenAI JIRA HTTP {exc.code}: {details[:160]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"JIRA network failure: {exc.reason}")

        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = self.extract_json_object(content)

        return {
            "customer_comment": str(parsed.get("customer_comment", "")).strip(),
            "internal_note": str(parsed.get("internal_note", "")).strip(),
        }

    def extract_json_object(self, text):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("JIRA output was not valid JSON")
        return json.loads(text[start : end + 1])

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
        self.config_refresh_button(state=tk.NORMAL, text="Download Models")
        self.refresh_cache_status()
        self.update_status(f"Models ready: {', '.join(results)}", "#34D399")
        self.set_mode_button_states()

    def fail_refresh_models(self, error_text):
        self.refreshing_models = False
        self.config_refresh_button(state=tk.NORMAL, text="Download Models")
        self.refresh_cache_status()
        self.update_status(f"Download/update failed: {error_text}", "#F87171")
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
