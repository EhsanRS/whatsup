/**
 * WhatsUp - Personal Micro-Status Timeline
 * Vanilla JS rendering engine. No dependencies.
 */

const App = {
  config: null,
  manifest: [],
  cache: {},

  async init() {
    try {
      const [configRes, manifestRes] = await Promise.all([
        fetch('config.json').then(r => r.ok ? r.json() : null),
        fetch('data/index.json').then(r => r.ok ? r.json() : [])
      ]);
      this.config = configRes || { name: 'WhatsUp', bio: '', avatar: '', links: [], timezone: 'UTC' };
      this.manifest = manifestRes;
      window.addEventListener('hashchange', () => this.route());
      this.route();
    } catch (e) {
      this.showError('Failed to load: ' + e.message);
    }
  },

  route() {
    const hash = location.hash.replace('#', '') || '/';
    if (hash === '/' || hash === '') {
      const latest = this.manifest.length
        ? [...this.manifest].sort((a, b) => b.date.localeCompare(a.date))[0].date
        : this.today();
      this.viewDay(latest);
    } else if (hash === '/archive') {
      this.viewArchive();
    } else if (/^\/\d{4}-\d{2}$/.test(hash)) {
      this.viewMonth(hash.slice(1));
    } else if (/^\/\d{4}-\d{2}-\d{2}$/.test(hash)) {
      this.viewDay(hash.slice(1));
    } else {
      this.showError('Page not found');
    }
  },

  async loadDay(date) {
    if (this.cache[date]) return this.cache[date];
    try {
      const r = await fetch(`data/entries/${date}.json`);
      const entries = r.ok ? await r.json() : [];
      this.cache[date] = entries;
      return entries;
    } catch {
      return [];
    }
  },

  // ── Views ──

  async viewDay(date) {
    const app = document.getElementById('app');
    this.setContent(app, this.navBar(date) + '<div class="day-layout"><div class="day-content"><div class="loading">Loading<span class="blink">_</span></div></div></div>');

    const entries = await this.loadDay(date);
    const sorted = this.manifest.map(m => m.date).sort();
    const idx = sorted.indexOf(date);
    const prev = idx > 0 ? sorted[idx - 1] : null;
    const next = idx >= 0 && idx < sorted.length - 1 ? sorted[idx + 1] : null;
    const ym = date.slice(0, 7);

    const sidebar = this.renderSidebar(entries, date, ym);

    let timeline = '';
    if (entries.length === 0) {
      timeline += this.manifest.length === 0
        ? '<div class="empty-state"><p>No entries yet.</p><p>Post your first update:</p><code>./whatsup "Hello world!"</code></div>'
        : '<div class="empty-state"><p>No entries for this day.</p></div>';
    } else {
      timeline += '<div class="timeline">';
      [...entries].reverse().forEach(e => { timeline += this.entryHTML(e); });
      timeline += '</div>';
    }

    const moodBanner = this.renderMoodBanner(entries);

    let body = this.navBar(date, prev, next, ym);
    body += '<div class="day-layout">';
    body += sidebar;
    body += moodBanner;
    body += '<div class="day-content">' + timeline + '</div>';
    body += '</div>';
    body += this.footer();

    this.setContent(app, body);
  },

  async viewMonth(ym) {
    const app = document.getElementById('app');
    const [year, month] = ym.split('-').map(Number);
    const daysInMonth = new Date(year, month, 0).getDate();
    const startDay = new Date(year, month - 1, 1).getDay();
    const monthName = new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const countByDay = {};
    this.manifest.filter(m => m.date.startsWith(ym)).forEach(m => {
      countByDay[m.date] = m.count;
    });

    const allMonths = [...new Set(this.manifest.map(m => m.date.slice(0, 7)))].sort();
    const mi = allMonths.indexOf(ym);
    const prevM = mi > 0 ? allMonths[mi - 1] : null;
    const nextM = mi >= 0 && mi < allMonths.length - 1 ? allMonths[mi + 1] : null;

    let nav = '<nav class="nav-bar">';
    nav += '<a href="#/" class="nav-brand">whatsup</a>';
    nav += '<div class="nav-arrows">' + (prevM ? '<a href="#/' + prevM + '">&larr;</a>' : '<span class="disabled">&larr;</span>') + '</div>';
    nav += '<div class="nav-center">' + monthName + '</div>';
    nav += '<div class="nav-arrows">' + (nextM ? '<a href="#/' + nextM + '">&rarr;</a>' : '<span class="disabled">&rarr;</span>') + '</div>';
    nav += '<div class="nav-links"><a href="#/archive">archive</a></div>';
    nav += '</nav>';

    let grid = '<div class="calendar-grid">';
    ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
      grid += '<div class="calendar-day-name">' + d + '</div>';
    });
    for (let i = 0; i < startDay; i++) grid += '<div class="calendar-day empty"></div>';
    for (let d = 1; d <= daysInMonth; d++) {
      const ds = ym + '-' + String(d).padStart(2, '0');
      const c = countByDay[ds] || 0;
      if (c > 0) {
        grid += '<div class="calendar-day has-entries" onclick="location.hash=\'/' + ds + '\'"><div class="day-number">' + d + '</div><div class="entry-count">' + c + '</div></div>';
      } else {
        grid += '<div class="calendar-day"><div class="day-number">' + d + '</div></div>';
      }
    }
    grid += '</div>';

    this.setContent(app, nav + '<main><div class="month-view">' + grid + '</div></main>' + this.footer());
  },

  viewArchive() {
    const app = document.getElementById('app');
    const byMonth = {};
    this.manifest.forEach(m => {
      const ym = m.date.slice(0, 7);
      byMonth[ym] = (byMonth[ym] || 0) + m.count;
    });
    const months = Object.keys(byMonth).sort().reverse();
    const byYear = {};
    months.forEach(m => {
      const y = m.slice(0, 4);
      if (!byYear[y]) byYear[y] = [];
      byYear[y].push(m);
    });

    let html = '<main><div class="archive-view"><h1 class="archive-title">Archive</h1>';
    if (months.length === 0) {
      html += '<div class="empty-state"><p>No entries yet.</p></div>';
    } else {
      html += '<div class="month-list">';
      Object.keys(byYear).sort().reverse().forEach(year => {
        html += '<div class="archive-year"><h2>' + year + '</h2>';
        byYear[year].forEach(ym => {
          const name = new Date(Number(ym.slice(0,4)), Number(ym.slice(5,7)) - 1).toLocaleDateString('en-US', { month: 'long' });
          const c = byMonth[ym];
          html += '<a href="#/' + ym + '" class="month-item"><span>' + name + '</span><span class="month-count">' + c + ' ' + (c === 1 ? 'entry' : 'entries') + '</span></a>';
        });
        html += '</div>';
      });
      html += '</div>';
    }
    html += '</div></main>';

    const nav = '<nav class="nav-bar"><a href="#/" class="nav-brand">whatsup</a><div class="nav-center">Archive</div><div class="nav-links"><a href="#/">today</a></div></nav>';
    this.setContent(app, nav + html + this.footer());
  },

  // ── Components ──

  navBar(date, prev, next, ym) {
    let nav = '<nav class="nav-bar">';
    nav += '<a href="#/" class="nav-brand">whatsup</a>';
    if (prev !== undefined) {
      nav += '<div class="nav-arrows">';
      nav += prev ? '<a href="#/' + prev + '">&larr; ' + this.shortDate(prev) + '</a>' : '<span class="disabled">&larr;</span>';
      nav += '</div>';
      nav += '<div class="nav-center">' + this.longDate(date) + '</div>';
      nav += '<div class="nav-arrows">';
      nav += next ? '<a href="#/' + next + '">' + this.shortDate(next) + ' &rarr;</a>' : '<span class="disabled">&rarr;</span>';
      nav += '</div>';
      nav += '<div class="nav-links"><a href="#/' + ym + '">month</a><a href="#/archive">archive</a></div>';
    }
    nav += '</nav>';
    return nav;
  },

  renderSidebar(entries, date, ym) {
    const moodEntry = [...entries].reverse().find(e => e.type === 'mood' && e.mood);
    const emoji = moodEntry ? this.moodEmoji(moodEntry.mood) : '💭';
    const moodName = moodEntry ? this.esc(moodEntry.mood) : 'no mood set';

    let gifUrl = null;
    this.sidebarGifEntryId = null;
    if (moodEntry && moodEntry.attachments && moodEntry.attachments.length) {
      const gifAtt = moodEntry.attachments.find(a => a.type === 'gif' || a.type === 'image');
      if (gifAtt) { gifUrl = this.giphyDirect(gifAtt.url); this.sidebarGifEntryId = moodEntry.id; }
    }

    const name = this.config.name ? this.esc(this.config.name) : '';
    const bio = this.config.bio ? this.esc(this.config.bio) : '';

    let html = '<aside class="mood-sidebar">';
    html += '<div class="sidebar-mood-emoji">' + emoji + '</div>';
    html += '<div class="sidebar-mood-name">' + moodName + '</div>';
    if (gifUrl) {
      html += '<img src="' + this.esc(gifUrl) + '" alt="" class="sidebar-mood-gif" loading="lazy">';
    }
    html += '<div class="sidebar-divider"></div>';
    if (name) html += '<div class="sidebar-user-name">' + name + '</div>';
    if (bio) html += '<div class="sidebar-user-bio">' + bio + '</div>';
    html += '<div class="sidebar-date">' + this.longDate(date) + '</div>';
    html += '<div class="sidebar-nav">';
    html += '<a href="#/' + ym + '">month view</a>';
    html += '<a href="#/archive">archive</a>';
    html += '</div>';
    html += '</aside>';
    return html;
  },

  renderMoodBanner(entries) {
    const moodEntry = [...entries].reverse().find(e => e.type === 'mood' && e.mood);
    const emoji = moodEntry ? this.moodEmoji(moodEntry.mood) : '💭';
    const moodName = moodEntry ? this.esc(moodEntry.mood) : 'no mood set';
    const name = this.config.name ? this.esc(this.config.name) : '';

    let gifUrl = null;
    if (moodEntry && moodEntry.attachments && moodEntry.attachments.length) {
      const gifAtt = moodEntry.attachments.find(a => a.type === 'gif' || a.type === 'image');
      if (gifAtt) gifUrl = this.giphyDirect(gifAtt.url);
    }

    let html = '<div class="mood-banner">';
    if (gifUrl) {
      html += '<img src="' + this.esc(gifUrl) + '" alt="" class="mood-banner-gif" loading="lazy">';
    } else {
      html += '<div class="mood-banner-emoji">' + emoji + '</div>';
    }
    html += '<div class="mood-banner-info">';
    html += '<div class="mood-banner-name">' + moodName + '</div>';
    if (name) html += '<div class="mood-banner-user">' + name + '</div>';
    html += '</div>';
    html += '</div>';
    return html;
  },

  footer() {
    return '<footer>powered by <a href="https://github.com">whatsup</a></footer>';
  },

  entryHTML(entry) {
    const time = this.formatTime(entry.ts);
    const rel = this.relTime(entry.ts);
    const moodAttr = entry.mood ? ' data-mood="' + this.esc(entry.mood) + '"' : '';
    let card = '';

    // Mood badge
    if (entry.type === 'mood' && entry.mood) {
      card += '<div class="mood-badge" data-mood="' + this.esc(entry.mood) + '"><span>' + this.moodEmoji(entry.mood) + '</span> ' + this.esc(entry.mood) + '</div>';
    }

    // Reply preview
    if (entry.type === 'reply' && entry.replyTo) {
      const preview = this.findEntry(entry.replyTo);
      card += '<div class="reply-preview">' + (preview ? this.esc(preview.content.slice(0, 100)) : '(original not found)') + '</div>';
    }

    // Content
    if (entry.content) {
      card += '<div class="entry-content">' + this.linkify(this.esc(entry.content)) + '</div>';
    }

    // Links
    if (entry.links && entry.links.length) {
      entry.links.forEach(l => {
        card += '<a href="' + this.esc(l.url) + '" class="attachment-link" target="_blank" rel="noopener noreferrer">🔗 ' + this.esc(l.title || l.url) + '</a>';
      });
    }

    // Attachments
    const skipGif = entry.id === this.sidebarGifEntryId;
    if (entry.attachments && entry.attachments.length) {
      card += '<div class="attachment">';
      entry.attachments.forEach(a => {
        if (a.type === 'gif' || a.type === 'image') {
          if (skipGif) return;
          const url = this.giphyDirect(a.url);
          card += '<img src="' + this.esc(url) + '" alt="' + this.esc(a.title || '') + '" class="gif-embed" loading="lazy">';
        } else if (a.type === 'pdf') {
          card += '<a href="' + this.esc(a.url) + '" class="attachment-link" target="_blank" rel="noopener noreferrer">📄 ' + this.esc(a.title || 'PDF') + '</a>';
        }
      });
      card += '</div>';
    }

    // Tags
    if (entry.tags && entry.tags.length) {
      card += '<div class="entry-meta">';
      entry.tags.forEach(t => { card += '<span class="tag">#' + this.esc(t) + '</span>'; });
      card += '</div>';
    }

    // Entry ID
    card += '<div class="entry-meta"><span class="entry-id">' + this.esc(entry.id) + '</span></div>';

    return '<div class="entry">' +
      '<div class="entry-time"><div>' + time + '</div><div class="relative-time">' + rel + '</div></div>' +
      '<div class="entry-card"' + moodAttr + '>' + card + '</div>' +
    '</div>';
  },

  // ── Helpers ──

  /**
   * Sets element content from trusted, pre-escaped HTML strings.
   * All user-supplied data is escaped via esc() before being included.
   */
  setContent(el, html) {
    el.innerHTML = html;
  },

  findEntry(id) {
    for (const d in this.cache) {
      const e = this.cache[d].find(x => x.id === id);
      if (e) return e;
    }
    return null;
  },

  giphyDirect(url) {
    if (url.includes('media.giphy.com') || url.includes('/media/')) return url;
    const m = url.match(/giphy\.com\/gifs\/[^/]+-([a-zA-Z0-9]+)\/?$/);
    return m ? 'https://media.giphy.com/media/' + m[1] + '/giphy.gif' : url;
  },

  formatTime(ts) {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  },

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
    const m = Math.floor(s / 60);
    if (m < 60) return m + 'm ago';
    const h = Math.floor(m / 60);
    if (h < 24) return h + 'h ago';
    const d = Math.floor(h / 24);
    if (d === 1) return 'yesterday';
    if (d < 7) return d + 'd ago';
    if (d < 30) return Math.floor(d / 7) + 'w ago';
    return Math.floor(d / 30) + 'mo ago';
  },

  today() {
    const n = new Date();
    return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0');
  },

  moodEmoji(mood) {
    return { focused:'🎯', happy:'😊', tired:'😴', excited:'🚀', frustrated:'😤', chill:'😎', thinking:'🤔', creative:'🎨' }[mood] || '💭';
  },

  linkify(text) {
    return text.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  },

  esc(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  },

  showError(msg) {
    const app = document.getElementById('app');
    this.setContent(app,
      '<nav class="nav-bar"><a href="#/" class="nav-brand">whatsup</a></nav>' +
      '<main><div class="error-state"><p>' + this.esc(msg) + '</p><a href="#/">go home</a></div></main>');
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
