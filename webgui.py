#!/usr/bin/env python3
"""WhatsUp Web GUI -- browser-based interface using stdlib http.server."""

import http.server
import json
import os
import subprocess
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PORT = 9000

# ── CLI runner ────────────────────────────────────────────────────────

def run_cli(args):
    """Run ./whatsup with args, returns (ok, stdout, stderr)."""
    try:
        cmd = ["bash", str(SCRIPT_DIR / "whatsup")] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=str(SCRIPT_DIR)
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timed out (30s)")
    except Exception as e:
        return (False, "", str(e))

# ── HTML page ─────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>whatsup - web gui</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
  <style>
    /* ── Compose panel ── */
    .compose-panel {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .compose-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--muted);
    }
    .compose-edit-label { color: var(--accent); font-weight: 600; }
    .compose-textarea {
      width: 100%;
      min-height: 64px;
      resize: vertical;
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.5;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 10px;
      background: var(--bg);
      color: var(--text);
      margin-bottom: 8px;
    }
    .compose-textarea:focus { outline: none; border-color: var(--link); }
    .compose-textarea::placeholder { color: var(--muted); }
    .compose-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 6px;
    }
    .compose-row label {
      font-size: 12px;
      color: var(--muted);
      font-weight: 500;
    }
    .compose-row select,
    .compose-row input[type="text"] {
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      font-size: 12px;
      padding: 4px 8px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--bg);
      color: var(--text);
    }
    .compose-row input[type="text"] { width: 120px; }
    .compose-row input[type="text"].wide { width: 200px; }
    .compose-btn {
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      font-size: 12px;
      padding: 5px 14px;
      border: 1px solid var(--border);
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
      background: var(--bg);
      color: var(--text);
    }
    .compose-btn:hover { border-color: var(--link); background: rgba(42,90,167,0.06); }
    .compose-btn.primary {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
      font-weight: 600;
    }
    .compose-btn.primary:hover { opacity: 0.9; }
    .compose-btn.small { padding: 2px 8px; font-size: 11px; }
    .tag-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
    .tag-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      background: rgba(138,132,120,0.1);
      border: 1px solid var(--border);
      border-radius: 12px;
      font-size: 12px;
      color: var(--muted);
    }
    .tag-pill .remove {
      cursor: pointer;
      color: var(--accent);
      font-weight: bold;
      margin-left: 2px;
    }
    .tag-pill .remove:hover { opacity: 0.7; }

    /* ── Entry action buttons ── */
    .entry-actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .entry-actions button {
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      font-size: 11px;
      padding: 2px 8px;
      border: 1px solid var(--border);
      border-radius: 4px;
      cursor: pointer;
      background: var(--bg);
      color: var(--muted);
      transition: all 0.2s;
    }
    .entry-actions button:hover { border-color: var(--link); color: var(--text); }
    .entry-actions button.del:hover { border-color: var(--accent); color: var(--accent); }

    /* ── Status bar ── */
    .status-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: 32px;
      background: var(--card-bg);
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      padding: 0 24px;
      font-size: 12px;
      color: var(--muted);
      z-index: 1000;
    }
    .status-bar.error { color: var(--accent); background: #fce4e0; }
    .status-bar.success { color: #3d7a3d; }

    /* ── Date select in nav ── */
    .nav-date-select {
      font-family: 'IBM Plex Mono', 'Courier New', monospace;
      font-size: 13px;
      padding: 2px 8px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--card-bg);
      color: var(--text);
      font-weight: 600;
    }

    /* Add bottom padding so content isn't hidden behind status bar */
    .day-content { padding-bottom: 48px; }
  </style>
</head>
<body>
  <div id="app">
    <div class="loading">Loading<span class="blink">_</span></div>
  </div>
  <div id="status-bar" class="status-bar">Ready</div>

<script>
/**
 * WhatsUp Web GUI - client-side rendering engine.
 * All user-supplied data is escaped via esc() before DOM insertion.
 * This follows the same sanitization pattern as the existing app.js.
 */
const WG = {
  config: null,
  manifest: [],
  currentDate: null,
  entries: [],
  tags: [],
  editId: null,

  MOODS: ['', 'focused', 'happy', 'tired', 'excited', 'frustrated', 'chill', 'thinking', 'creative'],
  MOOD_EMOJI: { focused:'\u{1F3AF}', happy:'\u{1F60A}', tired:'\u{1F634}', excited:'\u{1F680}', frustrated:'\u{1F624}', chill:'\u{1F60E}', thinking:'\u{1F914}', creative:'\u{1F3A8}' },

  async init() {
    try {
      const [config, manifest] = await Promise.all([
        fetch('/api/config').then(r => r.ok ? r.json() : null),
        fetch('/api/manifest').then(r => r.ok ? r.json() : [])
      ]);
      this.config = config || { name: 'WhatsUp', bio: '', avatar: '', links: [], timezone: 'UTC' };
      this.manifest = manifest;

      if (this.manifest.length) {
        const sorted = [...this.manifest].sort((a, b) => b.date.localeCompare(a.date));
        this.currentDate = sorted[0].date;
      } else {
        this.currentDate = this.today();
      }

      await this.loadAndRender();
    } catch (e) {
      document.getElementById('app').textContent = 'Failed to load: ' + e.message;
    }

    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); this.doPost(); }
      if (e.key === 'Escape') this.clearCompose();
    });
  },

  async loadAndRender() {
    const res = await fetch('/api/entries?date=' + this.currentDate);
    this.entries = res.ok ? await res.json() : [];
    this.render();
  },

  render() {
    const sorted = this.manifest.map(m => m.date).sort();
    const idx = sorted.indexOf(this.currentDate);
    const prev = idx > 0 ? sorted[idx - 1] : null;
    const next = idx >= 0 && idx < sorted.length - 1 ? sorted[idx + 1] : null;

    const app = document.getElementById('app');
    // Build full page using pre-escaped strings, then set via setContent
    let html = this.navBar(prev, next);
    html += '<div class="day-layout">';
    html += this.renderSidebar();
    html += '<div class="day-content">';
    html += this.renderCompose();
    html += this.renderTimeline();
    html += '</div></div>';

    this.setContent(app, html);
    this.bindEvents();
  },

  /**
   * Sets element content from trusted, pre-escaped HTML strings.
   * All user-supplied data is escaped via esc() before being included.
   */
  setContent(el, html) { el.innerHTML = html; },

  navBar(prev, next) {
    let dates = [...this.manifest].sort((a, b) => b.date.localeCompare(a.date));
    let options = dates.map(m =>
      '<option value="' + m.date + '"' + (m.date === this.currentDate ? ' selected' : '') + '>' + m.date + '</option>'
    ).join('');
    if (!dates.find(m => m.date === this.currentDate)) {
      options = '<option value="' + this.currentDate + '" selected>' + this.currentDate + '</option>' + options;
    }

    let nav = '<nav class="nav-bar">';
    nav += '<span class="nav-brand">whatsup</span>';
    nav += '<div class="nav-arrows">';
    nav += prev ? '<a href="#" onclick="WG.goDate(\'' + prev + '\');return false">&larr; ' + this.shortDate(prev) + '</a>' : '<span class="disabled">&larr;</span>';
    nav += '</div>';
    nav += '<div class="nav-center"><select class="nav-date-select" onchange="WG.goDate(this.value)">' + options + '</select></div>';
    nav += '<div class="nav-arrows">';
    nav += next ? '<a href="#" onclick="WG.goDate(\'' + next + '\');return false">' + this.shortDate(next) + ' &rarr;</a>' : '<span class="disabled">&rarr;</span>';
    nav += '</div>';
    nav += '</nav>';
    return nav;
  },

  renderSidebar() {
    const moodEntry = [...this.entries].reverse().find(e => e.type === 'mood' && e.mood);
    const emoji = moodEntry ? (this.MOOD_EMOJI[moodEntry.mood] || '\u{1F4AD}') : '\u{1F4AD}';
    const moodName = moodEntry ? this.esc(moodEntry.mood) : 'no mood set';
    const name = this.config.name ? this.esc(this.config.name) : '';
    const bio = this.config.bio ? this.esc(this.config.bio) : '';

    let gifUrl = null;
    this.sidebarGifEntryId = null;
    if (moodEntry && moodEntry.attachments && moodEntry.attachments.length) {
      const gifAtt = moodEntry.attachments.find(a => a.type === 'gif' || a.type === 'image');
      if (gifAtt) { gifUrl = this.giphyDirect(gifAtt.url); this.sidebarGifEntryId = moodEntry.id; }
    }

    let html = '<aside class="mood-sidebar">';
    html += '<div class="sidebar-mood-emoji">' + emoji + '</div>';
    html += '<div class="sidebar-mood-name">' + moodName + '</div>';
    if (gifUrl) html += '<img src="' + this.esc(gifUrl) + '" alt="" class="sidebar-mood-gif" loading="lazy">';
    html += '<div class="sidebar-divider"></div>';
    if (name) html += '<div class="sidebar-user-name">' + name + '</div>';
    if (bio) html += '<div class="sidebar-user-bio">' + bio + '</div>';
    html += '<div class="sidebar-date">' + this.longDate(this.currentDate) + '</div>';
    html += '</aside>';
    return html;
  },

  renderCompose() {
    let moodOpts = this.MOODS.map(m =>
      '<option value="' + m + '">' + (m ? (this.MOOD_EMOJI[m] || '') + ' ' + m : '(none)') + '</option>'
    ).join('');

    let pills = this.tags.map(t =>
      '<span class="tag-pill">#' + this.esc(t) + '<span class="remove" onclick="WG.removeTag(\'' + this.esc(t) + '\')">\u2715</span></span>'
    ).join('');

    let html = '<div class="compose-panel">';
    html += '<div class="compose-header"><span>COMPOSE</span>';
    if (this.editId) html += '<span class="compose-edit-label">Editing ' + this.esc(this.editId) + '</span>';
    html += '</div>';
    html += '<textarea id="compose-content" class="compose-textarea" placeholder="What\'s up?"></textarea>';

    html += '<div class="compose-row">';
    html += '<label>Mood:</label><select id="compose-mood">' + moodOpts + '</select>';
    html += '<label>Tag:</label><input type="text" id="compose-tag" placeholder="add tag">';
    html += '<button class="compose-btn small" onclick="WG.addTag()">+</button>';
    html += '<label>Link:</label><input type="text" id="compose-link" class="wide" placeholder="https://">';
    html += '</div>';

    html += '<div class="compose-row">';
    html += '<label>Reply:</label><input type="text" id="compose-reply" placeholder="entry id">';
    html += '<label>GIF:</label><input type="text" id="compose-gif" class="wide" placeholder="giphy url">';
    html += '<span style="flex:1"></span>';
    html += '<button class="compose-btn" onclick="WG.clearCompose()">Clear</button>';
    html += '<button class="compose-btn primary" onclick="WG.doPost()">' + (this.editId ? 'Save' : 'Post') + '</button>';
    html += '</div>';

    if (this.tags.length) html += '<div class="tag-pills">' + pills + '</div>';
    html += '</div>';
    return html;
  },

  renderTimeline() {
    if (!this.entries.length) {
      return '<div class="empty-state"><p>No entries for this day.</p></div>';
    }
    let html = '<div class="timeline">';
    [...this.entries].reverse().forEach(e => { html += this.entryHTML(e); });
    html += '</div>';
    return html;
  },

  entryHTML(entry) {
    const time = this.formatTime(entry.ts);
    const rel = this.relTime(entry.ts);
    const moodAttr = entry.mood ? ' data-mood="' + this.esc(entry.mood) + '"' : '';
    let card = '';

    if (entry.type === 'mood' && entry.mood) {
      card += '<div class="mood-badge" data-mood="' + this.esc(entry.mood) + '"><span>' + (this.MOOD_EMOJI[entry.mood] || '\u{1F4AD}') + '</span> ' + this.esc(entry.mood) + '</div>';
    }

    if (entry.type === 'reply' && entry.replyTo) {
      const preview = this.entries.find(x => x.id === entry.replyTo);
      card += '<div class="reply-preview">' + (preview ? this.esc(preview.content.slice(0, 100)) : '(original not found)') + '</div>';
    }

    if (entry.content) {
      card += '<div class="entry-content">' + this.linkify(this.esc(entry.content)) + '</div>';
    }

    if (entry.links && entry.links.length) {
      entry.links.forEach(l => {
        card += '<a href="' + this.esc(l.url) + '" class="attachment-link" target="_blank" rel="noopener noreferrer">\u{1F517} ' + this.esc(l.title || l.url) + '</a>';
      });
    }

    const skipGif = entry.id === this.sidebarGifEntryId;
    if (entry.attachments && entry.attachments.length) {
      card += '<div class="attachment">';
      entry.attachments.forEach(a => {
        if (a.type === 'gif' || a.type === 'image') {
          if (skipGif) return;
          const url = this.giphyDirect(a.url);
          card += '<img src="' + this.esc(url) + '" alt="" class="gif-embed" loading="lazy">';
        } else if (a.type === 'pdf') {
          card += '<a href="' + this.esc(a.url) + '" class="attachment-link" target="_blank" rel="noopener noreferrer">\u{1F4C4} ' + this.esc(a.title || 'PDF') + '</a>';
        }
      });
      card += '</div>';
    }

    if (entry.tags && entry.tags.length) {
      card += '<div class="entry-meta">';
      entry.tags.forEach(t => { card += '<span class="tag">#' + this.esc(t) + '</span>'; });
      card += '</div>';
    }

    card += '<div class="entry-meta"><span class="entry-id">' + this.esc(entry.id) + '</span></div>';

    card += '<div class="entry-actions">';
    card += '<button onclick="WG.editEntry(\'' + this.esc(entry.id) + '\')">edit</button>';
    card += '<button class="del" onclick="WG.deleteEntry(\'' + this.esc(entry.id) + '\')">delete</button>';
    card += '</div>';

    return '<div class="entry">' +
      '<div class="entry-time"><div>' + time + '</div><div class="relative-time">' + rel + '</div></div>' +
      '<div class="entry-card"' + moodAttr + '>' + card + '</div>' +
    '</div>';
  },

  // ── Actions ──

  async doPost() {
    const content = document.getElementById('compose-content').value.trim();
    if (!content) { this.status('Content is required', true); return; }

    const body = {};

    if (this.editId) {
      body.action = 'edit';
      body.id = this.editId;
      body.content = content;
    } else {
      body.action = 'post';
      body.content = content;
      body.mood = document.getElementById('compose-mood').value;
      body.link = document.getElementById('compose-link').value.trim();
      body.reply = document.getElementById('compose-reply').value.trim();
      body.gif = document.getElementById('compose-gif').value.trim();
      body.tags = this.tags;
    }

    const endpoint = this.editId ? '/api/edit' : '/api/post';
    this.status(this.editId ? 'Saving edit...' : 'Posting...');

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.ok) {
        this.status(data.message, false, true);
        this.editId = null;
        this.tags = [];
        const mRes = await fetch('/api/manifest');
        this.manifest = mRes.ok ? await mRes.json() : this.manifest;
        await this.loadAndRender();
      } else {
        this.status('Error: ' + data.error, true);
      }
    } catch (e) {
      this.status('Error: ' + e.message, true);
    }
  },

  editEntry(id) {
    const entry = this.entries.find(e => e.id === id);
    if (!entry) return;
    this.editId = id;
    this.tags = [];
    this.render();
    const ta = document.getElementById('compose-content');
    if (ta) { ta.value = entry.content || ''; ta.focus(); }
  },

  async deleteEntry(id) {
    if (!confirm('Delete entry ' + id + '?')) return;
    this.status('Deleting...');
    try {
      const res = await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (data.ok) {
        this.status('Deleted ' + id, false, true);
        const mRes = await fetch('/api/manifest');
        this.manifest = mRes.ok ? await mRes.json() : this.manifest;
        await this.loadAndRender();
      } else {
        this.status('Error: ' + data.error, true);
      }
    } catch (e) {
      this.status('Error: ' + e.message, true);
    }
  },

  clearCompose() {
    this.editId = null;
    this.tags = [];
    this.render();
  },

  addTag() {
    const input = document.getElementById('compose-tag');
    if (!input) return;
    const tag = input.value.trim().replace(/^#/, '');
    if (tag && !this.tags.includes(tag)) {
      this.tags.push(tag);
      const state = this.captureComposeState();
      this.render();
      this.restoreComposeState(state);
    }
    const newInput = document.getElementById('compose-tag');
    if (newInput) { newInput.value = ''; newInput.focus(); }
  },

  removeTag(tag) {
    this.tags = this.tags.filter(t => t !== tag);
    const state = this.captureComposeState();
    this.render();
    this.restoreComposeState(state);
  },

  captureComposeState() {
    return {
      content: (document.getElementById('compose-content') || {}).value || '',
      mood: (document.getElementById('compose-mood') || {}).value || '',
      link: (document.getElementById('compose-link') || {}).value || '',
      reply: (document.getElementById('compose-reply') || {}).value || '',
      gif: (document.getElementById('compose-gif') || {}).value || '',
    };
  },

  restoreComposeState(s) {
    const el = (id) => document.getElementById(id);
    if (el('compose-content')) el('compose-content').value = s.content;
    if (el('compose-mood')) el('compose-mood').value = s.mood;
    if (el('compose-link')) el('compose-link').value = s.link;
    if (el('compose-reply')) el('compose-reply').value = s.reply;
    if (el('compose-gif')) el('compose-gif').value = s.gif;
  },

  goDate(date) {
    this.currentDate = date;
    this.editId = null;
    this.tags = [];
    this.loadAndRender();
  },

  bindEvents() {
    const tagInput = document.getElementById('compose-tag');
    if (tagInput) {
      tagInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); this.addTag(); }
      });
    }
  },

  // ── Status bar ──

  status(msg, isError, isSuccess) {
    const bar = document.getElementById('status-bar');
    if (!bar) return;
    bar.textContent = msg;
    bar.className = 'status-bar' + (isError ? ' error' : '') + (isSuccess ? ' success' : '');
    if (!isError) {
      setTimeout(() => {
        bar.textContent = 'Ready';
        bar.className = 'status-bar';
      }, 5000);
    }
  },

  // ── Helpers ──

  giphyDirect(url) {
    if (url.includes('media.giphy.com') || url.includes('/media/')) return url;
    const m = url.match(/giphy\.com\/gifs\/[^/]+-([a-zA-Z0-9]+)\/?$/);
    return m ? 'https://media.giphy.com/media/' + m[1] + '/giphy.gif' : url;
  },
  formatTime(ts) { return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }); },
  longDate(ds) {
    const [y, m, d] = ds.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  },
  shortDate(ds) {
    const [y, m, d] = ds.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  },
  relTime(ts) {
    const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (s < 60) return 'just now';
    const m = Math.floor(s / 60); if (m < 60) return m + 'm ago';
    const h = Math.floor(m / 60); if (h < 24) return h + 'h ago';
    const d = Math.floor(h / 24);
    if (d === 1) return 'yesterday'; if (d < 7) return d + 'd ago';
    if (d < 30) return Math.floor(d / 7) + 'w ago';
    return Math.floor(d / 30) + 'mo ago';
  },
  today() {
    const n = new Date();
    return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0');
  },
  linkify(text) { return text.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'); },
  esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }
};

document.addEventListener('DOMContentLoaded', () => WG.init());
</script>
</body>
</html>
"""

# ── Request handler ───────────────────────────────────────────────────

class WhatsUpHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def log_message(self, format, *args):
        sys.stderr.write("[webgui] %s\n" % (format % args))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._respond_html(HTML_PAGE)
        elif path == "/api/config":
            self._serve_json_file(SCRIPT_DIR / "config.json")
        elif path == "/api/manifest":
            self._serve_json_file(SCRIPT_DIR / "data" / "index.json")
        elif path == "/api/entries":
            qs = urllib.parse.parse_qs(parsed.query)
            date = qs.get("date", [None])[0]
            if date:
                self._serve_json_file(SCRIPT_DIR / "data" / "entries" / f"{date}.json")
            else:
                self._respond_json({"error": "date parameter required"}, 400)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
        except (json.JSONDecodeError, ValueError):
            self._respond_json({"ok": False, "error": "Invalid JSON"}, 400)
            return

        if path == "/api/post":
            self._handle_post(body)
        elif path == "/api/edit":
            self._handle_edit(body)
        elif path == "/api/delete":
            self._handle_delete(body)
        else:
            self._respond_json({"ok": False, "error": "Unknown endpoint"}, 404)

    def _handle_post(self, body):
        content = body.get("content", "").strip()
        if not content:
            self._respond_json({"ok": False, "error": "Content is required"})
            return

        args = []
        mood = body.get("mood", "")
        if mood:
            args.extend(["--mood", mood])
        link = body.get("link", "")
        if link:
            args.extend(["--link", link])
        reply = body.get("reply", "")
        if reply:
            args.extend(["--reply", reply])
        gif = body.get("gif", "")
        if gif:
            args.extend(["--gif", gif])
        for tag in body.get("tags", []):
            if tag:
                args.extend(["--tag", tag])
        args.append(content)

        ok, stdout, stderr = run_cli(args)
        if ok:
            self._respond_json({"ok": True, "message": stdout.strip()})
        else:
            self._respond_json({"ok": False, "error": stderr.strip() or stdout.strip()})

    def _handle_edit(self, body):
        entry_id = body.get("id", "").strip()
        content = body.get("content", "").strip()
        if not entry_id or not content:
            self._respond_json({"ok": False, "error": "id and content required"})
            return

        ok, stdout, stderr = run_cli(["--edit", entry_id, content])
        if ok:
            self._respond_json({"ok": True, "message": stdout.strip()})
        else:
            self._respond_json({"ok": False, "error": stderr.strip() or stdout.strip()})

    def _handle_delete(self, body):
        entry_id = body.get("id", "").strip()
        if not entry_id:
            self._respond_json({"ok": False, "error": "id required"})
            return

        ok, stdout, stderr = run_cli(["--delete", entry_id])
        if ok:
            self._respond_json({"ok": True, "message": stdout.strip()})
        else:
            self._respond_json({"ok": False, "error": stderr.strip() or stdout.strip()})

    # ── Response helpers ──

    def _respond_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond_json(self, obj, status=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_json_file(self, path):
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._respond_json(data)
            except Exception:
                self._respond_json({"error": "Failed to read file"}, 500)
        else:
            self._respond_json([], 200)


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = HTTPServer(("", PORT), WhatsUpHandler)
    print(f"WhatsUp Web GUI: http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
