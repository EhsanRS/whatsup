# whatsup

A personal micro-status timeline that lives in your Git repo and deploys as a static site. Post quick updates, moods, links, and GIFs from the command line -- they show up on your own timeline page, hosted on GitHub Pages (or anywhere static).

No database. No backend. No dependencies. Just a bash script, some JSON files, and a vanilla JS frontend.

## What it looks like

A two-column layout with a warm, cream-toned IBM retro aesthetic:

- **Left sidebar** -- your current mood (big emoji or GIF), name, bio, date, and navigation
- **Right timeline** -- scrollable feed of your entries for the day, with timestamps and tags
- **Mobile** -- sidebar collapses to a compact mood banner above the timeline

Entry types: plain posts, mood updates, link shares, replies, GIF attachments, and PDF attachments.

## Quick start

```bash
# Clone and initialize
git clone <your-repo-url>
cd whatsup
./whatsup --init

# Post your first update
./whatsup "Hello world!"

# Preview locally
./whatsup --serve
# Open http://localhost:8000
```

The `--init` command creates the `data/` directory, `config.json`, and the entry manifest. Every post auto-commits and pushes to your repo.

## Usage

```bash
# Simple post
./whatsup "Working on the new feature"

# Mood update
./whatsup --mood focused "Deep work session"

# Share a link
./whatsup --link https://example.com/article "Great read on distributed systems"

# Attach a GIF
./whatsup --gif https://media.giphy.com/media/xyz/giphy.gif "Current vibe"

# Attach a PDF
./whatsup --pdf ./report.pdf "Q4 results"

# Reply to an entry
./whatsup --reply abc123 "Good point"

# Add tags (can use multiple times)
./whatsup --tag project --tag update "Shipped v2.0"

# Edit an existing entry
./whatsup --edit abc123 "Updated content"

# Delete an entry
./whatsup --delete abc123

# List today's entries
./whatsup --list

# Start local preview server
./whatsup --serve
```

### Available moods

`focused` `happy` `tired` `excited` `frustrated` `chill` `thinking` `creative`

Each mood gets its own emoji and accent color on the timeline.

## Configuration

Edit `config.json` to customize your profile:

```json
{
  "name": "Your Name",
  "bio": "What I'm up to",
  "avatar": "",
  "links": [],
  "timezone": "America/Los_Angeles"
}
```

The name and bio appear in the sidebar on the day view.

## How it works

### Data model

```
data/
  index.json              # Manifest: list of days with entry counts
  entries/
    2026-02-09.json       # All entries for that day
```

Each entry is a JSON object:

```json
{
  "id": "17799fa6",
  "ts": "2026-02-09T14:27:03Z",
  "type": "mood",
  "content": "Deep work session on the new project",
  "mood": "focused",
  "links": [],
  "attachments": [],
  "replyTo": null,
  "tags": ["productivity"]
}
```

Entry types: `post`, `mood`, `link`, `reply`. Attachments support `gif`, `image`, and `pdf`.

### Frontend

The web UI is a single-page app built with vanilla JS (no framework, no build step):

- `index.html` -- shell that loads the app
- `app.js` -- routing, data fetching, and rendering
- `style.css` -- IBM Plex Mono typography, warm cream palette, two-column layout

Hash-based routing:
- `#/` or `#/2026-02-09` -- day view (two-column with mood sidebar)
- `#/2026-02` -- month calendar view
- `#/archive` -- archive listing by year/month

### Git-powered workflow

Every `./whatsup` post automatically:
1. Creates/updates the day's JSON file in `data/entries/`
2. Updates the manifest in `data/index.json`
3. Commits the changes
4. Pushes to the remote

This means your timeline is version-controlled and deployable anywhere that serves static files.

## Deployment

### GitHub Pages

1. Push the repo to GitHub
2. Go to Settings > Pages
3. Set source to the `main` branch, root directory
4. Your timeline is live at `https://<username>.github.io/<repo>/`

The `.nojekyll` file is included so GitHub Pages serves the files directly.

### Other static hosts

Works with any static hosting (Netlify, Vercel, Cloudflare Pages, S3, etc.) -- just point it at the repo root.

## File structure

```
whatsup              # CLI script (bash)
index.html           # App shell
app.js               # Frontend rendering engine
style.css            # Styles (IBM retro light theme)
config.json          # User profile configuration
404.html             # Custom 404 page
.nojekyll            # Tells GitHub Pages to skip Jekyll
data/
  index.json         # Day manifest
  entries/           # Per-day entry files
assets/              # Uploaded PDFs
```

## Design

The visual design draws from the IBM Model M keyboard era -- warm cream backgrounds, charcoal text, IBM Plex Mono typography, and subtle red-brown accents. Clean and readable, not flashy.

### Palette

| Role       | Color     | Hex       |
|------------|-----------|-----------|
| Background | Warm cream | `#f5f0e8` |
| Cards      | Warm white | `#fffdf7` |
| Text       | Charcoal  | `#2c2c2c` |
| Muted      | Warm gray | `#8a8478` |
| Accent     | IBM red   | `#c8553d` |
| Links      | Classic blue | `#2a5aa7` |
| Borders    | Warm beige | `#d9d0c1` |

## Requirements

- Bash
- Python 3 (for the CLI -- entry creation, manifest updates, local server)
- Git
- A modern web browser

## License

Apache 2.0
