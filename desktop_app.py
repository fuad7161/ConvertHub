"""
Desktop UI for the text-to-audio generator.

Run:
    python desktop_app.py

This UI reuses the same synthesis pipeline from main.py.
"""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import pygame

from main import DEFAULT_VOICE, EMOTION_PRESETS, normalize_text, text_to_audio

VOICE_OPTIONS = {
    "en-US-ChristopherNeural (Male)": "en-US-ChristopherNeural",
    "en-US-GuyNeural (Male)": "en-US-GuyNeural",
    "en-US-JennyNeural (Female)": "en-US-JennyNeural",
    "en-US-AriaNeural (Female)": "en-US-AriaNeural",
    "en-GB-SoniaNeural (Female)": "en-GB-SoniaNeural",
}

DEFAULT_VOICE_LABEL = next(
    (label for label, voice_id in VOICE_OPTIONS.items() if voice_id == DEFAULT_VOICE),
    "en-US-ChristopherNeural (Male)",
)


class TextToAudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Text to Audio Studio")
        self.root.geometry("1200x820")
        self.root.minsize(1040, 740)

        self.is_generating = False
        self.generated_files: list[Path] = []
        self.is_paused = False
        self.storage_placeholder = "Add folder to store audio"
        self.storage_entry: tk.Entry | None = None

        self.input_file_var = tk.StringVar(value="input.txt")
        self.output_file_var = tk.StringVar(value="")
        self.storage_folder_var = tk.StringVar(value=self.storage_placeholder)
        self.theme_var = tk.StringVar(value="System")
        self.voice_var = tk.StringVar(value=DEFAULT_VOICE_LABEL)
        self.emotion_var = tk.StringVar(value="neutral")
        self.rate_var = tk.StringVar(value="")
        self.pitch_var = tk.StringVar(value="")
        self.volume_var = tk.StringVar(value="")
        self.max_chars_var = tk.StringVar(value="2600")
        self.retries_var = tk.StringVar(value="3")
        self.retry_delay_var = tk.StringVar(value="1.2")
        self.auto_expression_var = tk.BooleanVar(value=True)
        self.selected_audio_var = tk.StringVar(value="No audio selected")
        self.char_count_var = tk.StringVar(value="Characters: 0")
        self.status_var = tk.StringVar(value="Ready")

        self.player_ready = False
        self.style = ttk.Style(self.root)
        self._init_player()

        self._setup_styles()
        self._build_ui()
        self._apply_theme(self.theme_var.get())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_player(self) -> None:
        try:
            pygame.mixer.init()
            self.player_ready = True
        except Exception:
            self.player_ready = False

    def _setup_styles(self) -> None:
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("Section.TLabelframe", padding=10)
        self.style.configure("Generate.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 8))
        self.style.configure("Icon.TButton", font=("Segoe UI Symbol", 13, "bold"), padding=(8, 4))

    def _detect_system_prefers_dark(self) -> bool:
        gtk_theme = os.environ.get("GTK_THEME", "").lower()
        if "dark" in gtk_theme:
            return True

        colorfgbg = os.environ.get("COLORFGBG", "")
        if colorfgbg:
            parts = colorfgbg.split(";")
            if parts and parts[-1].isdigit():
                try:
                    bg_index = int(parts[-1])
                    return bg_index <= 6
                except ValueError:
                    pass

        return False

    def _get_active_theme_mode(self, selected_mode: str) -> str:
        if selected_mode == "System":
            return "Dark" if self._detect_system_prefers_dark() else "Light"
        return selected_mode

    def _apply_theme(self, selected_mode: str) -> None:
        mode = self._get_active_theme_mode(selected_mode)

        if mode == "Dark":
            palette = {
                "root_bg": "#0b1020",
                "panel_bg": "#121a2b",
                "card_bg": "#1a2338",
                "title": "#eaf1ff",
                "subtitle": "#a7b5d6",
                "muted": "#93a2c8",
                "input_bg": "#0f172a",
                "input_fg": "#e5e7eb",
                "placeholder": "#7381a7",
                "button_bg": "#3b82f6",
                "button_active": "#2563eb",
                "button_fg": "#f8fbff",
                "tab_bg": "#141d31",
                "tab_selected": "#1f2a44",
                "tab_fg": "#c8d4f2",
                "tab_selected_fg": "#ffffff",
                "border": "#263352",
            }
        else:
            palette = {
                "root_bg": "#eef3fb",
                "panel_bg": "#ffffff",
                "card_bg": "#ffffff",
                "title": "#1f3b73",
                "subtitle": "#3b4c6b",
                "muted": "#5f6368",
                "input_bg": "#ffffff",
                "input_fg": "#111111",
                "placeholder": "#7a7a7a",
                "button_bg": "#2f6feb",
                "button_active": "#2559bb",
                "button_fg": "#ffffff",
                "tab_bg": "#dde8fb",
                "tab_selected": "#ffffff",
                "tab_fg": "#234070",
                "tab_selected_fg": "#12264a",
                "border": "#c4d5f2",
            }

        self.root.configure(bg=palette["root_bg"])

        self.style.configure("TFrame", background=palette["root_bg"])
        self.style.configure("TLabel", background=palette["root_bg"], foreground=palette["input_fg"])
        self.style.configure(
            "TButton",
            background=palette["card_bg"],
            foreground=palette["input_fg"],
            bordercolor=palette["border"],
            lightcolor=palette["card_bg"],
            darkcolor=palette["card_bg"],
        )
        self.style.map("TButton", background=[("active", palette["tab_selected"])])
        self.style.configure(
            "TEntry",
            fieldbackground=palette["input_bg"],
            foreground=palette["input_fg"],
            bordercolor=palette["border"],
            insertcolor=palette["input_fg"],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=palette["input_bg"],
            background=palette["input_bg"],
            foreground=palette["input_fg"],
            arrowcolor=palette["input_fg"],
            bordercolor=palette["border"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["input_bg"]), ("!disabled", palette["input_bg"])],
            foreground=[("readonly", palette["input_fg"]), ("!disabled", palette["input_fg"])],
            selectbackground=[("readonly", palette["input_bg"]), ("!disabled", palette["input_bg"])],
            selectforeground=[("readonly", palette["input_fg"]), ("!disabled", palette["input_fg"])],
        )
        self.style.configure(
            "TNotebook",
            background=palette["root_bg"],
            borderwidth=0,
            tabmargins=(2, 4, 2, 0),
        )
        self.style.configure(
            "TNotebook.Tab",
            background=palette["tab_bg"],
            foreground=palette["tab_fg"],
            padding=(10, 5),
            bordercolor=palette["border"],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", palette["tab_selected"]), ("active", palette["tab_selected"])],
            foreground=[("selected", palette["tab_selected_fg"]), ("active", palette["tab_selected_fg"])],
            padding=[("selected", (14, 8)), ("!selected", (10, 5))],
        )
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=palette["title"], background=palette["root_bg"])
        self.style.configure("SubTitle.TLabel", font=("Segoe UI", 10), foreground=palette["subtitle"], background=palette["root_bg"])
        self.style.configure("Section.TLabelframe", background=palette["root_bg"], borderwidth=1, relief="solid", bordercolor=palette["border"])
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=palette["title"], background=palette["root_bg"])
        self.style.configure("Muted.TLabel", foreground=palette["muted"], background=palette["root_bg"])
        self.style.configure("Generate.TButton", foreground=palette["button_fg"], background=palette["button_bg"], bordercolor=palette["button_bg"])
        self.style.map("Generate.TButton", background=[("active", palette["button_active"])])
        self.style.configure("Icon.TButton", foreground=palette["input_fg"], background=palette["card_bg"], bordercolor=palette["border"])
        self.style.map("Icon.TButton", background=[("active", palette["tab_selected"])])

        # Update tk widgets after they are created
        if hasattr(self, "text_editor"):
            self.text_editor.configure(
                bg=palette["input_bg"],
                fg=palette["input_fg"],
                insertbackground=palette["input_fg"],
                selectbackground="#3b82f6" if mode == "Dark" else "#cfe3ff",
                selectforeground=palette["input_fg"],
            )
        if hasattr(self, "history_list"):
            self.history_list.configure(
                bg=palette["input_bg"],
                fg=palette["input_fg"],
                selectbackground="#3b82f6" if mode == "Dark" else "#cfe3ff",
                selectforeground=palette["input_fg"],
                highlightthickness=0,
            )
        if self.storage_entry is not None:
            current_value = self.storage_folder_var.get().strip()
            use_placeholder = current_value == self.storage_placeholder or not current_value
            self.storage_entry.configure(
                bg=palette["input_bg"],
                highlightbackground=palette["border"],
                highlightcolor=palette["button_bg"],
                relief="flat",
                insertbackground=palette["input_fg"],
                fg=palette["placeholder"] if use_placeholder else palette["input_fg"],
            )

    def _on_theme_changed(self, _event: tk.Event | None = None) -> None:
        self._apply_theme(self.theme_var.get())

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=14, pady=(12, 8))
        ttk.Label(header, text="Text to Audio Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Paste text, choose options, generate speech, and play it instantly.",
            style="SubTitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=8)

        create_tab = ttk.Frame(notebook)
        player_tab = ttk.Frame(notebook)
        help_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)
        notebook.add(create_tab, text="Create Audio")
        notebook.add(player_tab, text="Player & History")
        notebook.add(help_tab, text="Quick Help")
        notebook.add(settings_tab, text="Settings")

        # Create tab layout (responsive on resize)
        paned = ttk.Panedwindow(create_tab, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        left_panel = ttk.Frame(paned)
        right_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=3)
        paned.add(right_panel, weight=2)

        file_frame = ttk.LabelFrame(left_panel, text="File Paths", style="Section.TLabelframe")
        file_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(file_frame, text="Input file").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(file_frame, textvariable=self.input_file_var).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(file_frame, text="Browse", command=self._browse_input_file).grid(row=0, column=2, **pad)
        ttk.Button(file_frame, text="Load", command=self._load_input_file).grid(row=0, column=3, **pad)

        ttk.Label(file_frame, text="Output file").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(file_frame, textvariable=self.output_file_var).grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(file_frame, text="Browse", command=self._browse_output_file).grid(row=1, column=2, **pad)

        ttk.Label(file_frame, text="Storage folder").grid(row=2, column=0, sticky="w", **pad)
        self.storage_entry = tk.Entry(file_frame, textvariable=self.storage_folder_var, fg="#7a7a7a")
        self.storage_entry.grid(row=2, column=1, sticky="we", **pad)
        self.storage_entry.bind("<FocusIn>", self._on_storage_focus_in)
        self.storage_entry.bind("<FocusOut>", self._on_storage_focus_out)
        ttk.Button(file_frame, text="Pick Folder", command=self._browse_storage_folder).grid(row=2, column=2, **pad)
        file_frame.columnconfigure(1, weight=1)

        text_frame = ttk.LabelFrame(left_panel, text="Input Text", style="Section.TLabelframe")
        text_frame.pack(fill="both", expand=True)

        self.text_editor = ScrolledText(text_frame, wrap="word", height=13, font=("Segoe UI", 11))
        self.text_editor.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        self.text_editor.bind("<KeyRelease>", lambda _e: self._update_char_count())

        editor_actions = ttk.Frame(text_frame)
        editor_actions.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(editor_actions, text="Clear Text", command=self._clear_text).pack(side="left")
        ttk.Label(editor_actions, textvariable=self.char_count_var, style="Muted.TLabel").pack(side="right")

        voice_frame = ttk.LabelFrame(right_panel, text="Voice & Tone", style="Section.TLabelframe")
        voice_frame.pack(fill="x", pady=(0, 8))
        voice_frame.columnconfigure(1, weight=1)

        ttk.Label(voice_frame, text="Voice").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(
            voice_frame,
            textvariable=self.voice_var,
            values=list(VOICE_OPTIONS.keys()),
            width=24,
        ).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(voice_frame, text="Emotion preset").grid(row=1, column=0, sticky="w", **pad)
        ttk.Combobox(
            voice_frame,
            textvariable=self.emotion_var,
            values=list(EMOTION_PRESETS.keys()),
            width=14,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(voice_frame, text="Rate").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(voice_frame, textvariable=self.rate_var, width=16).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Label(voice_frame, text="Pitch").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(voice_frame, textvariable=self.pitch_var, width=16).grid(row=3, column=1, sticky="ew", **pad)
        ttk.Label(voice_frame, text="Volume").grid(row=4, column=0, sticky="w", **pad)
        ttk.Entry(voice_frame, textvariable=self.volume_var, width=16).grid(row=4, column=1, sticky="ew", **pad)

        stability_frame = ttk.LabelFrame(right_panel, text="Stability", style="Section.TLabelframe")
        stability_frame.pack(fill="x", pady=(0, 8))
        stability_frame.columnconfigure(1, weight=1)
        ttk.Label(stability_frame, text="Max chars/chunk").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(stability_frame, textvariable=self.max_chars_var, width=12).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Label(stability_frame, text="Retries").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(stability_frame, textvariable=self.retries_var, width=12).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Label(stability_frame, text="Retry delay (s)").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(stability_frame, textvariable=self.retry_delay_var, width=12).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Checkbutton(
            stability_frame,
            text="Auto-detect expression",
            variable=self.auto_expression_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 8))

        action_frame = ttk.LabelFrame(right_panel, text="Generate & Play", style="Section.TLabelframe")
        action_frame.pack(fill="x")
        self.generate_btn = ttk.Button(
            action_frame,
            text="⚡ Generate Audio",
            command=self._on_generate,
            style="Generate.TButton",
        )
        self.generate_btn.pack(fill="x", padx=8, pady=(8, 6))

        play_row = ttk.Frame(action_frame)
        play_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(play_row, text="▶", command=self._on_play, style="Icon.TButton", width=3).pack(side="left")
        ttk.Button(play_row, text="⏸", command=self._on_pause, style="Icon.TButton", width=3).pack(side="left", padx=(6, 0))
        ttk.Button(play_row, text="⏹", command=self._on_stop, style="Icon.TButton", width=3).pack(side="left", padx=(6, 0))

        ttk.Label(action_frame, text="Selected audio:", style="Muted.TLabel").pack(anchor="w", padx=8)
        ttk.Label(action_frame, textvariable=self.selected_audio_var, wraplength=290).pack(anchor="w", padx=8, pady=(0, 8))

        self.progress = ttk.Progressbar(action_frame, mode="indeterminate")
        self.progress.pack(fill="x", padx=8, pady=(0, 8))

        # Player/history tab
        history_frame = ttk.LabelFrame(player_tab, text="Generated Files", style="Section.TLabelframe")
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.history_list = tk.Listbox(history_frame, height=14)
        self.history_list.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        history_actions = ttk.Frame(history_frame)
        history_actions.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(history_actions, text="Use Selected", command=self._use_selected_history).pack(side="left")
        ttk.Button(history_actions, text="Play Selected", command=self._play_selected_history).pack(side="left", padx=6)

        # Help tab
        help_frame = ttk.LabelFrame(help_tab, text="How to Use", style="Section.TLabelframe")
        help_frame.pack(fill="both", expand=True, padx=10, pady=10)
        help_text = (
            "1) Paste your text in the Input Text box.\n"
            "2) Choose voice and optional tone controls.\n"
            "3) Click Generate Audio.\n"
            "4) Click Play to preview immediately.\n\n"
            "Tips:\n"
            "- Keep auto-detect expression ON for plain text.\n"
            "- Use retries if network is unstable.\n"
            "- Leave output blank for auto-named files in audio/."
        )
        ttk.Label(help_frame, text=help_text, justify="left").pack(anchor="nw", padx=10, pady=10)

        # Settings tab
        settings_frame = ttk.LabelFrame(settings_tab, text="Appearance", style="Section.TLabelframe")
        settings_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(settings_frame, text="Theme", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        theme_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.theme_var,
            values=["System", "Light", "Dark"],
            width=14,
            state="readonly",
        )
        theme_combo.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(status_bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")

        self._update_char_count()

    def _browse_input_file(self) -> None:
        path = filedialog.askopenfilename(title="Select input text file")
        if path:
            self.input_file_var.set(path)

    def _browse_output_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save output audio",
            defaultextension=".mp3",
            filetypes=[("MP3 Audio", "*.mp3")],
        )
        if path:
            self.output_file_var.set(path)

    def _browse_storage_folder(self) -> None:
        path = filedialog.askdirectory(title="Select folder to store generated audio")
        if path:
            self.storage_folder_var.set(path)
            if self.storage_entry is not None:
                self.storage_entry.configure(fg="#111111")

    def _on_storage_focus_in(self, _event: tk.Event) -> None:
        if self.storage_folder_var.get().strip() == self.storage_placeholder:
            self.storage_folder_var.set("")
            if self.storage_entry is not None:
                self.storage_entry.configure(fg="#111111")

    def _on_storage_focus_out(self, _event: tk.Event) -> None:
        if not self.storage_folder_var.get().strip():
            self.storage_folder_var.set(self.storage_placeholder)
            if self.storage_entry is not None:
                self.storage_entry.configure(fg="#7a7a7a")

    def _get_storage_folder_text(self) -> str:
        value = self.storage_folder_var.get().strip()
        if value == self.storage_placeholder:
            return ""
        return value

    def _load_input_file(self) -> None:
        path = Path(self.input_file_var.get().strip())
        if not path.exists():
            messagebox.showerror("Input file not found", f"File does not exist:\n{path}")
            return

        text = path.read_text(encoding="utf-8")
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", text)
        self.status_var.set(f"Loaded: {path}")

    def _clear_text(self) -> None:
        self.text_editor.delete("1.0", tk.END)
        self._update_char_count()

    def _update_char_count(self) -> None:
        text = self.text_editor.get("1.0", tk.END)
        self.char_count_var.set(f"Characters: {len(text.strip())}")

    def _set_selected_audio(self, output_path: Path) -> None:
        self.output_file_var.set(str(output_path))
        self.selected_audio_var.set(str(output_path))

    def _add_to_history(self, output_path: Path) -> None:
        if output_path not in self.generated_files:
            self.generated_files.append(output_path)
            self.history_list.insert(tk.END, str(output_path))

    def _get_selected_history_path(self) -> Path | None:
        selection = self.history_list.curselection()
        if not selection:
            return None
        selected_text = self.history_list.get(selection[0])
        return Path(selected_text)

    def _use_selected_history(self) -> None:
        path = self._get_selected_history_path()
        if path is None:
            messagebox.showinfo("No selection", "Select an audio file from history.")
            return
        self._set_selected_audio(path)
        self.status_var.set(f"Selected: {path}")

    def _play_selected_history(self) -> None:
        path = self._get_selected_history_path()
        if path is None:
            messagebox.showinfo("No selection", "Select an audio file from history.")
            return
        self._set_selected_audio(path)
        self._on_play()

    def _on_play(self) -> None:
        if not self.player_ready:
            messagebox.showerror(
                "Audio player unavailable",
                "pygame audio mixer could not be initialized.",
            )
            return

        audio_path = Path(self.output_file_var.get().strip())
        if not audio_path.exists():
            messagebox.showerror("Audio not found", "Generate audio first or select a valid output file.")
            return

        try:
            if self.is_paused and pygame.mixer.music.get_busy():
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.status_var.set("Resumed audio...")
                return

            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()
            self.is_paused = False
            self.selected_audio_var.set(str(audio_path))
            self.status_var.set("Playing audio...")
        except Exception as exc:
            messagebox.showerror("Play failed", str(exc))

    def _on_pause(self) -> None:
        if self.player_ready and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_paused = True
            self.status_var.set("Paused")

    def _on_stop(self) -> None:
        if self.player_ready:
            pygame.mixer.music.stop()
            self.is_paused = False
            self.status_var.set("Playback stopped")

    def _resolve_rate_pitch_volume(self) -> tuple[str, str, str]:
        preset = EMOTION_PRESETS[self.emotion_var.get()]
        rate = self.rate_var.get().strip() or preset["rate"]
        pitch = self.pitch_var.get().strip() or preset["pitch"]
        volume = self.volume_var.get().strip() or preset["volume"]
        return rate, pitch, volume

    def _resolve_output_path(self) -> Path:
        output_text = self.output_file_var.get().strip()
        storage_folder_text = self._get_storage_folder_text()
        timestamp = datetime.now().strftime("%Y-%m-%d:%H-%M-%S-%f")
        default_name = f"tts_{timestamp}.mp3"

        if output_text:
            output_candidate = Path(output_text).expanduser()

            # If user provides a folder path, save auto-named file inside that folder.
            if output_candidate.exists() and output_candidate.is_dir():
                return output_candidate / default_name
            if output_text.endswith(("/", "\\")):
                return output_candidate / default_name
            if output_candidate.suffix == "":
                return output_candidate / default_name

            # Otherwise treat it as an explicit file path.
            return output_candidate

        # If no output file is provided, place file in <selected-folder>/audio.
        if storage_folder_text:
            return Path(storage_folder_text).expanduser() / "audio" / default_name

        # Default fallback: OS Music/audio directory.
        return Path.home() / "Music" / "audio" / default_name

    def _on_generate(self) -> None:
        if self.is_generating:
            return

        raw_text = self.text_editor.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showerror("Missing text", "Please add text in the editor.")
            return

        try:
            max_chars = int(self.max_chars_var.get().strip())
            retries = int(self.retries_var.get().strip())
            retry_delay = float(self.retry_delay_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid numeric values", "Check max chars, retries, and retry delay.")
            return

        selected_voice_label = self.voice_var.get().strip()
        voice = VOICE_OPTIONS.get(selected_voice_label, DEFAULT_VOICE)
        rate, pitch, volume = self._resolve_rate_pitch_volume()
        output_path = self._resolve_output_path()
        text = normalize_text(raw_text)
        auto_expression = bool(self.auto_expression_var.get())

        self.is_generating = True
        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("Generating audio...")
        self.progress.start(8)

        thread = threading.Thread(
            target=self._generate_worker,
            args=(
                text,
                output_path,
                voice,
                rate,
                pitch,
                volume,
                max_chars,
                retries,
                retry_delay,
                auto_expression,
            ),
            daemon=True,
        )
        thread.start()

    def _generate_worker(
        self,
        text: str,
        output_path: Path,
        voice: str,
        rate: str,
        pitch: str,
        volume: str,
        max_chars: int,
        retries: int,
        retry_delay: float,
        auto_expression: bool,
    ) -> None:
        try:
            asyncio.run(
                text_to_audio(
                    text=text,
                    output_path=output_path,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume,
                    max_chars_per_chunk=max_chars,
                    retries=retries,
                    retry_delay=retry_delay,
                    auto_detect_expressions=auto_expression,
                )
            )
            self.root.after(0, self._on_generate_success, output_path)
        except Exception as exc:
            self.root.after(0, self._on_generate_error, str(exc))

    def _on_generate_success(self, output_path: Path) -> None:
        self.is_generating = False
        self.generate_btn.config(state=tk.NORMAL)
        self.progress.stop()
        self._set_selected_audio(output_path)
        self._add_to_history(output_path)
        self.status_var.set(f"Done: {output_path}")
        messagebox.showinfo("Success", f"Audio generated:\n{output_path}")

    def _on_generate_error(self, error_text: str) -> None:
        self.is_generating = False
        self.generate_btn.config(state=tk.NORMAL)
        self.progress.stop()
        self.status_var.set("Failed")
        messagebox.showerror("Generation failed", error_text)

    def _on_close(self) -> None:
        try:
            if self.player_ready:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        finally:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TextToAudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
