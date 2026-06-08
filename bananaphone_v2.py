#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox
import traceback
import audioop
import json
import urllib.error
import urllib.request
import uuid
import wave
from io import BytesIO

import customtkinter as ctk
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
# --- Text AI provider (translation + Jira) --------------------------------
# The text tasks (PT->EN translation and Jira dual-output) speak the OpenAI
# Chat API, so any OpenAI-compatible endpoint works: OpenAI cloud, a local
# Ollama / llama.cpp / LM Studio server, or a custom URL. Speech (faster-whisper
# local, or OpenAI audio API) is configured separately by Engine.
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"

TEXT_PROVIDERS = {
    "OpenAI (cloud)": "openai",
    "Ollama (local)": "ollama",
    "Custom (OpenAI-compatible)": "custom",
}
TEXT_PROVIDER_LABELS = {value: key for key, value in TEXT_PROVIDERS.items()}
PROVIDER_DEFAULT_MODEL = {
    "openai": DEFAULT_OPENAI_TEXT_MODEL,
    "ollama": "qwen2.5:3b",
    "custom": DEFAULT_OPENAI_TEXT_MODEL,
}
PROVIDER_DEFAULT_BASE_URL = {
    "openai": DEFAULT_OPENAI_BASE_URL,
    "ollama": DEFAULT_OLLAMA_BASE_URL,
    "custom": DEFAULT_OLLAMA_BASE_URL,
}

DEFAULT_SILENCE_TIMEOUT = os.environ.get("BANANAPHONE_V2_SILENCE_TIMEOUT", "4")
SILENCE_TIMEOUT_OPTIONS = ("4", "7", "10", "off")
MIN_SPEECH_SECONDS = float(os.environ.get("BANANAFONE_MIN_SPEECH_SECONDS", "0.35"))
SILENCE_RMS_MULTIPLIER = float(os.environ.get("BANANAFONE_SILENCE_RMS_MULTIPLIER", "1.35"))

# --- Modern dark palette -------------------------------------------------
COLOR_WINDOW = "#0F172A"      # slate-950
COLOR_CARD = "#1E293B"        # slate-800
COLOR_CARD_BORDER = "#334155" # slate-700
COLOR_FIELD = "#0B1220"       # near-black field bg for textboxes
COLOR_TITLE = "#F8FAFC"       # slate-50
COLOR_MUTED = "#94A3B8"       # slate-400
COLOR_SUBTLE = "#64748B"      # slate-500

# Status / feedback colors (kept compatible with prior hex usage)
COLOR_OK = "#34D399"
COLOR_INFO = "#60A5FA"
COLOR_WARN = "#FBBF24"
COLOR_ERROR = "#F87171"

# Accent set for the main talk button
TALK_IDLE = "#F59E0B"
TALK_IDLE_HOVER = "#FBBF24"
TALK_IDLE_TEXT = "#1F2937"
TALK_REC = "#DC2626"
TALK_REC_HOVER = "#EF4444"
TALK_BUSY = "#1D4ED8"
TALK_LOADING = "#475569"
TALK_FAIL = "#7F1D1D"

# Secondary button accents
BTN_PRIMARY = "#2563EB"
BTN_PRIMARY_HOVER = "#1D4ED8"
BTN_NEUTRAL = "#334155"
BTN_NEUTRAL_HOVER = "#475569"
BTN_DANGER = "#7F1D1D"
BTN_DANGER_HOVER = "#991B1B"
BTN_GOOD = "#047857"
BTN_GOOD_HOVER = "#059669"

LANGUAGES = {
    "en": {
        "label": "EN",
        "name": "English",
        "dictation_name": "English",
    },
    "pt": {
        "label": "PT",
        "name": "Brazilian Portuguese",
        "dictation_name": "Brazilian Portuguese",
    },
    "es": {
        "label": "ES",
        "name": "Spanish",
        "dictation_name": "Spanish",
    },
}

OUTPUT_TARGETS = {
    "en": {"label": "EN"},
    "pt": {"label": "PT"},
    "es": {"label": "ES"},
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
        self.root.geometry("560x740")
        self.root.minsize(520, 700)
        self.root.attributes("-topmost", True)
        self.root.configure(fg_color=COLOR_WINDOW)
        self.root.eval("tk::PlaceWindow . center")

        self.settings = self.load_settings()
        self.default_mode_key = self.settings.get("default_mode", "slow")
        self.default_input_language = self.settings.get("default_input_language", "en")
        self.default_output_target = self.settings.get("default_output", "en")
        self.default_jira_mode = self.settings.get("default_jira_mode", False)
        self.silence_timeout_setting = self.settings.get("silence_timeout", DEFAULT_SILENCE_TIMEOUT)
        self.configured_api_key = self.settings.get("api_key", "")
        self.text_provider = self.settings.get("text_provider", "openai")
        self.text_model = self.settings.get("text_model", "") or PROVIDER_DEFAULT_MODEL.get(
            self.text_provider, DEFAULT_OPENAI_TEXT_MODEL
        )
        self.text_base_url = self.settings.get("text_base_url", "") or PROVIDER_DEFAULT_BASE_URL.get(
            self.text_provider, DEFAULT_OPENAI_BASE_URL
        )
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
        self.refresh_button = None
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

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        container = ctk.CTkFrame(self.root, fg_color=COLOR_WINDOW)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # Header --------------------------------------------------------
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill=tk.X)
        self.title_label = ctk.CTkLabel(
            header,
            text="🍌  BananaPhone",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLOR_TITLE,
        )
        self.title_label.pack()
        self.status_label = ctk.CTkLabel(
            header,
            text="Loading API mode...",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_MUTED,
            wraplength=480,
        )
        self.status_label.pack(pady=(2, 0))

        # Route card ----------------------------------------------------
        self.route_frame = ctk.CTkFrame(
            container,
            fg_color=COLOR_CARD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=14,
        )
        self.route_frame.pack(fill=tk.X, pady=(16, 8))

        self.engine_var = tk.StringVar(value="Jira Mode" if self.jira_mode else MODE_LABELS.get(self.mode_key, "API"))
        self.input_var = tk.StringVar(value=LANGUAGE_LABELS.get(self.input_language, "English"))
        self.output_var = tk.StringVar(value=LANGUAGE_LABELS.get(self.output_target, "English"))

        self.engine_combo = self._build_route_field(
            self.route_frame, 0, "ENGINE", self.engine_var,
            tuple(MODE_CHOICES.keys()), self.on_engine_selected,
        )
        self.input_combo = self._build_route_field(
            self.route_frame, 1, "INPUT", self.input_var,
            tuple(LANGUAGE_CHOICES.keys()), self.on_input_selected,
        )
        self.output_combo = self._build_route_field(
            self.route_frame, 2, "OUTPUT", self.output_var,
            tuple(LANGUAGE_CHOICES.keys()), self.on_output_selected,
        )
        for column in range(3):
            self.route_frame.grid_columnconfigure(column, weight=1)

        self.route_label = ctk.CTkLabel(
            container,
            text="Click to talk. Auto-stops after silence. Ctrl+Shift works while focused.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTLE,
            wraplength=480,
        )
        self.route_label.pack(pady=(0, 12))

        # Main talk button ---------------------------------------------
        self.hold_button = ctk.CTkButton(
            container,
            text="PRESS TO TALK",
            font=ctk.CTkFont(size=17, weight="bold"),
            height=72,
            corner_radius=16,
            fg_color=TALK_IDLE,
            hover_color=TALK_IDLE_HOVER,
            text_color=TALK_IDLE_TEXT,
            command=self.on_main_button_click,
        )
        self.hold_button.pack(fill=tk.X, padx=4, pady=(0, 14))

        # Normal result area -------------------------------------------
        self.result_text = ctk.CTkTextbox(
            container,
            height=150,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_FIELD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
            wrap="word",
        )
        self.result_text.configure(state="disabled")

        # Jira panel ----------------------------------------------------
        self.jira_frame = ctk.CTkFrame(container, fg_color="transparent")

        self.jira_actions_frame = ctk.CTkFrame(self.jira_frame, fg_color="transparent")
        self.jira_actions_frame.pack(fill=tk.X, pady=(0, 8))

        self.generate_jira_button = ctk.CTkButton(
            self.jira_actions_frame,
            text="Generate JIRA",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            command=self.generate_jira_from_notes,
        )
        self.generate_jira_button.pack(side=tk.LEFT, padx=(0, 6))

        self.clear_notes_button = ctk.CTkButton(
            self.jira_actions_frame,
            text="Clear",
            width=70,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
            command=self.clear_jira_notes,
        )
        self.clear_notes_button.pack(side=tk.LEFT, padx=(0, 6))

        self.copy_internal_button = ctk.CTkButton(
            self.jira_actions_frame,
            text="Copy Internal",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            command=self.copy_internal_note,
        )
        self.copy_internal_button.pack(side=tk.RIGHT)

        self.copy_customer_button = ctk.CTkButton(
            self.jira_actions_frame,
            text="Copy Customer",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            command=self.copy_customer_comment,
        )
        self.copy_customer_button.pack(side=tk.RIGHT, padx=(0, 6))

        self.jira_tabs = ctk.CTkTabview(
            self.jira_frame,
            fg_color=COLOR_CARD,
            segmented_button_fg_color=COLOR_CARD,
            segmented_button_selected_color=BTN_PRIMARY,
            segmented_button_selected_hover_color=BTN_PRIMARY_HOVER,
            corner_radius=12,
            height=210,
        )
        self.jira_tabs.pack(fill=tk.BOTH, expand=True)

        self.raw_notes_tab = self.jira_tabs.add("Raw Notes")
        self.customer_tab = self.jira_tabs.add("Customer")
        self.internal_tab = self.jira_tabs.add("Internal")

        self.raw_notes_text = self._build_panel_textbox(self.raw_notes_tab)
        self.customer_text = self._build_panel_textbox(self.customer_tab)
        self.internal_text = self._build_panel_textbox(self.internal_tab)

        # Bottom bar ----------------------------------------------------
        self.bottom_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.cache_label = ctk.CTkLabel(
            self.bottom_frame,
            text="Models: checking...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTLE,
        )
        self.cache_label.pack(pady=(0, 2))

        self.defaults_label = ctk.CTkLabel(
            self.bottom_frame,
            text="Default: loading...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_MUTED,
        )
        self.defaults_label.pack(pady=(0, 8))

        self.bottom_actions_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.bottom_actions_frame.pack()

        self.save_defaults_button = ctk.CTkButton(
            self.bottom_actions_frame,
            text="Set Default",
            width=130,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            corner_radius=10,
            fg_color=BTN_GOOD,
            hover_color=BTN_GOOD_HOVER,
            command=self.save_current_as_default,
        )
        self.save_defaults_button.grid(row=0, column=0, padx=6)

        self.settings_button = ctk.CTkButton(
            self.bottom_actions_frame,
            text="⚙  Settings",
            width=130,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            corner_radius=10,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            command=self.open_settings_window,
        )
        self.settings_button.grid(row=0, column=1, padx=6)

    def _build_route_field(self, parent, column, label, variable, values, handler):
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.grid(row=0, column=column, padx=10, pady=12, sticky="ew")
        ctk.CTkLabel(
            group,
            text=label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(0, 4))
        menu = ctk.CTkOptionMenu(
            group,
            variable=variable,
            values=list(values),
            command=handler,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_FIELD,
            button_color=BTN_NEUTRAL,
            button_hover_color=BTN_NEUTRAL_HOVER,
            corner_radius=8,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=BTN_PRIMARY,
        )
        menu.pack(fill=tk.X)
        return menu

    def _build_panel_textbox(self, parent):
        textbox = ctk.CTkTextbox(
            parent,
            height=160,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_FIELD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=8,
            wrap="word",
        )
        textbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        textbox.configure(state="disabled")
        return textbox

    def setup_bindings(self):
        self.root.bind_all("<KeyPress-Control_L>", self.on_ctrl_press)
        self.root.bind_all("<KeyRelease-Control_L>", self.on_ctrl_release)
        self.root.bind_all("<KeyPress-Control_R>", self.on_ctrl_press)
        self.root.bind_all("<KeyRelease-Control_R>", self.on_ctrl_release)
        self.root.bind_all("<KeyPress-Shift_L>", self.on_shift_press)
        self.root.bind_all("<KeyRelease-Shift_L>", self.on_shift_release)
        self.root.bind_all("<KeyPress-Shift_R>", self.on_shift_press)
        self.root.bind_all("<KeyRelease-Shift_R>", self.on_shift_release)

    def update_status(self, text, color=COLOR_TITLE):
        self.status_label.configure(text=text, text_color=color)

    def config_refresh_button(self, **kwargs):
        button = self.refresh_button
        if button is not None and button.winfo_exists():
            button.configure(**kwargs)

    def on_engine_selected(self, _choice=None):
        choice = MODE_CHOICES.get(self.engine_var.get(), "slow")
        if choice == "jira":
            self.set_jira_mode(True)
        else:
            if self.jira_mode:
                self.set_jira_mode(False, update_engine=False)
            self.select_mode(choice)

    def on_input_selected(self, _choice=None):
        self.set_input_language(LANGUAGE_CHOICES.get(self.input_var.get(), "en"))

    def on_output_selected(self, _choice=None):
        self.set_output_target(LANGUAGE_CHOICES.get(self.output_var.get(), "en"))

    def set_mode_button_states(self):
        busy = self.is_recording or self.model_loading or self.refreshing_models or self.generating_jira
        control_state = "disabled" if busy else "normal"
        self.engine_combo.configure(state=control_state)
        self.input_combo.configure(state=control_state)
        self.output_combo.configure(state=control_state)
        self.config_refresh_button(state=control_state)
        self.save_defaults_button.configure(state=control_state)
        self.settings_button.configure(state=control_state)
        self.generate_jira_button.configure(state=control_state)
        self.clear_notes_button.configure(state=control_state)
        self.copy_customer_button.configure(state=control_state)
        self.copy_internal_button.configure(state=control_state)

    def set_hold_button_idle(self):
        self.hold_button.configure(
            text=self.idle_button_text(),
            fg_color=TALK_IDLE,
            hover_color=TALK_IDLE_HOVER,
            text_color=TALK_IDLE_TEXT,
            state="disabled" if self.model_loading else "normal",
        )

    def set_hold_button_recording(self):
        self.hold_button.configure(
            text="LISTENING...  CLICK TO STOP",
            fg_color=TALK_REC,
            hover_color=TALK_REC_HOVER,
            text_color="#FFFFFF",
            state="normal",
        )

    def set_hold_button_busy(self, text, color=TALK_BUSY):
        self.hold_button.configure(
            text=text,
            fg_color=color,
            text_color="#FFFFFF",
            state="disabled",
        )

    def set_result_text(self, text):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text)
        self.result_text.configure(state="disabled")

    def set_text_widget(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def set_jira_text(self, customer_comment, internal_note):
        self.set_text_widget(self.customer_text, customer_comment)
        self.set_text_widget(self.internal_text, internal_note)

    def refresh_raw_notes_text(self):
        self.set_text_widget(self.raw_notes_text, "\n\n".join(self.jira_raw_notes))

    def copy_customer_comment(self):
        text = self.customer_text.get("1.0", "end").strip()
        if text:
            self.copy_to_clipboard(text)
            self.update_status("Customer Comment copied.", COLOR_OK)

    def copy_internal_note(self):
        text = self.internal_text.get("1.0", "end").strip()
        if text:
            self.copy_to_clipboard(text)
            self.update_status("Internal Note copied.", COLOR_OK)

    def clear_jira_notes(self):
        self.jira_raw_notes = []
        self.refresh_raw_notes_text()
        self.set_jira_text("", "")
        self.jira_tabs.set("Raw Notes")
        self.update_status("JIRA notes cleared.", COLOR_OK)

    def add_jira_note(self, text):
        note = text.strip()
        if not note:
            return
        self.jira_raw_notes.append(note)
        self.refresh_raw_notes_text()
        self.jira_tabs.set("Raw Notes")

    def generate_jira_from_notes(self):
        if self.is_recording or self.model_loading or self.refreshing_models or self.generating_jira:
            return
        notes = "\n\n".join(self.jira_raw_notes).strip()
        if not notes:
            self.update_status("No Raw Notes to generate JIRA output.", COLOR_WARN)
            return
        if self.text_requires_key() and not self.get_openai_api_key():
            self.update_status("JIRA MODE needs an API key for the selected text provider. Open Settings.", COLOR_WARN)
            return

        self.generating_jira = True
        self.set_mode_button_states()
        self.set_hold_button_busy("GENERATING JIRA...")
        self.update_status("Generating Customer Comment and Internal Note...", COLOR_INFO)
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
        self.jira_tabs.set("Customer")
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(f"Customer Comment copied in {elapsed:.1f}s.", COLOR_OK)

    def fail_generate_jira(self, error_text):
        self.generating_jira = False
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(f"JIRA generation error: {error_text}", COLOR_ERROR)

    def refresh_output_panel(self):
        if self.jira_mode:
            self.result_text.pack_forget()
            self.jira_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        else:
            self.jira_frame.pack_forget()
            self.result_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 8))

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
        self.route_label.configure(text=self.current_route_status())
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
        self.route_label.configure(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_hold_button_idle()
        self.set_mode_button_states()
        if enabled:
            if self.text_requires_key() and not self.get_openai_api_key():
                self.update_status("JIRA MODE needs an API key for the selected text provider. Open Settings.", COLOR_WARN)
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
            self.route_label.configure(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_mode_button_states()

    def set_output_target(self, target_key, update_status=True):
        if self.is_recording or self.model_loading or target_key not in OUTPUT_TARGETS:
            return
        self.output_target = target_key
        if hasattr(self, "output_var"):
            self.output_var.set(LANGUAGE_LABELS.get(target_key, "English"))
        if update_status:
            self.route_label.configure(text=self.current_route_status())
        self.refresh_defaults_label()
        self.set_mode_button_states()

    def refresh_defaults_label(self):
        default_mode_label = MODES.get(self.default_mode_key, MODES["slow"])["label"]
        input_label = LANGUAGES.get(self.default_input_language, LANGUAGES["en"])["label"]
        output_label = OUTPUT_TARGETS.get(self.default_output_target, OUTPUT_TARGETS["en"])["label"]
        jira_label = " + JIRA" if self.default_jira_mode else ""
        self.defaults_label.configure(text=f"Default: {default_mode_label} + {input_label} → {output_label}{jira_label}")

    def idle_button_text(self):
        if self.jira_mode:
            return "ADD NOTE  ·  JIRA MODE"
        if self.silence_timeout_seconds() is None:
            return "PRESS TO TALK  ·  click again to stop"
        return "PRESS TO TALK  ·  auto-stops on silence"

    def text_provider_short(self):
        return {"openai": "Cloud", "ollama": "Local", "custom": "Custom"}.get(self.text_provider, "Cloud")

    def current_route_status(self):
        input_name = LANGUAGES[self.input_language]["name"]
        output_name = LANGUAGES[self.output_target]["name"]
        mode_label = " | JIRA MODE" if self.jira_mode else ""
        timeout = self.silence_timeout_label()
        text_ai = ""
        if self.jira_mode or self.input_language != self.output_target:
            text_ai = f" | Text AI: {self.text_provider_short()}"
        return f"{self.mode['status']} | Input: {input_name} | Output: {output_name}{mode_label} | Silence: {timeout}{text_ai}"

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
        text_provider = settings.get("text_provider", "openai")
        if text_provider not in ("openai", "ollama", "custom"):
            text_provider = "openai"
        text_model = str(settings.get("text_model", "")).strip()
        text_base_url = str(settings.get("text_base_url", "")).strip()
        return {
            "default_mode": default_mode,
            "default_input_language": default_input_language,
            "default_output": default_output,
            "default_jira_mode": default_jira_mode,
            "silence_timeout": silence_timeout,
            "api_key": settings.get("api_key", "").strip(),
            "text_provider": text_provider,
            "text_model": text_model,
            "text_base_url": text_base_url,
        }

    def write_settings(self):
        settings = {
            "default_mode": self.default_mode_key,
            "default_input_language": self.default_input_language,
            "default_output": self.default_output_target,
            "default_jira_mode": self.default_jira_mode,
            "silence_timeout": self.silence_timeout_setting,
            "api_key": self.configured_api_key,
            "text_provider": self.text_provider,
            "text_model": self.text_model,
            "text_base_url": self.text_base_url,
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
            COLOR_OK,
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

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("BananaPhone Settings")
        dialog.geometry("520x720")
        dialog.configure(fg_color=COLOR_WINDOW)
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)

        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=20)

        ctk.CTkLabel(
            body,
            text="Silence timeout",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TITLE,
        ).pack(anchor="w")

        silence_var = tk.StringVar(value=self.silence_timeout_setting)
        timeout_frame = ctk.CTkFrame(body, fg_color="transparent")
        timeout_frame.pack(anchor="w", pady=(6, 16))
        for value, label in (("4", "4s"), ("7", "7s"), ("10", "10s"), ("off", "Off")):
            ctk.CTkRadioButton(
                timeout_frame,
                text=label,
                value=value,
                variable=silence_var,
                font=ctk.CTkFont(size=12),
                fg_color=BTN_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER,
            ).pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(
            body,
            text="OpenAI API key",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TITLE,
        ).pack(anchor="w")

        key_var = tk.StringVar(value=self.configured_api_key)
        key_entry = ctk.CTkEntry(
            body,
            textvariable=key_var,
            show="*",
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_FIELD,
            border_color=COLOR_CARD_BORDER,
            corner_radius=8,
        )
        key_entry.pack(fill=tk.X, pady=(6, 4))

        ctk.CTkLabel(
            body,
            text="Stored only in ~/.config/bananafone/settings_v2.json. Env/file fallback still works.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTLE,
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # --- Text AI provider (translation + Jira) ----------------------
        ctk.CTkLabel(
            body,
            text="Text AI  —  translation & Jira",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TITLE,
        ).pack(anchor="w")

        provider_var = tk.StringVar(value=TEXT_PROVIDER_LABELS.get(self.text_provider, "OpenAI (cloud)"))
        model_var = tk.StringVar(value=self.text_model)
        baseurl_var = tk.StringVar(value=self.text_base_url)

        provider_menu = ctk.CTkOptionMenu(
            body,
            variable=provider_var,
            values=list(TEXT_PROVIDERS.keys()),
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_FIELD,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            corner_radius=8,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=BTN_PRIMARY,
        )
        provider_menu.pack(fill=tk.X, pady=(6, 8))

        ctk.CTkLabel(
            body, text="Model", font=ctk.CTkFont(size=11), text_color=COLOR_MUTED
        ).pack(anchor="w")
        model_entry = ctk.CTkEntry(
            body,
            textvariable=model_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_FIELD,
            border_color=COLOR_CARD_BORDER,
            corner_radius=8,
        )
        model_entry.pack(fill=tk.X, pady=(2, 6))

        ctk.CTkLabel(
            body, text="Server URL", font=ctk.CTkFont(size=11), text_color=COLOR_MUTED
        ).pack(anchor="w")
        baseurl_entry = ctk.CTkEntry(
            body,
            textvariable=baseurl_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_FIELD,
            border_color=COLOR_CARD_BORDER,
            corner_radius=8,
        )
        baseurl_entry.pack(fill=tk.X, pady=(2, 6))

        local_model_hint = ctk.CTkLabel(
            body,
            text=(
                "Ollama (local): pick the model above, then click Download local model. "
                "If Ollama isn't installed, the app offers to install it for you (you approve "
                "a system prompt), starts it, then downloads the model. No API key; the model "
                "is freed from RAM after each call. Cloud is faster; local keeps audio and "
                "tickets on this machine."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTLE,
            wraplength=460,
            justify="left",
        )
        local_model_hint.pack(anchor="w", pady=(0, 16))

        local_model_row = ctk.CTkFrame(body, fg_color="transparent")
        pull_button = ctk.CTkButton(
            local_model_row,
            text="Download local model",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
        )
        pull_button.pack(side=tk.LEFT)
        pull_status = ctk.CTkLabel(
            local_model_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_MUTED,
            wraplength=300,
            justify="left",
        )
        pull_status.pack(side=tk.LEFT, padx=(10, 0))

        def ollama_root_from(base):
            base = base.strip().rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3].rstrip("/")
            return base

        def reachable(root_url):
            try:
                urllib.request.urlopen(
                    urllib.request.Request(root_url + "/api/tags"), timeout=3
                ).read()
                return True
            except Exception:
                return False

        def set_status(message, color):
            if pull_status.winfo_exists():
                pull_status.configure(text=message, text_color=color)

        def finish_pull(message, color):
            set_status(message, color)
            if pull_button.winfo_exists():
                pull_button.configure(state="normal", text="Download local model")

        def do_pull(root_url, model):
            # Streams `ollama pull` over the local daemon API. No privilege needed.
            try:
                data = json.dumps({"name": model}).encode("utf-8")
                request = urllib.request.Request(
                    root_url + "/api/pull",
                    data=data,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=3600) as resp:
                    for raw in resp:
                        line = raw.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("error"):
                            self.root.after(0, finish_pull, f"Pull error: {str(obj['error'])[:80]}", COLOR_ERROR)
                            return
                        status = obj.get("status", "")
                        total = obj.get("total")
                        completed = obj.get("completed")
                        if total and completed:
                            msg = f"{status} {completed * 100 / total:.0f}%"
                        else:
                            msg = status
                        self.root.after(0, set_status, msg, COLOR_INFO)
                self.root.after(0, finish_pull, f"Model '{model}' ready.", COLOR_OK)
            except Exception as exc:
                self.root.after(0, finish_pull, f"Pull failed: {str(exc)[:80]}", COLOR_ERROR)

        def wait_until_reachable(root_url, attempts=30, delay=1.0):
            for _ in range(attempts):
                if reachable(root_url):
                    return True
                time.sleep(delay)
            return False

        def ensure_serving(root_url):
            # Best-effort: binary present but daemon down -> launch it detached.
            if reachable(root_url) or not shutil.which("ollama"):
                return
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                pass

        def install_ollama_cmd():
            # Platform-specific elevated install. None = can't auto-install here.
            system = platform.system()
            if system == "Windows":
                if shutil.which("winget"):
                    return [
                        "winget", "install", "--id", "Ollama.Ollama", "--source", "winget",
                        "--accept-package-agreements", "--accept-source-agreements", "--silent",
                    ]
            elif system == "Linux":
                if shutil.which("pkexec"):
                    return ["pkexec", "sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]
            elif system == "Darwin":
                if shutil.which("brew"):
                    return ["brew", "install", "ollama"]
            return None

        def install_worker(root_url, model):
            cmd = install_ollama_cmd()
            if cmd is None:
                self.root.after(0, finish_pull,
                                "Can't auto-install here. Get Ollama from ollama.com, then click again.",
                                COLOR_ERROR)
                return
            self.root.after(0, set_status, "Installing Ollama runtime (approve the prompt)...", COLOR_WARN)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            except Exception as exc:
                self.root.after(0, finish_pull, f"Install failed: {str(exc)[:80]}", COLOR_ERROR)
                return
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")
                self.root.after(0, finish_pull, f"Install failed: {detail[:80] or 'see logs'}", COLOR_ERROR)
                return
            # Linux installer starts the systemd service; Windows auto-starts.
            self.root.after(0, set_status, "Starting Ollama...", COLOR_WARN)
            ensure_serving(root_url)
            if not wait_until_reachable(root_url):
                self.root.after(0, finish_pull,
                                "Ollama installed but not responding yet. Start it, then click again.",
                                COLOR_ERROR)
                return
            do_pull(root_url, model)

        def start_worker(root_url, model):
            # Daemon installed but not reachable: bring it up, then pull.
            self.root.after(0, set_status, "Starting Ollama...", COLOR_WARN)
            ensure_serving(root_url)
            if wait_until_reachable(root_url, attempts=10):
                do_pull(root_url, model)
            else:
                self.root.after(0, finish_pull,
                                "Ollama is installed but won't start. Start it manually, then click again.",
                                COLOR_ERROR)

        def prompt_install(root_url, model):
            elevation = (
                "." if platform.system() == "Windows"
                else " and may ask for your password."
            )
            ok = messagebox.askyesno(
                "Install Ollama runtime?",
                "Ollama is not installed. Install it now to run the text model fully offline?\n\n"
                "This downloads and installs the Ollama runtime" + elevation + "\n\n"
                "The app keeps working in Cloud/API mode if you decline.",
                parent=dialog,
            )
            if not ok:
                finish_pull("Skipped. Cloud/API mode still works.", COLOR_MUTED)
                return
            threading.Thread(target=install_worker, args=(root_url, model), daemon=True).start()

        def after_preflight(state, root_url, model):
            if state == "reachable":
                threading.Thread(target=do_pull, args=(root_url, model), daemon=True).start()
            elif state == "installed_stopped":
                threading.Thread(target=start_worker, args=(root_url, model), daemon=True).start()
            else:  # missing
                prompt_install(root_url, model)

        def preflight_worker(root_url, model):
            if reachable(root_url):
                state = "reachable"
            elif shutil.which("ollama"):
                state = "installed_stopped"
            else:
                state = "missing"
            self.root.after(0, after_preflight, state, root_url, model)

        def start_pull():
            model = model_var.get().strip()
            if not model:
                pull_status.configure(text="Set a model name first.", text_color=COLOR_WARN)
                return
            root_url = ollama_root_from(baseurl_var.get())
            pull_button.configure(state="disabled", text="Working...")
            pull_status.configure(text="Checking Ollama...", text_color=COLOR_WARN)
            threading.Thread(target=preflight_worker, args=(root_url, model), daemon=True).start()

        pull_button.configure(command=start_pull)

        def update_local_row(provider_key):
            if provider_key == "ollama":
                local_model_row.pack(anchor="w", pady=(0, 16), before=local_model_hint)
            else:
                local_model_row.pack_forget()

        def on_provider_change(label):
            key = TEXT_PROVIDERS.get(label, "openai")
            model_var.set(PROVIDER_DEFAULT_MODEL.get(key, DEFAULT_OPENAI_TEXT_MODEL))
            baseurl_var.set(PROVIDER_DEFAULT_BASE_URL.get(key, DEFAULT_OPENAI_BASE_URL))
            update_local_row(key)

        provider_menu.configure(command=on_provider_change)
        update_local_row(self.text_provider)

        ctk.CTkLabel(
            body,
            text="Local speech models",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TITLE,
        ).pack(anchor="w")

        self.refresh_button = ctk.CTkButton(
            body,
            text="Download Models",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=10,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            command=self.refresh_models,
        )
        self.refresh_button.pack(anchor="w", pady=(6, 18))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(side=tk.BOTTOM, anchor="e")

        def save_settings():
            self.silence_timeout_setting = silence_var.get()
            self.configured_api_key = key_var.get().strip()
            self.text_provider = TEXT_PROVIDERS.get(provider_var.get(), "openai")
            self.text_model = model_var.get().strip() or PROVIDER_DEFAULT_MODEL.get(
                self.text_provider, DEFAULT_OPENAI_TEXT_MODEL
            )
            self.text_base_url = baseurl_var.get().strip() or PROVIDER_DEFAULT_BASE_URL.get(
                self.text_provider, DEFAULT_OPENAI_BASE_URL
            )
            self.write_settings()
            self.route_label.configure(text=self.current_route_status())
            self.set_hold_button_idle()
            self.update_status("Settings saved.", COLOR_OK)
            dialog.destroy()
            if self.mode.get("backend") == "openai" and self.model is None:
                self.ensure_model_loaded_async(self.mode_key)

        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=90,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            corner_radius=10,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            command=dialog.destroy,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(
            buttons,
            text="Save",
            width=90,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            corner_radius=10,
            fg_color=BTN_GOOD,
            hover_color=BTN_GOOD_HOVER,
            command=save_settings,
        ).pack(side=tk.LEFT)

    def ensure_model_loaded_async(self, mode_key):
        if self.model_key_loaded == mode_key and self.model is not None:
            self.update_status(f"{self.mode['label']} mode ready.", COLOR_OK)
            self.set_hold_button_idle()
            self.refresh_cache_status()
            return

        self.model_loading = True
        self.update_status(f"Loading {MODES[mode_key]['label']} mode...", COLOR_WARN)
        self.set_hold_button_busy("LOADING...", TALK_LOADING)
        self.set_mode_button_states()
        threading.Thread(target=self.load_mode_resources, args=(mode_key,), daemon=True).start()

    def load_mode_resources(self, mode_key):
        try:
            mode = MODES[mode_key]
            started = time.time()
            source = sr.Microphone()
            with source as mic_source:
                self.root.after(0, self.update_status, "Calibrating ambient noise...", COLOR_WARN)
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
        self.update_status(f"{self.mode['label']} mode ready in {elapsed:.1f}s.", COLOR_OK)

    def fail_loading_mode(self, error_text):
        self.model_loading = False
        self.set_mode_button_states()
        self.set_hold_button_busy("LOAD ERROR · check the log", TALK_FAIL)
        self.update_status(f"Load error: {error_text}", COLOR_ERROR)

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
        self.update_status(status, COLOR_OK)
        self.recording_thread = threading.Thread(target=self.capture_audio_loop, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_requested = True
        self.hotkey_recording = False

        self.set_hold_button_busy("TRANSCRIBING...")
        self.update_status(f"Transcribing with {self.mode['label']} mode...", COLOR_INFO)
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
        self.update_status("No audio captured. Try again.", COLOR_ERROR)

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
            COLOR_OK,
        )

    def after_transcription_error(self, error_text):
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(error_text, COLOR_ERROR)

    def handle_capture_failure(self, error_text):
        self.is_recording = False
        self.stop_requested = False
        self.hotkey_recording = False
        self.audio_chunks = []
        self.set_mode_button_states()
        self.set_hold_button_idle()
        self.update_status(error_text, COLOR_ERROR)

    def get_model_cache_path(self, model_name):
        return os.path.join(HF_CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")

    def is_model_cached(self, model_name):
        return os.path.isdir(self.get_model_cache_path(model_name))

    def refresh_cache_status(self):
        small = "ok" if self.is_model_cached("small") else "missing"
        medium = "ok" if self.is_model_cached("medium") else "missing"
        self.cache_label.configure(text=f"Models: small {small} | medium {medium} | API cloud")

    def refresh_models(self):
        if self.model_loading or self.is_recording or self.refreshing_models:
            return

        self.refreshing_models = True
        self.config_refresh_button(state="disabled", text="Downloading...")
        self.update_status("Downloading or updating local models...", COLOR_WARN)
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

    def text_requires_key(self):
        # Local Ollama needs no API key; cloud/custom OpenAI-compatible do.
        return self.text_provider != "ollama"

    def text_chat_url(self):
        return self.text_base_url.rstrip("/") + "/chat/completions"

    def run_text_chat(self, messages, json_mode=False, timeout=90):
        model = self.text_model or PROVIDER_DEFAULT_MODEL.get(self.text_provider, DEFAULT_OPENAI_TEXT_MODEL)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.text_provider == "ollama":
            # Free the model from RAM right after the call (load-on-demand).
            payload["keep_alive"] = 0
        else:
            api_key = self.get_openai_api_key()
            if not api_key:
                raise RuntimeError("Text provider needs an API key. Open Settings.")
            headers["Authorization"] = f"Bearer {api_key}"

        request = urllib.request.Request(
            self.text_chat_url(),
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Text HTTP {exc.code}: {details[:160]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Text provider unreachable ({self.text_provider}): {exc.reason}")

        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

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

        source_name = LANGUAGES[source_language]["name"]
        target_name = LANGUAGES[target_language]["name"]
        system_prompt = (
            f"You convert dictated {source_name} into natural, professional {target_name}. "
            "Preserve meaning, names, numbers, times, technical terms, and message intent. "
            "Fix obvious dictation artifacts and produce text a human would actually send. "
            f"Output only the final {target_name} text."
        )

        return self.run_text_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ]
        )

    def transform_to_jira(self, text):
        source_name = LANGUAGES[self.input_language]["name"]
        language_name = LANGUAGES[self.output_target]["name"]
        system_prompt = (
            f"You are a senior IT support engineer turning dictated ticket notes from {source_name} "
            f"into clean Jira documentation written in {language_name}. The dictation is raw, "
            "spoken, and may be out of order or contain speech-to-text artifacts. Your job is to "
            "reconstruct a coherent ticket from it.\n\n"
            "Return STRICT JSON ONLY, no markdown, no prose outside the JSON, with exactly two keys: "
            "customer_comment and internal_note.\n\n"
            "=== customer_comment (PUBLIC — the end user reads this) ===\n"
            "- Address the user directly and professionally.\n"
            "- Empathetic and reassuring, never robotic, never cold.\n"
            "- NO jargon, NO tool names, NO commands, NO internal blame, NO root-cause minutiae.\n"
            "- Confirm what was done in plain language and what the user can expect next.\n"
            "- 2-4 sentences. Tight. No filler openers like 'I hope this finds you well'.\n\n"
            "=== internal_note (PRIVATE — support team only) ===\n"
            "- Full technical picture for a peer engineer. Direct, matter-of-fact, no softening.\n"
            "- Structure it under these labels, each on its own line, omitting any with no real content:\n"
            "  Issue: what was reported.\n"
            "  Investigation: what was checked and how.\n"
            "  Actions: concrete steps taken (include tools, commands, config changes, hostnames, "
            "ticket/asset IDs exactly as dictated).\n"
            "  Result: current state — resolved, workaround in place, or pending.\n"
            "  Follow-up: anything to monitor or do next. Write 'None' if truly nothing.\n\n"
            "=== HARD RULES ===\n"
            "- NEVER invent facts, numbers, names, error codes, or outcomes not present in the dictation. "
            "Preserve every identifier (names, times, IPs, ticket IDs, error codes) verbatim.\n"
            "- If the dictation does not describe a completed resolution, do NOT pretend the ticket is "
            "closed: write Result as a progress update and reflect that in the customer_comment.\n"
            "- If the dictation is too thin to fill a section, leave it out rather than padding it.\n"
            "- Both fields must be written in fluent, native-level {language_name}.\n"
        ).replace("{language_name}", language_name)

        content = self.run_text_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            json_mode=True,
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
        self.config_refresh_button(state="normal", text="Download Models")
        self.refresh_cache_status()
        self.update_status(f"Models ready: {', '.join(results)}", COLOR_OK)
        self.set_mode_button_states()

    def fail_refresh_models(self, error_text):
        self.refreshing_models = False
        self.config_refresh_button(state="normal", text="Download Models")
        self.refresh_cache_status()
        self.update_status(f"Download/update failed: {error_text}", COLOR_ERROR)
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
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        root = ctk.CTk()
        app = DictationApp(root)
        root.mainloop()
    except Exception:
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write("\n[FATAL] Bananafone failed before or during GUI startup\n")
            traceback.print_exc(file=log)
        raise
