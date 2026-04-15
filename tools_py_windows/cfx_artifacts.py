from __future__ import annotations

import importlib.util
import re
import webbrowser
import tarfile
import zipfile
import subprocess
import sys
import threading
import platform
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:
    raise RuntimeError("tkinter est requis pour ouvrir l'interface. Installez le support Tk pour votre Python.") from exc

REQUIRED_MODULES = [("requests", "requests"), ("bs4", "beautifulsoup4"), ("py7zr", "py7zr")]
DEFAULT_RUNTIME_URL_WINDOWS = "https://runtime.fivem.net/artifacts/fivem/build_server_windows/master/"
DEFAULT_RUNTIME_URL_LINUX = "https://runtime.fivem.net/artifacts/fivem/build_proot_linux/master/"
ARTIFACT_DB_API = "https://artifacts.jgscripts.com/jsonv2"
ARTIFACT_CHECK_API = "https://artifacts.jgscripts.com/check"

def ensure_modules() -> None:
    missing = []
    for module_name, pip_name in REQUIRED_MODULES:
        if importlib.util.find_spec(module_name) is None: missing.append((module_name, pip_name))
    if not missing: return
    for module_name, pip_name in missing:
        try: subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Impossible d'installer la bibliotheque requise '{pip_name}' ({module_name}).") from exc


ensure_modules()

import requests
from bs4 import BeautifulSoup
import py7zr


@dataclass(slots=True)
class ArtifactInfo:
    artifact: str
    archive_name: str
    modified_at: str
    url: str
    status: str = "UNKNOWN"
    reason: str = ""


class FiveMArtifactLister:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Liste des artefacts FiveM")
        self.root.geometry("1040x720")
        self.root.minsize(900, 600)

        self.artifacts: list[ArtifactInfo] = []
        self.artifact_by_item: dict[str, ArtifactInfo] = {}
        self.tree_item_order: list[str] = []
        self.api_broken_rules: list[tuple[int | None, int | None, str]] = []
        self.recommended_artifact = ""
        self.recommended_windows_link = ""
        self.recommended_linux_link = ""
        self.download_dir = tk.StringVar(value="")
        self.url_var = tk.StringVar(value=DEFAULT_RUNTIME_URL_WINDOWS)
        self.source_mode = tk.StringVar(value="windows")
        self.filter_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Pret")
        self.selection_var = tk.StringVar(value="Aucun artefact selectionne")
        self.recommended_var = tk.StringVar(value="Recommande: --")
        self.windows_link_var = tk.StringVar(value="Windows: --")
        self.linux_link_var = tk.StringVar(value="Linux: --")
        self.source_badge_var = tk.StringVar(value="windows actif")
        self.api_status_var = tk.StringVar(value="API: en attente")
        self.loading_label = None
        self.loading_bar = None
        self.main_frames: list[ttk.Frame] = []
        self.loading_frame: ttk.Frame | None = None
        self.use_custom_chrome = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        self._configure_theme()
        self._build_ui()
        self.root.update_idletasks()
        self._apply_native_dark_titlebar()
        if platform.system() == "Windows":
            self.root.bind("<Map>", lambda _event: self._apply_native_dark_titlebar())
        self._show_loading("Chargement initial des artefacts...")
        self.root.after(100, self.load_artifacts)

    def _apply_native_dark_titlebar(self) -> None:
        if platform.system() != "Windows":
            return

        try:
            import ctypes
            from ctypes import byref, c_int, sizeof
            from ctypes import wintypes

            hwnd = self.root.winfo_id()
            value = c_int(1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    wintypes.HWND(hwnd),
                    wintypes.DWORD(attr),
                    byref(value),
                    sizeof(value),
                )
        except Exception:
            pass

    def _configure_theme(self) -> None:
        try:
            self.root.tk.call("source", "azure-dark.tcl")
            self.root.tk.call("set_theme", "dark")
        except tk.TclError:
            pass

        self.colors = {
            "bg": "#080a0d",
            "panel": "#0f1317",
            "panel_alt": "#14191e",
            "border": "#1e242c",
            "text": "#d4d7da",
            "muted": "#6f7680",
            "accent": "#707780",
            "accent_2": "#59626d",
            "danger": "#f87171",
            "warning": "#fbbf24",
            "chrome": "#0b0e12",
            "chrome_alt": "#11151b",
            "chrome_border": "#1a2027",
        }

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg=self.colors["bg"])
        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], fieldbackground=self.colors["panel"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["panel"], relief="flat")
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        style.configure("Card.TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure(
            "Badge.TLabel",
            background="#12171c",
            foreground=self.colors["muted"],
            padding=(10, 4),
        )
        style.configure("TEntry", fieldbackground=self.colors["panel"], foreground=self.colors["text"])
        style.configure("TButton", padding=(12, 8))
        style.configure("Accent.TButton", padding=(12, 8), background="#141a20", foreground=self.colors["text"])
        style.configure("Source.TButton", padding=(10, 6), background="#0d1115", foreground=self.colors["muted"])
        style.configure("SourceActive.TButton", padding=(10, 6), background="#161b21", foreground=self.colors["text"])
        style.map(
            "Accent.TButton",
            background=[("active", "#181e25"), ("pressed", "#1c2229")],
            foreground=[("active", "#efefeb"), ("pressed", "#efefeb")],
        )
        style.map(
            "Source.TButton",
            background=[("active", "#12171c"), ("pressed", "#151a20")],
            foreground=[("active", "#aeb4bc")],
        )
        style.map(
            "SourceActive.TButton",
            background=[("active", "#1b2128"), ("pressed", "#1f262e")],
            foreground=[("active", "#f2f2ef")],
        )
        style.map(
            "TButton",
            foreground=[("active", self.colors["text"])],
            background=[("active", "#151a20")],
        )
        style.configure(
            "Treeview",
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            rowheight=30,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
            relief="flat",
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#1d232b"), ("pressed", "#202731")],
            foreground=[("active", "#f3f3ef"), ("pressed", "#ffffff")],
        )
        style.map("Treeview", background=[("selected", "#131820")], foreground=[("selected", "#f3f3ef")])
        style.configure(
            "Vertical.TScrollbar",
            background="#131921",
            troughcolor=self.colors["bg"],
            arrowcolor=self.colors["muted"],
        )
        style.configure("Horizontal.TProgressbar", troughcolor="#11151a", background="#565d67")

    def _build_ui(self) -> None:
        self.root.configure(bg=self.colors["bg"])

        if self.use_custom_chrome:
            self.root.overrideredirect(True)
            self.root.rowconfigure(0, weight=0)
            self.root.rowconfigure(1, weight=1)
            self.root.columnconfigure(0, weight=1)
            self.chrome_frame = tk.Frame(
                self.root,
                bg=self.colors["chrome"],
                highlightthickness=1,
                highlightbackground=self.colors["chrome_border"],
                bd=0,
            )
            self.chrome_frame.grid(row=0, column=0, sticky="ew")
            self.chrome_frame.columnconfigure(0, weight=1)

            self.chrome_frame.bind("<ButtonPress-1>", self._begin_window_drag)
            self.chrome_frame.bind("<B1-Motion>", self._drag_window)

            title_wrap = tk.Frame(self.chrome_frame, bg=self.colors["chrome"])
            title_wrap.grid(row=0, column=0, sticky="ew", padx=10, pady=6)
            title_wrap.columnconfigure(0, weight=1)
            title_wrap.bind("<ButtonPress-1>", self._begin_window_drag)
            title_wrap.bind("<B1-Motion>", self._drag_window)

            title_text = tk.Label(
                title_wrap,
                text="Liste des artefacts FiveM",
                bg=self.colors["chrome"],
                fg=self.colors["text"],
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            title_text.grid(row=0, column=0, sticky="w")
            title_text.bind("<ButtonPress-1>", self._begin_window_drag)
            title_text.bind("<B1-Motion>", self._drag_window)

            window_controls = tk.Frame(title_wrap, bg=self.colors["chrome"])
            window_controls.grid(row=0, column=1, sticky="e")

            self._add_chrome_button(window_controls, "_", self.root.iconify)
            self._add_chrome_button(window_controls, "X", self.root.destroy, danger=True)

            self.main_container = ttk.Frame(self.root, style="TFrame")
            self.main_container.grid(row=1, column=0, sticky="nsew")
        else:
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            self.main_container = ttk.Frame(self.root, style="TFrame")
            self.main_container.grid(row=0, column=0, sticky="nsew")

        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(0, weight=1)

        self.content_frame = ttk.Frame(self.main_container, style="TFrame")
        self.content_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(2, weight=1)

        card_pad = 14

        self.loading_frame = ttk.Frame(self.main_container, style="Card.TFrame", padding=card_pad + 8)
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.columnconfigure(0, weight=1)
        self.loading_frame.rowconfigure(0, weight=1)
        self.loading_frame.grid_remove()

        loading_card = ttk.Frame(self.loading_frame, style="Card.TFrame")
        loading_card.grid(row=0, column=0)
        loading_card.columnconfigure(0, weight=1)

        self.loading_label = ttk.Label(loading_card, text="Chargement...", style="Card.TLabel")
        self.loading_label.grid(row=0, column=0, sticky="w")

        self.loading_bar = ttk.Progressbar(loading_card, mode="indeterminate")
        self.loading_bar.grid(row=1, column=0, sticky="ew", pady=(16, 0))

        top = ttk.Frame(self.content_frame, padding=card_pad, style="Card.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Source", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        source_buttons = ttk.Frame(top, style="Card.TFrame")
        source_buttons.grid(row=0, column=1, sticky="w", padx=(8, 8))
        source_buttons.columnconfigure(0, weight=1)
        source_buttons.columnconfigure(1, weight=1)
        source_buttons.columnconfigure(2, weight=0)
        self.windows_source_button = ttk.Button(
            source_buttons, text="Windows", style="SourceActive.TButton", command=lambda: self.set_runtime_source("windows")
        )
        self.windows_source_button.grid(row=0, column=0, padx=(0, 1), sticky="ew")
        self.linux_source_button = ttk.Button(
            source_buttons, text="Linux", style="Source.TButton", command=lambda: self.set_runtime_source("linux")
        )
        self.linux_source_button.grid(row=0, column=1, padx=(1, 0), sticky="ew")
        ttk.Label(source_buttons, textvariable=self.source_badge_var, style="Badge.TLabel").grid(
            row=0, column=2, padx=(10, 0), sticky="w"
        )
        ttk.Button(top, text="Recharger", style="Accent.TButton", command=self.load_artifacts).grid(row=0, column=2, sticky="e")

        ttk.Label(top, textvariable=self.url_var, style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Separator(top, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        ttk.Label(top, text="Recherche", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        filter_entry = ttk.Entry(top, textvariable=self.filter_var)
        filter_entry.grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=(12, 0))
        filter_entry.bind("<KeyRelease>", lambda _event: self.apply_filter())

        ttk.Button(top, text="Verifier selection", style="Accent.TButton", command=self.verify_selected_artifact).grid(
            row=3, column=2, sticky="e", pady=(12, 0)
        )

        info = ttk.Frame(self.content_frame, padding=(card_pad, 0, card_pad, 8), style="Card.TFrame")
        info.grid(row=1, column=0, sticky="ew")
        info.columnconfigure(0, weight=1)

        api_panel = ttk.Frame(info, style="Card.TFrame", padding=16)
        api_panel.grid(row=0, column=0, sticky="ew")
        api_panel.columnconfigure(0, weight=1)
        api_panel.columnconfigure(1, weight=1)

        header_row = ttk.Frame(api_panel, style="Card.TFrame")
        header_row.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_row.columnconfigure(0, weight=1)
        header_row.columnconfigure(1, weight=1)
        ttk.Label(header_row, textvariable=self.recommended_var, style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header_row, textvariable=self.api_status_var, style="Card.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(api_panel, textvariable=self.windows_link_var, wraplength=980, justify="left", style="Card.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Label(api_panel, textvariable=self.linux_link_var, wraplength=980, justify="left", style="Card.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(2, 0)
        )
        links_row = ttk.Frame(api_panel, style="Card.TFrame")
        links_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        links_row.columnconfigure(0, weight=1)
        links_row.columnconfigure(1, weight=1)
        ttk.Button(links_row, text="Ouvrir Windows", style="Accent.TButton", command=self.open_windows_link).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(links_row, text="Copier Windows", style="Source.TButton", command=self.copy_windows_link).grid(
            row=0, column=1, sticky="e"
        )
        ttk.Button(links_row, text="Ouvrir Linux", style="Accent.TButton", command=self.open_linux_link).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(links_row, text="Copier Linux", style="Source.TButton", command=self.copy_linux_link).grid(
            row=1, column=1, sticky="e", pady=(8, 0)
        )

        mid = ttk.Frame(self.content_frame, padding=(card_pad, 0, card_pad, card_pad), style="Card.TFrame")
        mid.grid(row=2, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        columns = ("artifact", "archive", "modified", "status", "reason")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("artifact", text="Artifact", command=lambda: self.sort_tree("artifact", False))
        self.tree.heading("archive", text="Archive", command=lambda: self.sort_tree("archive", False))
        self.tree.heading("modified", text="Modifie", command=lambda: self.sort_tree("modified", False))
        self.tree.heading("status", text="Statut", command=lambda: self.sort_tree("status", False))
        self.tree.heading("reason", text="Problème connu", command=lambda: self.sort_tree("reason", False))
        self.tree.column("artifact", width=130, anchor="center", stretch=False)
        self.tree.column("archive", width=120, anchor="center", stretch=False)
        self.tree.column("modified", width=160, anchor="center", stretch=False)
        self.tree.column("status", width=120, anchor="center", stretch=False)
        self.tree.column("reason", width=500, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        self.tree.bind("<Double-1>", lambda _event: self.download_selected_artifact())

        tree_scroll = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        bottom = ttk.Frame(self.content_frame, padding=card_pad, style="Card.TFrame")
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(1, weight=1)

        ttk.Label(bottom, text="Selection").grid(row=0, column=0, sticky="w")
        ttk.Label(bottom, textvariable=self.selection_var).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(bottom, text="Dossier de telechargement").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(bottom, textvariable=self.download_dir).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Button(bottom, text="Choisir", command=self.choose_download_directory).grid(
            row=1, column=2, sticky="e", pady=(10, 0)
        )

        action_row = ttk.Frame(bottom)
        action_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        action_row.columnconfigure(2, weight=1)

        ttk.Button(action_row, text="Telecharger selection", style="Accent.TButton", command=self.download_selected_artifact).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(action_row, text="Telecharger recommande Windows", style="Accent.TButton", command=self.download_recommended_windows).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(action_row, text="Telecharger recommande Linux", style="Accent.TButton", command=self.download_recommended_linux).grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )

        ttk.Label(bottom, textvariable=self.status_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.main_frames = [top, info, mid, bottom]
        self._update_source_button_styles()

    def _show_loading(self, text: str) -> None:
        for frame in self.main_frames:
            frame.grid_remove()
        if self.loading_frame is not None:
            self.loading_frame.lift()
            self.loading_frame.grid()
        if self.loading_label is None or self.loading_bar is None:
            return
        self.loading_label.configure(text=text)
        self.loading_bar.start(10)

    def _set_loading_text(self, text: str) -> None:
        if self.loading_label is not None:
            self.loading_label.configure(text=text)

    def _add_chrome_button(self, parent: tk.Misc, text: str, command, danger: bool = False) -> None:
        if command == self.root.iconify:
            command = self._minimize_window
        bg = "#12171c" if not danger else "#1d1111"
        fg = self.colors["text"] if not danger else "#f2c0c0"
        active_bg = "#1b2128" if not danger else "#351717"
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
            padx=10,
            pady=4,
            highlightthickness=0,
        )
        button.pack(side="right", padx=(6, 0))

    def _begin_window_drag(self, event: tk.Event) -> None:
        self._drag_offset_x = event.x_root - self.root.winfo_x()
        self._drag_offset_y = event.y_root - self.root.winfo_y()

    def _drag_window(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def _minimize_window(self) -> None:
        if not self.use_custom_chrome:
            self.root.iconify()
            return

        self._chrome_override_enabled = False
        self.root.overrideredirect(False)
        self.root.iconify()

    def _on_window_map(self, _event: tk.Event) -> None:
        if not self.use_custom_chrome:
            return
        if self.root.state() == "normal" and not self._chrome_override_enabled:
            self.root.overrideredirect(True)
            self._chrome_override_enabled = True
            self.root.lift()
            self.root.focus_force()

    def _hide_loading(self) -> None:
        if self.loading_bar is not None:
            self.loading_bar.stop()
        if self.loading_frame is not None:
            self.loading_frame.grid_remove()
        self.content_frame.lift()
        for frame in self.main_frames:
            frame.grid()

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def set_runtime_source(self, source: str) -> None:
        source = source.lower().strip()
        if source not in {"windows", "linux"}:
            return

        self.source_mode.set(source)
        if source == "windows":
            self.url_var.set(DEFAULT_RUNTIME_URL_WINDOWS)
        else:
            self.url_var.set(DEFAULT_RUNTIME_URL_LINUX)
        self.source_badge_var.set(f"{source} actif")
        self._update_source_button_styles()
        self._set_status(f"Source activee: {source}")

    def _update_source_button_styles(self) -> None:
        if not hasattr(self, "windows_source_button") or not hasattr(self, "linux_source_button"):
            return
        if self.source_mode.get() == "windows":
            self.windows_source_button.configure(style="SourceActive.TButton")
            self.linux_source_button.configure(style="Source.TButton")
        else:
            self.windows_source_button.configure(style="Source.TButton")
            self.linux_source_button.configure(style="SourceActive.TButton")

    def _copy_text(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def open_windows_link(self) -> None:
        if self.recommended_windows_link:
            webbrowser.open(self.recommended_windows_link)

    def open_linux_link(self) -> None:
        if self.recommended_linux_link:
            webbrowser.open(self.recommended_linux_link)

    def copy_windows_link(self) -> None:
        if self.recommended_windows_link:
            self._copy_text(self.recommended_windows_link)
            self._set_status("Lien Windows copie")

    def copy_linux_link(self) -> None:
        if self.recommended_linux_link:
            self._copy_text(self.recommended_linux_link)
            self._set_status("Lien Linux copie")

    def _request_json(self, url: str, timeout: int = 20) -> dict:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def load_artifacts(self) -> None:
        self._show_loading("Chargement de la liste initiale...")
        self._set_status("Chargement en cours...")
        if self.tree_item_order:
            self.tree.delete(*self.tree_item_order)
        self.artifacts.clear()
        self.artifact_by_item.clear()
        self.tree_item_order.clear()

        worker = threading.Thread(target=self._load_artifacts_worker, daemon=True)
        worker.start()

    def _load_artifacts_worker(self) -> None:
        try:
            api_data = self._request_json(ARTIFACT_DB_API)
            self.api_broken_rules = self._build_broken_rules(api_data.get("brokenArtifacts", []))
            self.recommended_artifact = str(api_data.get("recommendedArtifact", "")).strip()
            self.recommended_windows_link = str(api_data.get("windowsDownloadLink", "")).strip()
            self.recommended_linux_link = str(api_data.get("linuxDownloadLink", "")).strip()
            self.root.after(0, self._update_api_labels)

            runtime_url = self.url_var.get().strip() or DEFAULT_RUNTIME_URL_WINDOWS
            response = requests.get(runtime_url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            artifacts = self._extract_artifacts(soup, runtime_url)
            self.root.after(0, self._apply_artifacts, artifacts)
        except Exception as exc:
            self.root.after(0, self._handle_load_error, exc)

    def _build_broken_rules(self, broken_artifacts: list[dict]) -> list[tuple[int | None, int | None, str]]:
        rules: list[tuple[int | None, int | None, str]] = []
        for entry in broken_artifacts:
            artifact_key = str(entry.get("artifact", "")).strip()
            reason = str(entry.get("reason", "")).strip()
            if artifact_key:
                start, end = self._parse_artifact_range(artifact_key)
                rules.append((start, end, reason))
        return rules

    def _update_api_labels(self) -> None:
        if self.recommended_artifact:
            self.recommended_var.set(f"Recommande: {self.recommended_artifact}")
        else:
            self.recommended_var.set("Recommande: --")
        self.windows_link_var.set(
            f"Windows: {self.recommended_windows_link}" if self.recommended_windows_link else "Windows: --"
        )
        self.linux_link_var.set(
            f"Linux: {self.recommended_linux_link}" if self.recommended_linux_link else "Linux: --"
        )
        self.api_status_var.set(f"API: {len(self.api_broken_rules)} artefacts signales")

    def _extract_artifacts(self, soup: BeautifulSoup, base_url: str) -> list[ArtifactInfo]:
        artifacts: dict[str, ArtifactInfo] = {}
        for link in soup.find_all("a"):
            href = link.get("href") or ""
            if not href.lower().endswith((".zip", ".7z")):
                continue

            full_url = urljoin(base_url, href)
            artifact_number = self._parse_artifact_number(full_url) or self._parse_artifact_number(href)
            if not artifact_number:
                artifact_number = Path(href).stem

            archive_name = Path(href).name
            modified_at = self._extract_modified_at(link)

            reason = self._get_broken_reason(artifact_number)
            status = "BROKEN" if reason else "OK"
            artifacts[artifact_number] = ArtifactInfo(
                artifact=artifact_number,
                archive_name=archive_name,
                modified_at=modified_at,
                url=full_url,
                status=status,
                reason=reason,
            )

        def sort_key(item: ArtifactInfo) -> tuple[int, str]:
            artifact_value = self._safe_int(item.artifact)
            return (artifact_value, item.artifact)

        return sorted(artifacts.values(), key=sort_key, reverse=True)

    def _parse_artifact_number(self, value: str) -> str:
        match = re.search(r"(\d{4,})", value)
        return match.group(1) if match else ""

    def _extract_modified_at(self, link: tk.Misc) -> str:
        level_item = link.select_one(".level-right .level-item")
        if level_item:
            return " ".join(level_item.get_text(" ", strip=True).split())
        return ""

    def _parse_artifact_range(self, value: str) -> tuple[int | None, int | None]:
        value = value.strip()
        if "-" in value:
            left, right = value.split("-", 1)
            return self._to_int_or_none(left), self._to_int_or_none(right)
        artifact = self._to_int_or_none(value)
        return artifact, artifact

    def _to_int_or_none(self, value: str) -> int | None:
        try:
            return int(value.strip())
        except ValueError:
            return None

    def _get_broken_reason(self, artifact_number: str) -> str:
        artifact_value = self._safe_int(artifact_number)
        if artifact_value < 0:
            return ""

        for start, end, reason in self.api_broken_rules:
            if start is None and end is None:
                continue
            if start is not None and end is not None and start <= artifact_value <= end:
                return reason
            if start is not None and end is None and artifact_value == start:
                return reason
            if end is not None and start is None and artifact_value == end:
                return reason
        return ""

    def _safe_int(self, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return -1

    def _apply_artifacts(self, artifacts: list[ArtifactInfo]) -> None:
        self._hide_loading()
        self.artifacts = artifacts
        if self.tree_item_order:
            self.tree.delete(*self.tree_item_order)
        self.artifact_by_item.clear()
        self.tree_item_order.clear()

        for artifact in artifacts:
            reason = artifact.reason or ""
            item_id = self.tree.insert(
                "",
                "end",
                values=(artifact.artifact, artifact.archive_name, artifact.modified_at, artifact.status, reason),
            )
            self.artifact_by_item[item_id] = artifact
            self.tree_item_order.append(item_id)

        self._set_status(f"{len(artifacts)} artefacts charges")
        self.apply_filter()
        self._select_first_visible_row()

    def _handle_load_error(self, exc: Exception) -> None:
        self._hide_loading()
        self._set_status("Erreur de chargement")
        messagebox.showerror("Erreur", f"Impossible de charger les artefacts: {exc}")

    def apply_filter(self) -> None:
        query = self.filter_var.get().strip().lower()
        visible_items = set(self.tree.get_children(""))
        for item_id in self.tree_item_order:
            values = self.tree.item(item_id, "values")
            haystack = " ".join(values).lower()
            should_show = not query or query in haystack

            if should_show and item_id not in visible_items:
                self.tree.reattach(item_id, "", "end")
            elif not should_show and item_id in visible_items:
                self.tree.detach(item_id)

        self._select_first_visible_row()

    def _select_first_visible_row(self) -> None:
        visible_items = self.tree.get_children("")
        if not visible_items:
            self.selection_var.set("Aucun artefact selectionne")
            return

        first_item = visible_items[0]
        if first_item not in self.tree.selection():
            self.tree.selection_set(first_item)
        self.tree.focus(first_item)
        self.tree.see(first_item)

    def sort_tree(self, column: str, reverse: bool) -> None:
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]

        def sort_value(value: str) -> tuple[int, str]:
            if column == "artifact":
                return (self._safe_int(value), value)
            if column == "modified":
                return (0, value)
            return (0, value.lower())

        items.sort(key=lambda pair: sort_value(pair[0]), reverse=reverse)

        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

        self.tree.heading(column, command=lambda: self.sort_tree(column, not reverse))

    def on_selection_change(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            self.selection_var.set("Aucun artefact selectionne")
            return

        item_id = selected[0]
        artifact = self.artifact_by_item.get(item_id)
        if not artifact:
            self.selection_var.set("Aucun artefact selectionne")
            return

        self.selection_var.set(
            f"{artifact.artifact} | {artifact.archive_name} | {artifact.modified_at or 'Date inconnue'} | {artifact.status} | {artifact.reason or 'Aucun probleme signale'}"
        )

    def choose_download_directory(self) -> None:
        directory = filedialog.askdirectory(title="Choisir le dossier de telechargement")
        if directory:
            self.download_dir.set(directory)

    def _selected_artifact(self) -> ArtifactInfo | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.artifact_by_item.get(selected[0])

    def _create_artifact_from_download_link(self, artifact_number: str, url: str) -> ArtifactInfo:
        return ArtifactInfo(
            artifact=artifact_number or "recommended",
            archive_name=Path(url).name,
            modified_at="",
            url=url,
            status="OK",
            reason="",
        )

    def _start_download(self, artifact: ArtifactInfo, verify: bool) -> None:
        if not self.download_dir.get():
            self.choose_download_directory()
            if not self.download_dir.get():
                return

        self._show_loading(f"Telechargement de {artifact.artifact}...")
        threading.Thread(target=self._download_worker, args=(artifact, verify), daemon=True).start()

    def verify_selected_artifact(self) -> None:
        artifact = self._selected_artifact()
        if not artifact:
            messagebox.showwarning("Selection requise", "Selectionnez un artefact dans la liste.")
            return

        self._show_loading(f"Verification de l'artefact {artifact.artifact}...")
        threading.Thread(target=self._verify_selected_worker, args=(artifact,), daemon=True).start()

    def _verify_selected_worker(self, artifact: ArtifactInfo) -> None:
        try:
            response = self._request_json(f"{ARTIFACT_CHECK_API}?artifact={artifact.artifact}")
            self.root.after(0, self._apply_verification_result, artifact.artifact, response)
        except Exception as exc:
            self.root.after(0, self._verification_error, exc)

    def _apply_verification_result(self, artifact_number: str, response: dict) -> None:
        self._hide_loading()
        status = str(response.get("status", "UNKNOWN")).upper()
        reason = str(response.get("reason", "")).strip()

        if status == "BROKEN":
            messagebox.showwarning(
                "Probleme connu",
                f"L'artefact {artifact_number} a des problemes connus:\n\n{reason}",
            )
        else:
            messagebox.showinfo("Verification", f"L'artefact {artifact_number} ne remonte aucun probleme connu.")

    def _verification_error(self, exc: Exception) -> None:
        self._hide_loading()
        messagebox.showerror("Erreur", f"Echec de la verification API: {exc}")

    def download_selected_artifact(self) -> None:
        artifact = self._selected_artifact()
        if artifact is None:
            messagebox.showwarning("Selection requise", "Veuillez selectionner un artefact a telecharger.")
            return

        self._start_download(artifact, verify=True)

    def download_recommended_windows(self) -> None:
        if not self.recommended_windows_link:
            messagebox.showwarning("Recommande indisponible", "Le lien Windows recommande n'est pas disponible.")
            return
        artifact = self._create_artifact_from_download_link(self.recommended_artifact, self.recommended_windows_link)
        self._start_download(artifact, verify=False)

    def download_recommended_linux(self) -> None:
        if not self.recommended_linux_link:
            messagebox.showwarning("Recommande indisponible", "Le lien Linux recommande n'est pas disponible.")
            return
        artifact = self._create_artifact_from_download_link(self.recommended_artifact, self.recommended_linux_link)
        self._start_download(artifact, verify=False)

    def _download_worker(self, artifact: ArtifactInfo, verify: bool) -> None:
        try:
            if verify:
                verification = self._request_json(f"{ARTIFACT_CHECK_API}?artifact={artifact.artifact}")
                if str(verification.get("status", "OK")).upper() == "BROKEN":
                    reason = str(verification.get("reason", "")).strip() or "Probleme connu"
                    self.root.after(0, self._download_broken_warning, artifact, reason)
                    return

            destination_dir = Path(self.download_dir.get()).expanduser()
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / Path(artifact.url).name

            with requests.get(artifact.url, stream=True, timeout=30) as response:
                response.raise_for_status()
                with destination.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            file_handle.write(chunk)

            extract_dir = destination_dir / f"{artifact.artifact}_extracted"
            extracted_path = self._extract_archive(destination, extract_dir)
            self.root.after(0, self._download_success, artifact, str(destination), extracted_path)
        except Exception as exc:
            self.root.after(0, self._download_error, exc)

    def _download_broken_warning(self, artifact: ArtifactInfo, reason: str) -> None:
        self._hide_loading()
        answer = messagebox.askyesno(
            "Artefact avec probleme",
            f"L'artefact {artifact.artifact} a des problemes connus:\n\n{reason}\n\nVoulez-vous continuer le telechargement ?",
        )
        if answer:
            self._show_loading(f"Telechargement de {artifact.artifact}...")
            threading.Thread(target=self._download_without_warning, args=(artifact,), daemon=True).start()

    def _download_without_warning(self, artifact: ArtifactInfo) -> None:
        try:
            destination_dir = Path(self.download_dir.get()).expanduser()
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / Path(artifact.url).name

            with requests.get(artifact.url, stream=True, timeout=30) as response:
                response.raise_for_status()
                with destination.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            file_handle.write(chunk)

            extract_dir = destination_dir / f"{artifact.artifact}_extracted"
            extracted_path = self._extract_archive(destination, extract_dir)
            self.root.after(0, self._download_success, artifact, str(destination), extracted_path)
        except Exception as exc:
            self.root.after(0, self._download_error, exc)

    def _extract_archive(self, archive_path: Path, extract_dir: Path) -> str:
        extract_dir.mkdir(parents=True, exist_ok=True)
        suffix = archive_path.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_dir)
        elif suffix == ".7z":
            with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                archive.extractall(path=extract_dir)
        elif archive_path.name.endswith(".tar.xz") or archive_path.name.endswith(".tar.gz") or archive_path.name.endswith(".tgz"):
            with tarfile.open(archive_path, mode="r:*") as archive:
                archive.extractall(extract_dir)
        else:
            return ""
        return str(extract_dir)

    def _download_success(self, artifact: ArtifactInfo, destination: str, extracted_path: str) -> None:
        self._hide_loading()
        if extracted_path:
            self._set_status(f"Telechargement termine: {destination} + extraction")
            messagebox.showinfo(
                "Succes",
                f"Artefact {artifact.artifact} telecharge vers:\n{destination}\n\nContenu extrait vers:\n{extracted_path}",
            )
        else:
            self._set_status(f"Telechargement termine: {destination}")
            messagebox.showinfo("Succes", f"Artefact {artifact.artifact} telecharge vers:\n{destination}")

    def _download_error(self, exc: Exception) -> None:
        self._hide_loading()
        self._set_status("Erreur de telechargement")
        messagebox.showerror("Erreur", f"Erreur lors du telechargement: {exc}")


def main() -> None:
    root = tk.Tk()
    FiveMArtifactLister(root)
    root.mainloop()


if __name__ == "__main__":
    main()
