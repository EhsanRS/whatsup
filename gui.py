#!/usr/bin/env python3
"""WhatsUp Desktop GUI -- tkinter wrapper around the whatsup CLI."""

import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("tkinter is required. Install it with:")
    print("  sudo apt install python3-tk")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent

# ── Theme colours (IBM retro cream) ──────────────────────────────────

BG          = "#f5f0e8"
CARD_BG     = "#fffdf7"
TEXT        = "#2c2c2c"
MUTED       = "#8a8478"
ACCENT      = "#c8553d"
LINK_CLR    = "#2a5aa7"
BORDER      = "#d9d0c1"
SIDEBAR_BG  = "#eee8dc"
TAG_BG      = "#e8e0d4"
ERROR_BG    = "#fce4e0"

MOOD_COLORS = {
    "focused":    "#c8a032",
    "happy":      "#5a9a5a",
    "tired":      "#a0998e",
    "excited":    "#b85ca0",
    "frustrated": "#c8553d",
    "chill":      "#4a8eab",
    "thinking":   "#7b6baa",
    "creative":   "#d48840",
}

MOOD_EMOJI = {
    "focused": "\U0001f3af",
    "happy":   "\U0001f60a",
    "tired":   "\U0001f634",
    "excited": "\U0001f680",
    "frustrated": "\U0001f624",
    "chill":   "\U0001f60e",
    "thinking": "\U0001f914",
    "creative": "\U0001f3a8",
}

MOODS = ["", "focused", "happy", "tired", "excited", "frustrated", "chill", "thinking", "creative"]


class WhatsUpGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("whatsup")
        self.root.geometry("960x720")
        self.root.minsize(760, 520)
        self.root.configure(bg=BG)

        # State
        self.config = {"name": "WhatsUp", "bio": "", "avatar": "", "links": [], "timezone": "UTC"}
        self.manifest = []
        self.entries = []
        self.current_date = None
        self.tags = []
        self.edit_id = None
        self.server_proc = None
        self.timeline_widgets = []

        self._detect_font()
        self._load_config()
        self._load_manifest()

        # Pick latest date
        if self.manifest:
            dates = sorted([m["date"] for m in self.manifest], reverse=True)
            self.current_date = dates[0]
        else:
            self.current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        self._build_ui()
        self.load_timeline()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    # ── Helpers ───────────────────────────────────────────────────────

    def _detect_font(self):
        """Pick the best available monospace font."""
        self.font_family = "TkFixedFont"
        for candidate in ("IBM Plex Mono", "Consolas", "Courier New"):
            try:
                test = tk.Label(font=(candidate, 10))
                actual = test.cget("font")
                test.destroy()
                if candidate.lower().replace(" ", "") in actual.lower().replace(" ", ""):
                    self.font_family = candidate
                    break
            except Exception:
                continue

    def _load_config(self):
        path = SCRIPT_DIR / "config.json"
        if path.exists():
            try:
                self.config = json.loads(path.read_text())
            except Exception:
                pass

    def _load_manifest(self):
        path = SCRIPT_DIR / "data" / "index.json"
        if path.exists():
            try:
                self.manifest = json.loads(path.read_text())
            except Exception:
                self.manifest = []

    def _on_close(self):
        if self.server_proc:
            self.server_proc.terminate()
        self.root.destroy()

    # ── UI builders ──────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()

        # Main pane: sidebar + right area
        self.main_pane = tk.Frame(self.root, bg=BG)
        self.main_pane.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_sidebar()

        # Right side: compose + timeline
        self.right = tk.Frame(self.main_pane, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)

        self._build_compose()
        self._build_timeline()
        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=CARD_BG, height=44)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        brand = tk.Label(bar, text="whatsup", font=(self.font_family, 14, "bold"),
                         fg=ACCENT, bg=CARD_BG, cursor="hand2")
        brand.pack(side="left", padx=12)

        # Right side buttons
        btn_frame = tk.Frame(bar, bg=CARD_BG)
        btn_frame.pack(side="right", padx=8)

        self.serve_btn = tk.Button(btn_frame, text="Start Server", font=(self.font_family, 9),
                                   command=self.toggle_server, bg=BG, fg=TEXT, relief="solid",
                                   borderwidth=1, padx=8, pady=2, cursor="hand2")
        self.serve_btn.pack(side="right", padx=4)

        refresh_btn = tk.Button(btn_frame, text="Refresh", font=(self.font_family, 9),
                                command=self.refresh, bg=BG, fg=TEXT, relief="solid",
                                borderwidth=1, padx=8, pady=2, cursor="hand2")
        refresh_btn.pack(side="right", padx=4)

        # Date dropdown
        self.date_var = tk.StringVar(value=self.current_date or "")
        dates = sorted([m["date"] for m in self.manifest], reverse=True) if self.manifest else []
        if not dates:
            dates = [self.current_date]
        self.date_menu = ttk.Combobox(btn_frame, textvariable=self.date_var,
                                      values=dates, state="readonly", width=12,
                                      font=(self.font_family, 9))
        self.date_menu.pack(side="right", padx=4)
        self.date_menu.bind("<<ComboboxSelected>>", self._on_date_change)

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.main_pane, bg=SIDEBAR_BG, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Mood emoji (big)
        self.sidebar_emoji = tk.Label(self.sidebar, text="\U0001f4ad", font=(self.font_family, 36),
                                      bg=SIDEBAR_BG, fg=TEXT)
        self.sidebar_emoji.pack(pady=(24, 4))

        self.sidebar_mood = tk.Label(self.sidebar, text="no mood set", font=(self.font_family, 11),
                                     bg=SIDEBAR_BG, fg=MUTED)
        self.sidebar_mood.pack(pady=(0, 8))

        sep = tk.Frame(self.sidebar, bg=BORDER, height=1)
        sep.pack(fill="x", padx=20, pady=8)

        self.sidebar_name = tk.Label(self.sidebar, text=self.config.get("name", ""),
                                     font=(self.font_family, 13, "bold"), bg=SIDEBAR_BG, fg=TEXT)
        self.sidebar_name.pack(pady=(4, 0))

        self.sidebar_bio = tk.Label(self.sidebar, text=self.config.get("bio", ""),
                                    font=(self.font_family, 10), bg=SIDEBAR_BG, fg=MUTED)
        self.sidebar_bio.pack(pady=(2, 8))

        self.sidebar_date = tk.Label(self.sidebar, text="", font=(self.font_family, 10),
                                     bg=SIDEBAR_BG, fg=MUTED)
        self.sidebar_date.pack(pady=(4, 12))

        # Nav buttons
        nav = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        nav.pack(pady=4)

        self.prev_btn = tk.Button(nav, text="\u25c0 Prev", font=(self.font_family, 9),
                                  command=lambda: self._navigate(-1), bg=SIDEBAR_BG, fg=TEXT,
                                  relief="solid", borderwidth=1, padx=6, cursor="hand2")
        self.prev_btn.pack(side="left", padx=4)

        self.next_btn = tk.Button(nav, text="Next \u25b6", font=(self.font_family, 9),
                                  command=lambda: self._navigate(1), bg=SIDEBAR_BG, fg=TEXT,
                                  relief="solid", borderwidth=1, padx=6, cursor="hand2")
        self.next_btn.pack(side="left", padx=4)

    def _build_compose(self):
        wrapper = tk.Frame(self.right, bg=BG)
        wrapper.pack(fill="x", padx=12, pady=(8, 0))

        # Header row
        header = tk.Frame(wrapper, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="COMPOSE", font=(self.font_family, 9, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        self.compose_mode_label = tk.Label(header, text="", font=(self.font_family, 9),
                                           bg=BG, fg=ACCENT)
        self.compose_mode_label.pack(side="left", padx=8)

        # Card border
        outer = tk.Frame(wrapper, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="x", pady=(4, 0))
        card = tk.Frame(outer, bg=CARD_BG, padx=10, pady=8)
        card.pack(fill="x")

        # Content text
        self.content_text = tk.Text(card, height=3, font=(self.font_family, 11),
                                    bg=CARD_BG, fg=TEXT, wrap="word", relief="flat",
                                    insertbackground=TEXT, borderwidth=0)
        self.content_text.pack(fill="x", pady=(0, 6))
        self._add_placeholder(self.content_text, "What's up?")

        # Row 1: mood, tag, link, reply
        row1 = tk.Frame(card, bg=CARD_BG)
        row1.pack(fill="x", pady=2)

        tk.Label(row1, text="Mood:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left")
        self.mood_var = tk.StringVar(value="")
        mood_menu = ttk.Combobox(row1, textvariable=self.mood_var, values=MOODS,
                                 state="readonly", width=10, font=(self.font_family, 9))
        mood_menu.pack(side="left", padx=(2, 8))

        tk.Label(row1, text="Tag:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left")
        self.tag_entry = tk.Entry(row1, font=(self.font_family, 9), bg=BG, fg=TEXT,
                                  relief="solid", borderwidth=1, width=10)
        self.tag_entry.pack(side="left", padx=2)
        self.tag_entry.bind("<Return>", lambda e: self.add_tag())
        tag_add_btn = tk.Button(row1, text="+", font=(self.font_family, 9, "bold"),
                                command=self.add_tag, bg=BG, fg=TEXT, relief="solid",
                                borderwidth=1, padx=4, cursor="hand2")
        tag_add_btn.pack(side="left", padx=(0, 8))

        tk.Label(row1, text="Link:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left")
        self.link_entry = tk.Entry(row1, font=(self.font_family, 9), bg=BG, fg=TEXT,
                                   relief="solid", borderwidth=1, width=14)
        self.link_entry.pack(side="left", padx=2)

        tk.Label(row1, text="Reply:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left", padx=(8, 0))
        self.reply_entry = tk.Entry(row1, font=(self.font_family, 9), bg=BG, fg=TEXT,
                                    relief="solid", borderwidth=1, width=8)
        self.reply_entry.pack(side="left", padx=2)

        # Row 2: gif, pdf, post, clear
        row2 = tk.Frame(card, bg=CARD_BG)
        row2.pack(fill="x", pady=2)

        tk.Label(row2, text="GIF:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left")
        self.gif_entry = tk.Entry(row2, font=(self.font_family, 9), bg=BG, fg=TEXT,
                                  relief="solid", borderwidth=1, width=16)
        self.gif_entry.pack(side="left", padx=2)

        tk.Label(row2, text="PDF:", font=(self.font_family, 9), bg=CARD_BG, fg=MUTED).pack(side="left", padx=(8, 0))
        self.pdf_path_var = tk.StringVar(value="")
        self.pdf_label = tk.Label(row2, textvariable=self.pdf_path_var,
                                  font=(self.font_family, 9), bg=CARD_BG, fg=MUTED, width=12, anchor="w")
        self.pdf_label.pack(side="left", padx=2)
        tk.Button(row2, text="Browse", font=(self.font_family, 9), command=self.browse_pdf,
                  bg=BG, fg=TEXT, relief="solid", borderwidth=1, padx=4, cursor="hand2").pack(side="left")

        spacer = tk.Frame(row2, bg=CARD_BG)
        spacer.pack(side="left", expand=True, fill="x")

        self.post_btn = tk.Button(row2, text="Post", font=(self.font_family, 10, "bold"),
                                  command=self.do_post, bg=ACCENT, fg=CARD_BG, relief="flat",
                                  padx=12, pady=2, cursor="hand2")
        self.post_btn.pack(side="right", padx=(4, 0))

        tk.Button(row2, text="Clear", font=(self.font_family, 9), command=self.clear_compose,
                  bg=BG, fg=TEXT, relief="solid", borderwidth=1, padx=8, pady=2,
                  cursor="hand2").pack(side="right", padx=4)

        # Tag pills row
        self.tag_pill_frame = tk.Frame(card, bg=CARD_BG)
        self.tag_pill_frame.pack(fill="x", pady=(2, 0))

        # Keyboard shortcuts
        self.root.bind("<Control-Return>", lambda e: self.do_post())
        self.root.bind("<Escape>", lambda e: self.clear_compose())

    def _build_timeline(self):
        wrapper = tk.Frame(self.right, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=12, pady=(8, 0))

        tk.Label(wrapper, text="TIMELINE", font=(self.font_family, 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w")

        # Scrollable area
        self.timeline_canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0, borderwidth=0)
        self.timeline_scrollbar = tk.Scrollbar(wrapper, orient="vertical",
                                               command=self.timeline_canvas.yview)
        self.timeline_inner = tk.Frame(self.timeline_canvas, bg=BG)

        self.timeline_inner.bind("<Configure>",
                                 lambda e: self.timeline_canvas.configure(
                                     scrollregion=self.timeline_canvas.bbox("all")))

        self.canvas_window = self.timeline_canvas.create_window((0, 0), window=self.timeline_inner,
                                                                 anchor="nw")
        self.timeline_canvas.configure(yscrollcommand=self.timeline_scrollbar.set)

        self.timeline_scrollbar.pack(side="right", fill="y")
        self.timeline_canvas.pack(side="left", fill="both", expand=True)

        # Resize inner frame width to match canvas
        self.timeline_canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling
        self.timeline_canvas.bind_all("<MouseWheel>",
                                      lambda e: self.timeline_canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.timeline_canvas.bind_all("<Button-4>",
                                      lambda e: self.timeline_canvas.yview_scroll(-3, "units"))
        self.timeline_canvas.bind_all("<Button-5>",
                                      lambda e: self.timeline_canvas.yview_scroll(3, "units"))

    def _on_canvas_configure(self, event):
        self.timeline_canvas.itemconfig(self.canvas_window, width=event.width)

    def _build_statusbar(self):
        self.statusbar = tk.Label(self.root, text="Ready", font=(self.font_family, 9),
                                  bg=CARD_BG, fg=MUTED, anchor="w", padx=8, pady=4)
        self.statusbar.pack(fill="x", side="bottom")

    # ── Placeholder logic ────────────────────────────────────────────

    def _add_placeholder(self, widget, text):
        widget._placeholder = text
        widget._has_placeholder = True
        widget.insert("1.0", text)
        widget.configure(fg=MUTED)
        widget.bind("<FocusIn>", lambda e: self._clear_placeholder(widget))
        widget.bind("<FocusOut>", lambda e: self._restore_placeholder(widget))

    def _clear_placeholder(self, widget):
        if widget._has_placeholder:
            widget.delete("1.0", "end")
            widget.configure(fg=TEXT)
            widget._has_placeholder = False

    def _restore_placeholder(self, widget):
        content = widget.get("1.0", "end").strip()
        if not content:
            widget.insert("1.0", widget._placeholder)
            widget.configure(fg=MUTED)
            widget._has_placeholder = True

    # ── Tag management ───────────────────────────────────────────────

    def add_tag(self):
        tag = self.tag_entry.get().strip().lstrip("#")
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self._render_tag_pills()
        self.tag_entry.delete(0, "end")

    def remove_tag(self, tag):
        if tag in self.tags:
            self.tags.remove(tag)
            self._render_tag_pills()

    def _render_tag_pills(self):
        for w in self.tag_pill_frame.winfo_children():
            w.destroy()
        for tag in self.tags:
            pill = tk.Frame(self.tag_pill_frame, bg=TAG_BG, padx=6, pady=1,
                            relief="solid", borderwidth=1)
            pill.pack(side="left", padx=(0, 4), pady=1)
            tk.Label(pill, text=f"#{tag}", font=(self.font_family, 9), bg=TAG_BG, fg=TEXT).pack(side="left")
            close = tk.Label(pill, text=" \u2715", font=(self.font_family, 9), bg=TAG_BG,
                             fg=ACCENT, cursor="hand2")
            close.pack(side="left")
            close.bind("<Button-1>", lambda e, t=tag: self.remove_tag(t))

    # ── PDF browse ───────────────────────────────────────────────────

    def browse_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self.pdf_path_var.set(os.path.basename(path))
            self.pdf_path_var._full_path = path

    # ── Compose actions ──────────────────────────────────────────────

    def _get_content(self):
        text = self.content_text.get("1.0", "end").strip()
        if self.content_text._has_placeholder:
            return ""
        return text

    def do_post(self, _event=None):
        content = self._get_content()
        if not content:
            self.set_status("Content is required", error=True)
            return

        args = []

        if self.edit_id:
            args = ["--edit", self.edit_id, content]
        else:
            mood = self.mood_var.get()
            if mood:
                args.extend(["--mood", mood])

            link = self.link_entry.get().strip()
            if link:
                args.extend(["--link", link])

            reply = self.reply_entry.get().strip()
            if reply:
                args.extend(["--reply", reply])

            gif = self.gif_entry.get().strip()
            if gif:
                args.extend(["--gif", gif])

            pdf = getattr(self.pdf_path_var, "_full_path", "")
            if pdf:
                args.extend(["--pdf", pdf])

            for tag in self.tags:
                args.extend(["--tag", tag])

            args.append(content)

        self.set_status("Posting..." if not self.edit_id else "Saving edit...")
        self.post_btn.configure(state="disabled")

        def callback(ok, stdout, stderr):
            self.post_btn.configure(state="normal")
            if ok:
                action = "Saved" if self.edit_id else "Posted"
                self.set_status(f"{action}: {stdout.strip()}")
                self.clear_compose()
                self.refresh()
            else:
                self.set_status(f"Error: {stderr.strip()}", error=True)

        self.run_cli_async(args, callback)

    def do_delete(self, entry_id):
        if not messagebox.askyesno("Delete entry", f"Delete entry {entry_id}?"):
            return
        self.set_status("Deleting...")

        def callback(ok, stdout, stderr):
            if ok:
                self.set_status(f"Deleted {entry_id}")
                self.refresh()
            else:
                self.set_status(f"Error: {stderr.strip()}", error=True)

        self.run_cli_async(["--delete", entry_id], callback)

    def clear_compose(self, _event=None):
        self.content_text.delete("1.0", "end")
        self.content_text._has_placeholder = False
        self._restore_placeholder(self.content_text)
        self.mood_var.set("")
        self.tag_entry.delete(0, "end")
        self.link_entry.delete(0, "end")
        self.reply_entry.delete(0, "end")
        self.gif_entry.delete(0, "end")
        self.pdf_path_var.set("")
        if hasattr(self.pdf_path_var, "_full_path"):
            self.pdf_path_var._full_path = ""
        self.tags = []
        self._render_tag_pills()
        self.edit_id = None
        self.compose_mode_label.configure(text="")
        self.post_btn.configure(text="Post")

    def enter_edit_mode(self, entry):
        self.edit_id = entry["id"]
        self.compose_mode_label.configure(text=f"Editing {entry['id']}")
        self.post_btn.configure(text="Save")

        # Fill content
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", entry.get("content", ""))
        self.content_text.configure(fg=TEXT)
        self.content_text._has_placeholder = False

        # Clear other fields (edit only changes content)
        self.mood_var.set("")
        self.link_entry.delete(0, "end")
        self.reply_entry.delete(0, "end")
        self.gif_entry.delete(0, "end")
        self.pdf_path_var.set("")
        self.tags = []
        self._render_tag_pills()

        self.content_text.focus_set()

    # ── Data loading ─────────────────────────────────────────────────

    def load_timeline(self):
        self._load_manifest()
        day_file = SCRIPT_DIR / "data" / "entries" / f"{self.current_date}.json"
        if day_file.exists():
            try:
                self.entries = json.loads(day_file.read_text())
            except Exception:
                self.entries = []
        else:
            self.entries = []

        self._render_entries()
        self._update_sidebar()

    def _render_entries(self):
        for w in self.timeline_inner.winfo_children():
            w.destroy()
        self.timeline_widgets = []

        if not self.entries:
            empty = tk.Label(self.timeline_inner, text="No entries for this day.",
                             font=(self.font_family, 11), bg=BG, fg=MUTED, pady=24)
            empty.pack()
            return

        for entry in self.entries:
            self._render_entry_card(entry)

    def _render_entry_card(self, entry):
        row = tk.Frame(self.timeline_inner, bg=BG)
        row.pack(fill="x", pady=(0, 8))

        # Time column
        ts = entry.get("ts", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = ""

        time_label = tk.Label(row, text=time_str, font=(self.font_family, 10),
                              bg=BG, fg=MUTED, width=6, anchor="ne")
        time_label.pack(side="left", padx=(0, 4), anchor="n", pady=4)

        # Vertical separator
        sep = tk.Frame(row, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=(0, 8))

        # Card with mood accent stripe
        mood = entry.get("mood")
        mood_color = MOOD_COLORS.get(mood, BORDER) if mood else BORDER

        card_outer = tk.Frame(row, bg=mood_color, padx=0, pady=0)
        card_outer.pack(side="left", fill="x", expand=True)

        # Left accent stripe
        accent_stripe = tk.Frame(card_outer, bg=mood_color, width=3)
        accent_stripe.pack(side="left", fill="y")

        # Card border
        card_border = tk.Frame(card_outer, bg=BORDER, padx=1, pady=1)
        card_border.pack(side="left", fill="x", expand=True)

        card = tk.Frame(card_border, bg=CARD_BG, padx=10, pady=8)
        card.pack(fill="x", expand=True)

        # Mood badge
        if entry.get("type") == "mood" and mood:
            emoji = MOOD_EMOJI.get(mood, "\U0001f4ad")
            mood_badge = tk.Label(card, text=f"{emoji} {mood}",
                                  font=(self.font_family, 10, "bold"),
                                  bg=CARD_BG, fg=mood_color)
            mood_badge.pack(anchor="w", pady=(0, 4))

        # Reply preview
        if entry.get("type") == "reply" and entry.get("replyTo"):
            reply_text = f"\u21b3 replying to {entry['replyTo']}"
            tk.Label(card, text=reply_text, font=(self.font_family, 9),
                     bg=CARD_BG, fg=MUTED).pack(anchor="w", pady=(0, 2))

        # Content
        content = entry.get("content", "")
        if content:
            content_lbl = tk.Label(card, text=content, font=(self.font_family, 11),
                                   bg=CARD_BG, fg=TEXT, wraplength=500, justify="left",
                                   anchor="w")
            content_lbl.pack(anchor="w", fill="x")

        # Links
        for link in entry.get("links", []):
            link_text = f"\U0001f517 {link.get('title', link.get('url', ''))}"
            link_lbl = tk.Label(card, text=link_text, font=(self.font_family, 10),
                                bg=CARD_BG, fg=LINK_CLR, cursor="hand2", anchor="w")
            link_lbl.pack(anchor="w", pady=(2, 0))
            url = link.get("url", "")
            if url:
                link_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        # Attachments
        for att in entry.get("attachments", []):
            att_type = att.get("type", "")
            if att_type == "gif" or att_type == "image":
                att_text = f"\U0001f3ac GIF: {att.get('url', '')[:50]}"
            elif att_type == "pdf":
                att_text = f"\U0001f4c4 {att.get('title', 'PDF')}"
            else:
                att_text = f"Attachment: {att.get('url', '')[:50]}"
            tk.Label(card, text=att_text, font=(self.font_family, 9),
                     bg=CARD_BG, fg=MUTED, anchor="w").pack(anchor="w", pady=(2, 0))

        # Bottom row: tags + ID
        bottom = tk.Frame(card, bg=CARD_BG)
        bottom.pack(fill="x", pady=(4, 0))

        if entry.get("tags"):
            for tag in entry["tags"]:
                pill = tk.Label(bottom, text=f"#{tag}", font=(self.font_family, 9),
                                bg=TAG_BG, fg=MUTED, padx=4, pady=1, relief="solid", borderwidth=1)
                pill.pack(side="left", padx=(0, 4))

        # Entry ID (clickable -> edit mode)
        eid = entry.get("id", "")
        id_label = tk.Label(bottom, text=eid, font=(self.font_family, 9),
                            bg=CARD_BG, fg=MUTED, cursor="hand2")
        id_label.pack(side="right")
        id_label.bind("<Button-1>", lambda e, ent=entry: self._show_entry_menu(e, ent))

    def _show_entry_menu(self, event, entry):
        """Show context menu on entry ID click."""
        menu = tk.Menu(self.root, tearoff=0, font=(self.font_family, 10),
                       bg=CARD_BG, fg=TEXT)
        menu.add_command(label=f"Edit {entry['id']}", command=lambda: self.enter_edit_mode(entry))
        menu.add_command(label=f"Delete {entry['id']}", command=lambda: self.do_delete(entry['id']))
        menu.add_separator()
        menu.add_command(label="Copy ID", command=lambda: self._copy_to_clipboard(entry['id']))
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status(f"Copied: {text}")

    def _update_sidebar(self):
        # Find latest mood entry
        mood_entry = None
        for e in reversed(self.entries):
            if e.get("type") == "mood" and e.get("mood"):
                mood_entry = e
                break

        if mood_entry:
            mood = mood_entry["mood"]
            emoji = MOOD_EMOJI.get(mood, "\U0001f4ad")
            self.sidebar_emoji.configure(text=emoji)
            self.sidebar_mood.configure(text=mood)
        else:
            self.sidebar_emoji.configure(text="\U0001f4ad")
            self.sidebar_mood.configure(text="no mood set")

        # Format date
        try:
            y, m, d = self.current_date.split("-")
            dt = datetime(int(y), int(m), int(d))
            date_str = dt.strftime("%b %-d, %Y")
        except Exception:
            date_str = self.current_date
        self.sidebar_date.configure(text=date_str)

        # Update nav button states
        dates = sorted([m["date"] for m in self.manifest])
        idx = dates.index(self.current_date) if self.current_date in dates else -1
        self.prev_btn.configure(state="normal" if idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if 0 <= idx < len(dates) - 1 else "disabled")

    # ── Navigation ───────────────────────────────────────────────────

    def _navigate(self, direction):
        dates = sorted([m["date"] for m in self.manifest])
        if self.current_date not in dates:
            return
        idx = dates.index(self.current_date) + direction
        if 0 <= idx < len(dates):
            self.current_date = dates[idx]
            self.date_var.set(self.current_date)
            self.load_timeline()

    def _on_date_change(self, _event):
        new_date = self.date_var.get()
        if new_date and new_date != self.current_date:
            self.current_date = new_date
            self.load_timeline()

    # ── Server ───────────────────────────────────────────────────────

    def toggle_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self.server_proc.terminate()
            self.server_proc = None
            self.serve_btn.configure(text="Start Server")
            self.set_status("Server stopped")
        else:
            try:
                self.server_proc = subprocess.Popen(
                    ["python3", "-m", "http.server", "8000"],
                    cwd=str(SCRIPT_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.serve_btn.configure(text="Stop Server")
                self.set_status("Server running at http://localhost:8000")
                self.root.after(800, lambda: webbrowser.open("http://localhost:8000"))
            except Exception as e:
                self.set_status(f"Failed to start server: {e}", error=True)

    # ── CLI runner ───────────────────────────────────────────────────

    def run_cli_async(self, args, callback):
        """Run ./whatsup with args in a background thread, then invoke callback on main thread."""
        def worker():
            try:
                cmd = ["bash", str(SCRIPT_DIR / "whatsup")] + args
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                        cwd=str(SCRIPT_DIR))
                self.root.after(0, lambda: callback(
                    result.returncode == 0, result.stdout, result.stderr))
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: callback(False, "", "Command timed out (30s)"))
            except Exception as e:
                self.root.after(0, lambda: callback(False, "", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Refresh ──────────────────────────────────────────────────────

    def refresh(self):
        self._load_manifest()
        # Update date dropdown values
        dates = sorted([m["date"] for m in self.manifest], reverse=True) if self.manifest else []
        if dates:
            self.date_menu.configure(values=dates)
            if self.current_date not in dates:
                self.current_date = dates[0]
                self.date_var.set(self.current_date)
        self.load_timeline()

    # ── Status bar ───────────────────────────────────────────────────

    def set_status(self, msg, error=False):
        self.statusbar.configure(text=msg, fg=ACCENT if error else MUTED,
                                 bg=ERROR_BG if error else CARD_BG)
        # Auto-clear after 5 seconds
        self.root.after(5000, lambda: self.statusbar.configure(text="Ready", fg=MUTED, bg=CARD_BG))


if __name__ == "__main__":
    WhatsUpGUI()
