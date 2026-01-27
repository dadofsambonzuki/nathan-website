# Nostr Event Sync Script

This script fetches Nostr events (Kind 1 Notes and Kind 30023 Articles) from relays and generates Hugo markdown files for your website.

## Features

- **Incremental sync**: Only fetches new events since last sync
- **NIP-65 relay discovery**: Automatically uses your relay list
- **Smart filtering**: Excludes replies from notes (configurable)
- **Replaceable events**: Handles article updates correctly
- **Toggle support**: Enable/disable Notes and Articles independently
- **Dry-run mode**: Preview changes without writing files

## Setup

### 1. Install Python Dependencies

```bash
pip install -r scripts/requirements.txt
```

Or using a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r scripts/requirements.txt
```

### 2. Configure

Copy the example config and add your npub:

```bash
cp scripts/nostr_config.json.example scripts/nostr_config.json
```

Edit `scripts/nostr_config.json` and replace the example npub with yours:

```json
{
  "npub": "npub1qqqqqqq...",
  "enable_notes": true,
  "enable_articles": true,
  ...
}
```

**Configuration options:**

- `npub`: Your Nostr public key in npub format (required)
- `enable_notes`: Fetch Kind 1 notes (default: true)
- `enable_articles`: Fetch Kind 30023 articles (default: true)
- `fallback_relays`: Relays to use if NIP-65 relay list not found
- `notes_config.exclude_replies`: Don't sync replies (default: true)
- `notes_config.max_fetch_per_sync`: Limit notes per sync (default: 100)
- `notes_config.ignore_event_ids`: Array of event IDs to exclude from sync
- `articles_config.max_fetch_per_sync`: Limit articles per sync (default: 50)
- `articles_config.ignore_identifiers`: Array of article identifiers (d tags) to exclude from sync

## Usage

### Basic Sync

Fetch new events and generate markdown files:

```bash
python scripts/fetch_nostr_events.py
```

### Dry Run

Preview what would be synced without writing files:

```bash
python scripts/fetch_nostr_events.py --dry-run
```

### Force Full Resync

Clear state and refetch everything:

```bash
python scripts/fetch_nostr_events.py --force-resync
```

### Verbose Mode

Show detailed logging:

```bash
python scripts/fetch_nostr_events.py --verbose
```

### Custom Config Path

Use a different config file:

```bash
python scripts/fetch_nostr_events.py --config path/to/config.json
```

## How It Works

### First Run

1. Reads your npub from config
2. Fetches your NIP-65 relay list (Kind 10002)
3. Connects to those relays (or fallback relays)
4. Fetches ALL Kind 1 notes and Kind 30023 articles
5. Generates markdown files in `content/notes/` and `content/articles/`
6. Saves sync state to `scripts/nostr_sync_state.json`

### Subsequent Runs

1. Reads last sync timestamps from state file
2. Fetches only events NEWER than last sync
3. Updates existing files if event was updated
4. Saves new state

### State File

`scripts/nostr_sync_state.json` tracks:

- Last sync timestamp
- Last note/article timestamps (for incremental fetch)
- Synced event IDs (to detect updates)

**Important**: This file is gitignored. If you delete it, the next sync will be a full resync.

## Generated Files

### Notes

Files are created at `content/notes/{event-id-prefix}.md`:

- Filename: First 8 characters of event ID
- Front matter: date, nostr_kind, nostr_event_id, nostr_nevent, tags
- Content: Full note text
- Hidden JSON: Full event data for templates

### Articles

Files are created at `content/articles/{slug}.md`:

- Filename: Slugified title or 'd' tag identifier
- Front matter: title, date, description, reading_time, nostr_kind, nostr_naddr, tags
- Content: Full article markdown
- Hidden JSON: Full event data for templates

## Hugo Integration

After syncing, build your Hugo site:

```bash
hugo server -D  # Preview locally
hugo            # Build for production
```

The generated markdown files are **not committed to git** (see `.gitignore`), so you need to:

1. Run the sync script locally before building
2. OR run it as part of your deployment pipeline
3. OR build and deploy the `public/` folder locally

## Toggle Notes/Articles

To disable syncing notes or articles:

**In config** (`scripts/nostr_config.json`):
```json
{
  "enable_notes": false,
  "enable_articles": true
}
```

**In Hugo** (`hugo.toml`):
```toml
[params.nostr]
enable_notes = false
enable_articles = true
```

**In navigation** (comment out in `hugo.toml`):
```toml
# [[menu.main]]
# name = "Notes"
# weight = 4
# url = "notes/"
```

## Troubleshooting

### "nostr-sdk not installed"

Install dependencies:
```bash
pip install -r scripts/requirements.txt
```

### "Config file not found"

Create config from example:
```bash
cp scripts/nostr_config.json.example scripts/nostr_config.json
```

### No events found

1. Check your npub is correct in config
2. Try force resync: `python scripts/fetch_nostr_events.py --force-resync`
3. Use verbose mode to see relay responses: `--verbose`
4. Check if relays are responding (might be rate limited or down)

### Events not appearing on website

1. Make sure sync completed successfully
2. Rebuild Hugo: `hugo`
3. Check that `enable_notes`/`enable_articles` is true in both config and hugo.toml
4. Verify generated markdown files exist in `content/notes/` or `content/articles/`

### Want to re-sync everything

Delete the state file and run again:
```bash
rm scripts/nostr_sync_state.json
python scripts/fetch_nostr_events.py
```

Or use the `--force-resync` flag.

## Workflow Example

### Daily workflow:

```bash
# Fetch new Nostr events
python scripts/fetch_nostr_events.py

# Preview locally
hugo server -D

# Build for production
hugo

# Deploy (your deployment method here)
rsync -avz public/ user@server:/var/www/
```

### Weekly full resync:

```bash
python scripts/fetch_nostr_events.py --force-resync --verbose
```

## File Structure

```
scripts/
├── fetch_nostr_events.py       # Main sync script
├── requirements.txt            # Python dependencies
├── nostr_config.json.example   # Config template
├── nostr_config.json           # Your config (gitignored)
├── nostr_sync_state.json       # Sync state (gitignored)
├── nostr_events/               # Event cache (gitignored)
└── README.md                   # This file

content/
├── notes/
│   ├── _index.md              # Notes section index (committed)
│   └── *.md                   # Generated notes (gitignored)
└── articles/
    ├── _index.md              # Articles section index (committed)
    └── *.md                   # Generated articles (gitignored)
```

## Advanced

### Custom relay list

Override NIP-65 by editing `fallback_relays` in config. The script will use these if it can't fetch your relay list.

### Filter by hashtags

Currently not implemented, but you can modify the script to add hashtag filters in the `fetch_notes()` or `fetch_articles()` methods.

### Event deletion

The script doesn't currently handle Kind 5 deletion events. Deleted events on Nostr will remain on your website until you manually remove the markdown file.

### Scheduled sync

Set up a cron job to run the sync automatically:

```bash
# Sync every 6 hours
0 */6 * * * cd /path/to/nathan-website && /path/to/venv/bin/python scripts/fetch_nostr_events.py
```

## Support

If you encounter issues:

1. Run with `--verbose` flag to see detailed logs
2. Check the Nostr relay status (some relays have downtime)
3. Try `--force-resync` to clear state and start fresh
4. Check that your npub is valid and has published events

## License

Part of the nathan-website Hugo project.
