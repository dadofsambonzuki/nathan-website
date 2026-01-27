#!/usr/bin/env python3
"""
Nostr Event Fetcher for Hugo Website
Fetches Kind 1 (Notes) and Kind 30023 (Articles) from Nostr relays
and generates Hugo markdown files with incremental sync support.
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple
import re

try:
    from nostr_sdk import (
        Client, Filter, PublicKey, Event,
        Kind, Timestamp, Nip19, RelayUrl, SyncOptions
    )
    # Import Duration for fetch_events
    from datetime import timedelta
except ImportError:
    print("Error: nostr-sdk not installed. Run: pip install nostr-sdk")
    sys.exit(1)


class NostrEventFetcher:
    def __init__(self, config_path: str = "scripts/nostr_config.json", verbose: bool = False):
        self.verbose = verbose
        self.config = self._load_config(config_path)
        self.state_file = Path("scripts/nostr_sync_state.json")
        self.state = self._load_state()
        self.client = None
        self.public_key = None
        
        # Stats
        self.stats = {
            "notes": {"new": 0, "updated": 0, "deleted": 0, "total": 0},
            "articles": {"new": 0, "updated": 0, "deleted": 0, "total": 0},
            "relays_queried": 0,
            "start_time": time.time()
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            if 'npub' not in config:
                raise ValueError("npub is required in config")
            
            return config
        except FileNotFoundError:
            print(f"Error: Config file not found at {config_path}")
            print("Copy nostr_config.json.example to nostr_config.json and add your npub")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)
    
    def _load_state(self) -> Dict:
        """Load sync state from file or create new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Could not parse state file, creating new state")
        
        return {
            "last_sync": None,
            "last_note_timestamp": 0,
            "last_article_timestamp": 0,
            "synced_note_ids": [],
            "synced_article_ids": []
        }
    
    def _save_state(self):
        """Save sync state to file."""
        self.state["last_sync"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        
        if self.verbose:
            print(f"State saved to {self.state_file}")
    
    def _log(self, message: str):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message)
    
    async def _setup_client(self):
        """Initialize Nostr client and connect to relays."""
        # Parse npub to get public key
        try:
            decoded = Nip19.from_bech32(self.config['npub'])
            decoded_enum = decoded.as_enum()
            
            # Get the public key from the decoded enum
            self.public_key = decoded_enum.npub
            self._log(f"Parsed public key: {self.public_key.to_hex()}")
        except Exception as e:
            print(f"Error: Could not parse npub: {e}")
            sys.exit(1)
        
        # Create client
        self.client = Client()
        
        # Get relays from NIP-65 or use fallback
        relays = await self._get_user_relays()
        
        if not relays:
            relays = self.config.get('fallback_relays', [])
            self._log("Using fallback relays")
        
        # Add relays
        for relay in relays:
            try:
                relay_url = RelayUrl.parse(relay)
                await self.client.add_relay(relay_url)
                self._log(f"Added relay: {relay}")
            except Exception as e:
                print(f"Warning: Could not add relay {relay}: {e}")
        
        # Connect
        await self.client.connect()
        self.stats["relays_queried"] = len(relays)
        self._log(f"Connected to {len(relays)} relays")
    
    async def _get_user_relays(self) -> List[str]:
        """Fetch user's NIP-65 relay list."""
        try:
            # First connect to fallback relays to fetch NIP-65
            temp_client = Client()
            for relay in self.config.get('fallback_relays', []):
                relay_url = RelayUrl.parse(relay)
                await temp_client.add_relay(relay_url)
            
            await temp_client.connect()
            
            # Fetch Kind 10002 (NIP-65 relay list)
            filter_relays = Filter().author(self.public_key).kind(Kind(10002)).limit(1)
            
            # Fetch relay list event
            events = await temp_client.fetch_events(filter_relays, timeout=timedelta(seconds=10))
            
            if not events.is_empty():
                # Parse relay list from tags
                relay_event = events.first()
                relays = []
                tags = relay_event.tags().to_vec()
                for tag in tags:
                    tag_list = tag.as_vec()
                    if len(tag_list) >= 2 and tag_list[0] == 'r':
                        relays.append(tag_list[1])
                
                self._log(f"Found {len(relays)} relays from NIP-65")
                return relays
            else:
                self._log("No NIP-65 relay list found")
                return []
        
        except Exception as e:
            self._log(f"Could not fetch NIP-65 relay list: {e}")
            return []
    
    async def fetch_notes(self) -> List[Event]:
        """Fetch Kind 1 notes with incremental sync."""
        if not self.config.get('enable_notes', True):
            self._log("Notes sync disabled in config")
            return []
        
        self._log("Fetching Kind 1 notes...")
        
        # Build filter
        filter_notes = (
            Filter()
            .author(self.public_key)
            .kind(Kind(1))
        )
        
        # Add since timestamp for incremental sync
        if self.state["last_note_timestamp"] > 0:
            filter_notes = filter_notes.since(Timestamp.from_secs(self.state["last_note_timestamp"]))
            self._log(f"Fetching notes since timestamp: {self.state['last_note_timestamp']}")
        else:
            self._log("Fetching all notes (first sync)")
        
        # Add limit
        max_fetch = self.config.get('notes_config', {}).get('max_fetch_per_sync', 100)
        filter_notes = filter_notes.limit(max_fetch)
        
        # Fetch events directly from relays
        self._log("Fetching from relays...")
        events = await self.client.fetch_events(filter_notes, timeout=timedelta(seconds=30))
        events_list = events.to_vec()
        
        self._log(f"Fetched {len(events_list)} note events")
        
        # Filter out replies if configured
        if self.config.get('notes_config', {}).get('exclude_replies', True):
            events_list = [e for e in events_list if not self._is_reply(e)]
            self._log(f"After filtering replies: {len(events_list)} notes")
        
        # Filter out ignored event IDs
        ignore_list = self.config.get('notes_config', {}).get('ignore_event_ids', [])
        if ignore_list:
            events_list = [e for e in events_list if e.id().to_hex() not in ignore_list]
            self._log(f"After filtering ignored events: {len(events_list)} notes")
        
        return events_list
    
    async def fetch_articles(self) -> List[Event]:
        """Fetch Kind 30023 articles with incremental sync."""
        if not self.config.get('enable_articles', True):
            self._log("Articles sync disabled in config")
            return []
        
        self._log("Fetching Kind 30023 articles...")
        
        # Build filter
        filter_articles = (
            Filter()
            .author(self.public_key)
            .kind(Kind(30023))
        )
        
        # Add since timestamp for incremental sync
        if self.state["last_article_timestamp"] > 0:
            filter_articles = filter_articles.since(Timestamp.from_secs(self.state["last_article_timestamp"]))
            self._log(f"Fetching articles since timestamp: {self.state['last_article_timestamp']}")
        else:
            self._log("Fetching all articles (first sync)")
        
        # Add limit
        max_fetch = self.config.get('articles_config', {}).get('max_fetch_per_sync', 50)
        filter_articles = filter_articles.limit(max_fetch)
        
        # Fetch events directly from relays
        self._log("Fetching from relays...")
        events = await self.client.fetch_events(filter_articles, timeout=timedelta(seconds=30))
        events_list = events.to_vec()
        
        self._log(f"Fetched {len(events_list)} article events")
        
        # Filter out ignored identifiers
        ignore_list = self.config.get('articles_config', {}).get('ignore_identifiers', [])
        if ignore_list:
            events_list = [e for e in events_list if self._get_article_identifier(e) not in ignore_list]
            self._log(f"After filtering ignored articles: {len(events_list)} articles")
        
        return events_list
    
    def _is_reply(self, event: Event) -> bool:
        """Check if a note is a reply based on NIP-10."""
        tags = event.tags().to_vec()
        for tag in tags:
            tag_list = tag.as_vec()
            if len(tag_list) >= 1 and tag_list[0] == 'e':
                # Has 'e' tag, likely a reply
                return True
        return False
    
    def _get_article_identifier(self, event: Event) -> str:
        """Get the 'd' tag identifier for an article."""
        tags = event.tags().to_vec()
        for tag in tags:
            tag_list = tag.as_vec()
            if len(tag_list) >= 2 and tag_list[0] == 'd':
                return tag_list[1]
        
        # Fallback to event ID if no 'd' tag
        return event.id().to_hex()[:8]
    
    def _get_tags_from_event(self, event: Event) -> List[str]:
        """Extract 't' tags from event."""
        result = []
        tags = event.tags().to_vec()
        for tag in tags:
            tag_list = tag.as_vec()
            if len(tag_list) >= 2 and tag_list[0] == 't':
                result.append(tag_list[1])
        return result
    
    def _get_article_metadata(self, event: Event) -> Dict:
        """Extract article metadata from tags."""
        metadata = {
            "title": None,
            "summary": None,
            "image": None,
            "published_at": None
        }
        
        tags = event.tags().to_vec()
        for tag in tags:
            tag_list = tag.as_vec()
            if len(tag_list) >= 2:
                tag_name = tag_list[0]
                tag_value = tag_list[1]
                
                if tag_name == 'title':
                    metadata['title'] = tag_value
                elif tag_name == 'summary':
                    metadata['summary'] = tag_value
                elif tag_name == 'image':
                    metadata['image'] = tag_value
                elif tag_name == 'published_at':
                    try:
                        metadata['published_at'] = int(tag_value)
                    except ValueError:
                        pass
        
        return metadata
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and special chars with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        # Limit length
        return text[:60]
    
    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (200 words per minute)."""
        words = len(content.split())
        minutes = max(1, round(words / 200))
        return minutes
    
    def _encode_nevent(self, event_id_hex: str) -> str:
        """Encode event ID to nevent/note."""
        try:
            from nostr_sdk import EventId
            event_id = EventId.parse(event_id_hex)
            return event_id.to_bech32()
        except Exception as e:
            self._log(f"Error encoding nevent: {e}")
            return event_id_hex
    
    def _encode_naddr(self, identifier: str, pubkey_hex: str, kind: int = 30023) -> str:
        """Encode article to naddr using coordinate format."""
        try:
            from nostr_sdk import Coordinate, Kind, PublicKey
            pk = PublicKey.parse(pubkey_hex)
            coord = Coordinate(Kind(kind), pk, identifier)
            # Return the coordinate string format (kind:pubkey:identifier)
            # Most clients accept this or we can use event ID as fallback
            return str(coord)
        except Exception as e:
            self._log(f"Error encoding naddr: {e}")
            return identifier
    
    def _generate_note_markdown(self, event: Event) -> Tuple[str, str]:
        """Generate markdown file for a note."""
        event_id = event.id().to_hex()
        filename = f"{event_id[:8]}.md"
        timestamp = event.created_at().as_secs()
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # Get nevent encoding
        nevent = self._encode_nevent(event_id)
        
        # Get tags
        tags = self._get_tags_from_event(event)
        tags_str = ', '.join([f'"{tag}"' for tag in tags]) if tags else ''
        
        # Create a short description (first 150 chars of content)
        content_preview = event.content().replace('\n', ' ').strip()[:150]
        
        # Create frontmatter
        frontmatter = f"""+++
title = "Note"
date = "{date.strftime('%Y-%m-%d %H:%M:%S')}+00:00"
draft = false
description = "{content_preview.replace('"', '\\"')}"
nostr_kind = 1
nostr_event_id = "{event_id}"
nostr_nevent = "{nevent}"
"""
        if tags:
            frontmatter += f"tags = [{tags_str}]\n"
        
        frontmatter += "+++"
        
        # Create content
        content = f"\n\n{event.content()}\n"
        
        # Add hidden event JSON for template access
        event_json = {
            "id": event_id,
            "pubkey": event.author().to_hex(),
            "created_at": timestamp,
            "kind": 1,
            "content": event.content(),
            "nevent": nevent
        }
        
        content += f"\n<!--\nNOSTR_EVENT_JSON:\n{json.dumps(event_json, indent=2)}\n-->\n"
        
        markdown = frontmatter + content
        
        return filename, markdown
    
    def _generate_article_markdown(self, event: Event) -> Tuple[str, str]:
        """Generate markdown file for an article."""
        identifier = self._get_article_identifier(event)
        metadata = self._get_article_metadata(event)
        
        # Determine filename from title or identifier
        if metadata['title']:
            slug = self._slugify(metadata['title'])
            filename = f"{slug}.md"
        else:
            filename = f"{identifier}.md"
        
        # Get timestamps
        timestamp = metadata.get('published_at') or event.created_at().as_secs()
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # Get naddr encoding
        event_id = event.id().to_hex()
        pubkey_hex = event.author().to_hex()
        naddr = self._encode_naddr(identifier, pubkey_hex, kind=30023)
        
        # Get tags
        tags = self._get_tags_from_event(event)
        tags_str = ', '.join([f'"{tag}"' for tag in tags]) if tags else ''
        
        # Estimate reading time
        reading_time = self._estimate_reading_time(event.content())
        
        # Create frontmatter
        title = metadata.get('title') or 'Untitled Article'
        
        # Get description from summary tag or first 200 chars of content
        description = metadata.get('summary')
        if not description:
            # Extract first 200 chars from content as description
            content_text = event.content().replace('\n', ' ').strip()
            description = content_text[:200] if len(content_text) > 200 else content_text
        
        frontmatter = f"""+++
title = "{title.replace('"', '\\"')}"
date = "{date.strftime('%Y-%m-%d %H:%M:%S')}+00:00"
draft = false
description = "{description.replace('"', '\\"')}"
nostr_kind = 30023
nostr_event_id = "{event_id}"
nostr_identifier = "{identifier}"
nostr_naddr = "{naddr}"
reading_time = {reading_time}
"""
        
        if metadata.get('image'):
            frontmatter += f'featuredImage = "{metadata["image"]}"\n'
        
        if tags:
            frontmatter += f"tags = [{tags_str}]\n"
        
        frontmatter += "+++"
        
        # Create content
        content = f"\n\n{event.content()}\n"
        
        # Add hidden event JSON for template access
        event_json = {
            "id": event_id,
            "pubkey": pubkey_hex,
            "created_at": timestamp,
            "kind": 30023,
            "identifier": identifier,
            "content": event.content(),
            "naddr": naddr,
            "metadata": metadata
        }
        
        content += f"\n<!--\nNOSTR_EVENT_JSON:\n{json.dumps(event_json, indent=2)}\n-->\n"
        
        markdown = frontmatter + content
        
        return filename, markdown
    
    def _write_markdown(self, content_type: str, filename: str, markdown: str):
        """Write markdown file to content directory."""
        content_dir = Path(f"content/{content_type}")
        content_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = content_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        self._log(f"Wrote {filepath}")
    
    def _process_notes(self, events: List[Event]):
        """Process note events and generate markdown."""
        for event in events:
            event_id = event.id().to_hex()
            
            # Check if already synced
            if event_id in self.state['synced_note_ids']:
                self.stats['notes']['updated'] += 1
                action = "Updated"
            else:
                self.stats['notes']['new'] += 1
                self.state['synced_note_ids'].append(event_id)
                action = "New"
            
            # Generate markdown
            filename, markdown = self._generate_note_markdown(event)
            self._write_markdown('notes', filename, markdown)
            
            # Update timestamp
            event_time = event.created_at().as_secs()
            if event_time > self.state['last_note_timestamp']:
                self.state['last_note_timestamp'] = event_time
            
            self._log(f"{action} note: {filename}")
        
        # Count total
        notes_dir = Path("content/notes")
        if notes_dir.exists():
            self.stats['notes']['total'] = len(list(notes_dir.glob("*.md"))) - 1  # Exclude _index.md
    
    def _process_articles(self, events: List[Event]):
        """Process article events and generate markdown."""
        # Group by identifier to handle replacements
        articles_by_id = {}
        for event in events:
            identifier = self._get_article_identifier(event)
            if identifier not in articles_by_id or event.created_at().as_secs() > articles_by_id[identifier].created_at().as_secs():
                articles_by_id[identifier] = event
        
        # Process latest version of each article
        for identifier, event in articles_by_id.items():
            # Check if already synced
            if identifier in self.state['synced_article_ids']:
                self.stats['articles']['updated'] += 1
                action = "Updated"
            else:
                self.stats['articles']['new'] += 1
                self.state['synced_article_ids'].append(identifier)
                action = "New"
            
            # Generate markdown
            filename, markdown = self._generate_article_markdown(event)
            self._write_markdown('articles', filename, markdown)
            
            # Update timestamp
            event_time = event.created_at().as_secs()
            if event_time > self.state['last_article_timestamp']:
                self.state['last_article_timestamp'] = event_time
            
            self._log(f"{action} article: {filename}")
        
        # Count total
        articles_dir = Path("content/articles")
        if articles_dir.exists():
            self.stats['articles']['total'] = len(list(articles_dir.glob("*.md"))) - 1  # Exclude _index.md
    
    def _print_stats(self):
        """Print sync statistics."""
        duration = time.time() - self.stats['start_time']
        
        print("\nNostr Event Sync Complete")
        print("=" * 50)
        print(f"Notes:    {self.stats['notes']['new']} new, {self.stats['notes']['updated']} updated, "
              f"{self.stats['notes']['deleted']} deleted ({self.stats['notes']['total']} total)")
        print(f"Articles: {self.stats['articles']['new']} new, {self.stats['articles']['updated']} updated, "
              f"{self.stats['articles']['deleted']} deleted ({self.stats['articles']['total']} total)")
        print(f"Relays queried: {self.stats['relays_queried']}")
        print(f"Duration: {duration:.1f}s")
        print("=" * 50)
    
    async def sync(self, dry_run: bool = False):
        """Main sync function."""
        print("Starting Nostr event sync...")
        
        if dry_run:
            print("DRY RUN MODE - No files will be written")
        
        # Setup client and connect to relays
        await self._setup_client()
        
        # Fetch events
        notes = await self.fetch_notes()
        articles = await self.fetch_articles()
        
        if dry_run:
            print(f"\nWould fetch {len(notes)} notes and {len(articles)} articles")
            return
        
        # Process events and generate markdown
        if notes:
            self._process_notes(notes)
        
        if articles:
            self._process_articles(articles)
        
        # Save state
        self._save_state()
        
        # Print stats
        self._print_stats()


async def main():
    parser = argparse.ArgumentParser(description="Fetch Nostr events for Hugo website")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be fetched without writing files")
    parser.add_argument('--force-resync', action='store_true', help="Clear state and refetch everything")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging")
    parser.add_argument('--config', default='scripts/nostr_config.json', help="Path to config file")
    
    args = parser.parse_args()
    
    # Clear state if force resync
    if args.force_resync:
        state_file = Path("scripts/nostr_sync_state.json")
        if state_file.exists():
            state_file.unlink()
            print("State file cleared - will perform full resync")
    
    # Create fetcher and sync
    fetcher = NostrEventFetcher(config_path=args.config, verbose=args.verbose)
    await fetcher.sync(dry_run=args.dry_run)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
