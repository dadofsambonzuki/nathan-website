# Development Notes - Nathan's Hugo Website

## Session: January 2026

### Project Context
Working on a Hugo static website for Nathan Day located at `/home/nathan-day/Code/nathan-website/` using the hugo-coder theme. The site includes a blog, projects page, and now presentations and podcasts sections.

## What Was Accomplished

### 1. Nostr Logo & Social Icon
- **Resized Nostr logo** in `content/_index.md` to 25% size using HTML img tag with inline style
- **Added custom Nostr social icon** with SVG support:
  - Created `layouts/partials/home/social.html` - Extended theme's social links to support SVG icons
  - Downloaded and optimized `static/images/nostr-icon.svg` (black transparent, viewBox adjusted from `0 0 256 256` to `40 40 176 176` to remove padding)
  - Created `assets/css/nostr-social.css` - Custom styling for SVG icons with Nostr purple (#662482) hover effects in both light/dark themes
  - Updated `hugo.toml` to include custom CSS and Nostr social link
  - Icon uses `2em` sizing to match Font Awesome `fa-2x` icons

### 2. Presentations & Podcasts Sections (Option 2 - Full Section Directories)
**Directory structure created:**
```
content/
├── presentations/
│   ├── _index.md (landing page)
│   ├── example-presentation.md (template)
│   └── btc-prague-dhd-2025.md
└── podcasts/
    ├── _index.md (landing page)
    ├── example-podcast.md (template)
    ├── stephan-livera-420.md
    └── [8 more podcast episodes]
```

**Navigation menu updated** in `hugo.toml`:
- About (1) → Blog (2) → Projects (3) → Presentations (4) → Podcasts (5) → Tags (6)

### 3. Custom Shortcodes for Media Links
Created `layouts/shortcodes/podcast-links.html` and `layouts/shortcodes/presentation-links.html`:

**Podcast shortcode** reads from front matter and displays:
- Fountain (⚡ bolt icon) - **listed first per user request**
- YouTube (fa-brands fa-youtube)
- Spotify (fa-brands fa-spotify)
- Apple Podcasts (fa-brands fa-apple)
- Generic audio URL (fa-solid fa-podcast)

**Presentation shortcode** displays:
- Slides (fa-solid fa-display)
- Video (fa-solid fa-video)
- Additional resources (fa-solid fa-link)

**Usage:** `{{< podcast-links >}}` or `{{< presentation-links >}}` in markdown content

### 4. Custom Single Page Templates
Created `layouts/podcasts/single.html` and `layouts/presentations/single.html`:
- Display featured images at **50% width** (not 100%)
- Show metadata like blog posts: date (calendar icon), reading time (clock icon), tags
- Uses theme's `post-meta` styling for consistency
- Featured images loaded from front matter `featuredImage` parameter

### 5. Podcast Episodes Added
Created 9 podcast episodes from Fountain playlist (https://fountain.fm/playlist/MvvFtkl967NzpjEok5LV):
1. **PCR66** - Putting Nostr On The Map (Jun 22, 2024)
2. **Daniel Prince #298** - BTCMap & Overlanding (Nov 22, 2022)
3. **SLP420** - Stephan Livera - BTCMap Mapping Merchants (Oct 6, 2022)
4. **Once BITten!** - Accept Bitcoin, Put Yourself on the Map (Feb 24, 2023)
5. **Ungovernable Misfits** - NOSTR is PGP for the masses (Nov 15, 2023 - estimated, it's a clip)
6. **Free Cities #93** - Overlanding & SSI (Aug 30, 2024)
7. **Connect The World** - BTCMAP.ORG (May 14, 2025)
8. **PCR120** - Attestations All the Way Down (Jul 12, 2025)
9. **Everyday Bitcoin #1** - Nathan Day BTCmap (Oct 16, 2025)

All episodes include:
- Fountain URLs (primary listening link)
- Featured images (podcast artwork from Fountain)
- Proper metadata (hosts, episode numbers, descriptions)
- Relevant tags

### 6. Enhanced Tag System (Phase 1 Enhancements)
**Created custom tag templates:**
- `layouts/tags/terms.html` - Tags index page shows alphabetical list with counts (e.g., "bitcoin (8)"), no dates
- `layouts/tags/term.html` - Individual tag pages show content type emojis before titles:
  - 🎙️ Podcasts
  - 📊 Presentations
  - 📝 Posts

**Key feature:** Both templates **exclude `/unlisted` content** from appearing in tags (important - there are old travel blog posts in `/unlisted` that shouldn't pollute the tag system)

**Added Tags to navigation menu** (weight 6, at the end)

### 7. Umami Analytics
Added analytics tracking in `hugo.toml`:
```toml
[params.umami]
siteID = "98a4f246-3482-4055-a059-78ae57d9a1ca"
scriptURL = "https://umami.btcmap.org/script.js"
```
Theme has built-in Umami support, so this was just configuration.

### 8. Repository Cleanup
- Created `.gitignore` to exclude `public/`, `resources/`, OS files, editor files
- Removed all previously tracked build output files from git
- Repository now only tracks source files

## Current File Structure

### Key Files Modified/Created:
```
nathan-website/
├── .gitignore (MODIFIED - excludes public/, resources/, Nostr generated content)
├── hugo.toml (MODIFIED - Nostr social, nav menu with Notes/Articles, Nostr params, Umami)
├── scripts/ (NEW - Nostr sync)
│   ├── fetch_nostr_events.py (NEW - main sync script)
│   ├── requirements.txt (NEW - Python dependencies)
│   ├── nostr_config.json.example (NEW - config template)
│   ├── nostr_config.json (gitignored - user config)
│   ├── nostr_sync_state.json (gitignored - sync state)
│   ├── nostr_events/ (gitignored - event cache)
│   └── README.md (NEW - sync script documentation)
├── content/
│   ├── _index.md (MODIFIED - Nostr logo resized to 25%)
│   ├── presentations/ (NEW - section directory)
│   │   ├── _index.md
│   │   ├── example-presentation.md
│   │   └── btc-prague-dhd-2025.md
│   ├── podcasts/ (NEW - section directory)
│   │   ├── _index.md
│   │   ├── example-podcast.md
│   │   └── [9 podcast episode files]
│   ├── notes/ (NEW - Nostr notes section)
│   │   ├── _index.md (committed)
│   │   └── *.md (gitignored - generated by sync script)
│   └── articles/ (NEW - Nostr articles section)
│       ├── _index.md (committed)
│       └── *.md (gitignored - generated by sync script)
├── layouts/
│   ├── partials/
│   │   └── home/
│   │       └── social.html (NEW - SVG icon support)
│   ├── podcasts/
│   │   └── single.html (NEW - custom template with featured images)
│   ├── presentations/
│   │   └── single.html (NEW - custom template with featured images)
│   ├── notes/ (NEW - Nostr notes templates)
│   │   ├── list.html (NEW - full content inline)
│   │   └── single.html (NEW - with View on Nostr links)
│   ├── articles/ (NEW - Nostr articles templates)
│   │   ├── list.html (NEW - title/desc/tags)
│   │   └── single.html (NEW - full article with metadata)
│   ├── shortcodes/
│   │   ├── podcast-links.html (NEW)
│   │   ├── presentation-links.html (NEW)
│   │   └── nostr-view-links.html (NEW - multi-client Nostr links)
│   └── tags/
│       ├── terms.html (NEW - alphabetical index)
│       └── term.html (MODIFIED - with content type emojis including Notes 💭 and Articles 📄)
├── assets/css/
│   └── nostr-social.css (NEW - Nostr icon styling)
└── static/images/
    └── nostr-icon.svg (NEW - optimized viewBox)
```

## Important Technical Decisions

1. **SVG Icon Sizing**: Fixed by adjusting SVG viewBox to remove internal padding (40 40 176 176), allowing proper 2em sizing
2. **Nostr Purple Hover**: Uses CSS filters to convert black → Nostr purple (#662482) on hover
3. **Fountain First**: Podcast links always show Fountain as first option (user preference)
4. **Featured Images**: 50% width, not 100% (user preference)
5. **Emoji Content Types**: Using emojis (🎙️📊📝) instead of Font Awesome icons for content type indicators on tag pages
6. **Exclude Unlisted**: Critical filter in tag templates to prevent old travel blog posts from appearing

## Key User Preferences to Remember

- Fountain links must be listed **first** in podcast episodes
- Nostr icon hover should be **Nostr purple** (#662482), not standard blue
- Featured images should be **50% width**, not full width
- Tag pages should use **emojis** for content types, not Font Awesome icons
- Content in `/unlisted` directory must be **excluded from tag pages**
- Build output (`public/`, `resources/`) should **never be committed** to git
- **Nostr sync should be incremental**, not full resync every time
- **Generated Nostr markdown files should NOT be committed** to git
- Notes and Articles can be **toggled on/off** independently in config
- Notes display **full content inline** on list page (social feed style)
- Articles display **title/description/tags** on list page (blog style)

### 9. Nostr Integration (Kind 1 Notes & Kind 30023 Articles)
**Created on nostr-integration branch (Jan 2026)**

Integrated Nostr events as content sections with incremental sync.

**Python Sync Script** (`scripts/fetch_nostr_events.py`):
- Fetches Kind 1 notes and Kind 30023 articles from Nostr relays
- Uses NIP-65 relay list discovery (falls back to configured relays)
- Incremental sync with state tracking (`scripts/nostr_sync_state.json`)
- Excludes replies from notes (configurable)
- Handles replaceable events (articles) correctly
- CLI flags: `--dry-run`, `--force-resync`, `--verbose`
- Generates markdown files with minimal frontmatter
- Full event JSON embedded in HTML comments for template access
- Notes: filename = first 8 chars of event ID
- Articles: filename = slugified title or 'd' tag identifier

**Hugo Layouts**:
- `layouts/notes/list.html` - Shows full note content inline on listing page
- `layouts/notes/single.html` - Individual note page with "View on Nostr" links
- `layouts/articles/list.html` - Shows title, description, reading time, tags
- `layouts/articles/single.html` - Full article with metadata (like blog posts)
- `layouts/shortcodes/nostr-view-links.html` - Multi-client view links (Primal, Nostrudel, Snort, Coracle)

**Content Sections**:
- `content/notes/` - Kind 1 notes (markdown files gitignored except _index.md)
- `content/articles/` - Kind 30023 articles (markdown files gitignored except _index.md)

**Configuration**:
- `scripts/nostr_config.json` - Sync script config (gitignored, copy from .example)
  - Toggle notes/articles independently
  - Configure max fetch limits
  - Exclude replies option
- `hugo.toml` - Added Nostr params and navigation
  - `[params.nostr]` section with enable flags
  - Navigation: Projects → Presentations → Podcasts → Notes → Articles → Tags
  - Blog menu item commented out (Articles replaces it)

**Tag System Integration**:
- Notes emoji: 💭 (added to `layouts/tags/term.html`)
- Articles emoji: 📄 (added to `layouts/tags/term.html`)
- Tags automatically mapped from Nostr 't' tags

**Workflow**:
1. Run `python scripts/fetch_nostr_events.py` to sync events
2. Build Hugo site as normal
3. Generated markdown files are NOT committed to git
4. State file tracks incremental sync

**Key Design Decisions**:
- Incremental sync to avoid refetching entire history each time
- Generated content not committed (only source code committed)
- Toggle support for disabling Notes/Articles in config
- nevent/naddr encoding for universal Nostr client compatibility
- Notes show full content inline on list page (like social feed)
- Articles show summary on list page (like traditional blog)
- Reading time calculated from content length for articles
- "View on Nostr" links to multiple clients (not just one)

## Potential Next Steps (Not Started)

If user wants to continue:
- Add more podcast episodes from Fountain playlist if any were missed
- Add actual presentation entries (only example exists currently)
- Add YouTube/Spotify/Apple Podcasts URLs to existing podcast episodes (currently only have Fountain URLs)
- Phase 2 tag enhancements (if desired): tag cloud, content type breakdown stats, filter buttons
- Add more content to podcasts/presentations sections
- Find exact date for Ungovernable Misfits clip (currently estimated as Nov 15, 2023)
- Test Nostr sync script with real npub and events
- Set up automated sync (cron job or deployment pipeline)
- Add Kind 5 (deletion) event handling to remove deleted notes/articles
- Add hashtag filtering for notes/articles

## Git Commits

Key commits from previous sessions:
- Initial Nostr icon and presentations/podcasts setup
- Tag system enhancements with content type emojis
- Umami analytics integration
- Repository cleanup (.gitignore and removal of build output)
- Commit: 0379177

Nostr integration branch (nostr-integration):
- Not yet committed/merged - work in progress

## Development Environment

- Hugo dev server: `hugo server -D` runs on `127.0.0.1:1313`
- Theme: hugo-coder
- Working directory: `/home/nathan-day/Code/nathan-website`
- Git repository: Active, changes pushed to GitHub
