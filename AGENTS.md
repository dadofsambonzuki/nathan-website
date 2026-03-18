# AGENTS.md - Content Management Guide for Nathan's Hugo Website

This guide provides instructions for AI agents on how to manage content for Nathan Day's Hugo website.

## Project Overview

- **Framework**: Hugo static site generator
- **Theme**: hugo-coder
- **Repository**: `dadofsambonzuki/nathan-website`
- **Main Branch**: `master`

## Content Structure

The site has the following content sections:
- `posts/` - Blog posts
- `projects/` - Projects page
- `presentations/` - Presentation talks
- `podcasts/` - Podcast appearances
- `notes/` - Nostr Kind 1 notes (auto-synced)
- `articles/` - Nostr Kind 30023 articles (auto-synced)

## Adding Presentations

### File Location
Create file: `content/presentations/{event-slug}.md`

### Front Matter Template
```toml
+++
title = "Event Name: Presentation Title"
date = "YYYY-MM-DD"
draft = false
description = "Brief description"
tags = ["tag1", "tag2", "tag3"]
event = "Conference/Event Name"
location = "City, Country"
slides_url = "https://docs.google.com/presentation/d/.../"
video_url = "https://youtube.com/..."  # Optional
+++

## Overview

Brief description of what you covered in the presentation.

## Resources

{{< presentation-links >}}
```

### Guidelines
- Use kebab-case for filenames: `btc-prague-2025-my-talk.md`
- Always include `slides_url` (Google Slides preferred)
- Add relevant tags (e.g., "bitcoin", "nostr", "btcmap")
- Include date in YYYY-MM-DD format
- Use the shortcode `{{< presentation-links >}}` to display resource buttons

### Examples in Repository
- `btc-prague-dhd-2025-the-nuts-are-in-the-mail.md`
- `adopting-bitcoin-el-salvador-2023-spedn-with-btc-map.md`

## Adding Podcasts

### File Location
Create file: `content/podcasts/{podcast-slug}.md`

### Front Matter Template
```toml
+++
title = "Podcast Name (Episode): Episode Title"
date = "YYYY-MM-DD"
draft = false
description = "Brief description"
tags = ["bitcoin", "btcmap"]
podcast_name = "Podcast Name"
episode_number = "123"  # Optional
hosts = "Host Name(s)"  # Optional
fountain_url = "https://fountain.fm/episode/..."
youtube_url = "https://youtube.com/..."  # Optional
spotify_url = "https://spotify.com/..."  # Optional
apple_podcasts_url = "https://podcasts.apple.com/..."  # Optional
featuredImage = "https://image-url.jpg"  # Or "/images/local-image.png"
+++

## Episode Summary

Description of what you discussed in the episode.

## Listen

{{< podcast-links >}}

## Topics Covered (Optional)

- Topic 1
- Topic 2
- Topic 3
```

### Guidelines
- **Fountain URL should be listed first** - this is a user preference
- For `featuredImage`, use either:
  - Full URL: `https://...`
  - Local path: `/images/filename.png` (place image in `static/images/`)
- If adding images to `static/images/`, include them in your commits
- Use the shortcode `{{< podcast-links >}}` to display listening buttons

### Examples in Repository
- `stephan-livera-420-btc-map-mapping-bitcoin-merchants.md`
- `frees-cities-093-overlanding-self-sovereign-identity-and-bitcoin-adoption.md`

## Adding Blog Posts

### File Location
Create file: `content/posts/{post-slug}.md`

### Front Matter Template
```toml
+++
title = "Post Title"
date = "YYYY-MM-DD"
draft = false
description = "Brief description"
tags = ["tag1", "tag2"]
+++

Content here...
```

## Branch and PR Workflow

1. **Create a feature branch from master:**
   ```bash
   git checkout master
   git pull origin master
   git checkout -b descriptive-branch-name
   ```

2. **Make changes and commit:**
   ```bash
   git add <files>
   git commit -m "Description of changes"
   ```

3. **Push and create PR:**
   ```bash
   git push -u origin descriptive-branch-name
   gh pr create --title "Description" --body "Summary of changes" --base master
   ```

## Technical Preferences

- **Fountain links** must be listed **first** in podcast episodes
- **Featured images** should be **50% width** (not full width) - this is controlled by template
- **Nostr icon hover** should be **Nostr purple** (#662482), not standard blue
- **Tag pages** use **emojis** for content types:
  - 🎙️ Podcasts
  - 📊 Presentations
  - 📝 Posts
  - 💭 Notes
  - 📄 Articles

## Images

### Static Images
- Place in: `static/images/`
- Reference with: `/images/filename.png`

### Podcast/Presentation Cover Art
- Can use external URLs (Fountain, YouTube, etc.)
- Or place local files in `static/images/`

## Important Notes

1. **Never commit build output** - `public/` and `resources/` are gitignored
2. **Nostr content is auto-synced** - Don't manually edit files in `content/notes/` or `content/articles/`
3. **Unlisted content** - Files in `/unlisted` directory are excluded from tag pages
4. **Use shortcodes** for resource links:
   - `{{< podcast-links >}}` for podcasts
   - `{{< presentation-links >}}` for presentations

## Development Commands

```bash
# Preview locally
hugo server -D

# Build for production
hugo

# Check site status
hugo server --bind 0.0.0.0 -D
```

## Template Files

- `layouts/podcasts/single.html` - Podcast page layout
- `layouts/presentations/single.html` - Presentation page layout
- `layouts/shortcodes/podcast-links.html` - Podcast resource buttons
- `layouts/shortcodes/presentation-links.html` - Presentation resource buttons
- `layouts/tags/term.html` - Tag page with content type emojis
- `layouts/tags/terms.html` - Tags index page

## Configuration

Key files:
- `hugo.toml` - Site configuration, navigation menu, analytics
- `assets/css/` - Custom styles
- `layouts/` - Custom templates
- `scripts/` - Nostr sync scripts (don't modify without understanding)

## Questions?

If unsure about anything, ask the user before making changes. It's better to clarify than to guess with content that represents their public website.
