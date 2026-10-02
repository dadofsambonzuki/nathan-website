#!/usr/bin/env python3
"""
Resolve the Nostr mentions in synced content to profile names.

Notes and articles are synced from Nostr (see fetch_nostr_events.py) and their
bodies are full of raw `nostr:npub1...` / `nostr:nprofile1...` mentions. This
script looks up the kind 0 metadata for every pubkey mentioned in those files
and writes `data/nostr_profiles.json`, which the Hugo templates read as
`site.Data.nostr_profiles` to label the mention links with a real name.

The cache is keyed by the identifier exactly as it appears in the content (both
the npub and the nprofile form of the same profile get their own entry), so it
is only ever appended to and only new mentions cost a relay round-trip.

Any failure is non-fatal: the existing cache is left alone, the reason is
printed, and the script still exits 0 so a deploy is never blocked. Without a
cache the templates fall back to a shortened identifier.
"""

import argparse
import json
import re
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

try:
    from nostr_sdk import Client, Filter, Kind, Nip19, PublicKey, RelayUrl
except ImportError:
    print("resolve_nostr_mentions: nostr-sdk not installed, skipping")
    sys.exit(0)


# bech32's charset excludes 1, b, i and o, so an identifier can never contain a
# second "1" after its prefix separator. All five kinds are collected: the
# profiles are looked up, the events and addresses are only canonicalised.
IDENTIFIER_RE = re.compile(
    r"(?<![0-9a-z])((?:npub|nprofile|note|nevent|naddr)1[023456789acdefghjklmnpqrstuvwxyz]{20,})"
)
CONTENT_DIRS = ("content/notes", "content/articles")
CACHE_PATH = Path("data/nostr_profiles.json")
CONFIG_PATH = Path("scripts/nostr_config.json")
EXTRA_RELAYS = (
    "wss://purplepag.es",
    "wss://relay.nostr.band",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.snort.social",
    "wss://relay.primal.net",
)


def log(message: str, verbose: bool):
    if verbose:
        print(f"  {message}")


def collect_identifiers(content_dirs: Iterable[str]) -> Dict[str, Set[str]]:
    """Return every bech32 identifier in the synced content, keyed by file."""
    found: Dict[str, Set[str]] = {}
    for directory in content_dirs:
        for path in sorted(Path(directory).glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            identifiers = set(IDENTIFIER_RE.findall(text))
            if identifiers:
                found[str(path)] = identifiers
    return found


def describe(identifier: str) -> Dict[str, Optional[str]]:
    """Decode an identifier into its pubkey (profiles only) and its canonical
    bech32 form.

    A mention is often written as an nprofile or an nevent carrying relay
    hints, which nobody wants to read or to see in a URL. The canonical form
    is the plain npub of the key, or the note1 of the event id, and that is
    what the templates label and link with when no profile name is known.
    """
    decoded = Nip19.from_bech32(identifier).as_enum()
    if decoded.is_pubkey():
        key = decoded.npub
        return {"pubkey": key.to_hex(), "short": key.to_bech32()}
    if decoded.is_profile():
        key = decoded.nprofile.public_key()
        return {"pubkey": key.to_hex(), "short": key.to_bech32()}
    if decoded.is_note():
        # The NOTE variant exposes event_id directly; EVENT wraps it.
        return {"pubkey": None, "short": decoded.event_id.to_bech32()}
    if decoded.is_event():
        return {"pubkey": None, "short": decoded.event.event_id().to_bech32()}
    if decoded.is_addr():
        return {"pubkey": None, "short": decoded.coordinate.to_bech32()}
    raise ValueError("unsupported identifier")


def load_cache() -> Dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open(encoding="utf-8") as handle:
            cache = json.load(handle)
        if isinstance(cache, dict):
            return cache
    except (json.JSONDecodeError, OSError) as error:
        print(f"resolve_nostr_mentions: ignoring unreadable cache ({error})")
    return {}


def load_relays() -> List[str]:
    relays = list(EXTRA_RELAYS)
    try:
        with CONFIG_PATH.open(encoding="utf-8") as handle:
            config = json.load(handle)
        relays = list(config.get("fallback_relays", [])) + relays
    except (json.JSONDecodeError, OSError):
        pass

    unique: List[str] = []
    for relay in relays:
        if relay not in unique:
            unique.append(relay)
    return unique


async def fetch_profiles(pubkeys: List[str], relays: List[str], verbose: bool, timeout: int) -> Dict[str, dict]:
    """Fetch the newest kind 0 metadata for each pubkey, keyed by hex pubkey."""
    client = Client()
    for relay in relays:
        try:
            await client.add_relay(RelayUrl.parse(relay))
        except Exception as error:  # noqa: BLE001 - a bad relay must not stop the rest
            log(f"skipping relay {relay}: {error}", verbose)

    await client.connect()

    profiles: Dict[str, dict] = {}
    try:
        filter_by_author = Filter().authors([PublicKey.parse(pk) for pk in pubkeys]).kind(Kind(0))
        events = await fetch_events(client, filter_by_author, timeout)
        for event in events:
            # 0.45 calls this author(), earlier releases pubkey().
            author_key = event.author() if hasattr(event, "author") else event.pubkey()
            author = author_key.to_hex()
            try:
                metadata = json.loads(event.content())
            except json.JSONDecodeError:
                continue
            current = profiles.get(author)
            if current is None or event.created_at().as_secs() > current["created_at"]:
                profiles[author] = {"created_at": event.created_at().as_secs(), "metadata": metadata}
    finally:
        try:
            await client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    return profiles


async def fetch_events(client: "Client", author_filter: "Filter", timeout: int) -> List:
    """Fetch events across the relays, tolerating the two client APIs in use.

    nostr-sdk 0.45 wants a ReqTarget; earlier releases take the filter (or a
    list of them) directly, which is what fetch_nostr_events.py still calls.
    """
    duration = timedelta(seconds=timeout)

    try:
        from nostr_sdk import ReqTarget

        events = await client.fetch_events(ReqTarget.auto([author_filter]), timeout=duration)
    except (ImportError, TypeError):
        events = await client.fetch_events(author_filter, timeout=duration)

    return events if isinstance(events, list) else events.to_vec()


def cache_entry(description: Dict[str, Optional[str]], profiles: Dict[str, dict]) -> dict:
    """One cache entry: the canonical identifier, the pubkey when it is a
    profile, and the kind 0 fields when the relays had them."""
    entry: dict = {}
    if description.get("short"):
        entry["short"] = description["short"]

    pubkey = description.get("pubkey")
    if pubkey:
        entry["pubkey"] = pubkey
        entry["checked"] = int(time.time())
        profile = profiles.get(pubkey)
        if profile:
            metadata = profile["metadata"]
            for field in ("name", "display_name", "nip05", "picture"):
                value = metadata.get(field)
                if isinstance(value, str) and value.strip():
                    entry[field] = value.strip()
    return entry


def needs_lookup(identifier: str, cache: Dict[str, dict], recheck_hours: int) -> bool:
    """True when an identifier is new, or is named-less and stale.

    Profiles without kind 0 metadata on the relays we tried are kept and
    retried later rather than refetched on every build; events and addresses
    have nothing to look up, so they only want a canonical form.
    """
    entry = cache.get(identifier)
    if entry is None:
        return True
    if entry.get("invalid"):
        return False
    if not entry.get("short"):
        # Written before the canonical form was recorded, or cached as a
        # nameless profile by an older run: rebuild the entry once.
        return True
    if not entry.get("pubkey"):
        # Events and addresses have no name to look up, only the short form.
        return False
    if entry.get("name") or entry.get("display_name"):
        return False
    checked = entry.get("checked")
    if not isinstance(checked, int):
        return True
    return (time.time() - checked) > recheck_hours * 3600


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Nostr mentions to profile names")
    parser.add_argument("--verbose", action="store_true", help="print progress")
    parser.add_argument("--timeout", type=int, default=8, help="relay timeout in seconds")
    parser.add_argument("--recheck-hours", type=int, default=24, help="retry nameless profiles after this long")
    parser.add_argument("--dry-run", action="store_true", help="report without writing the cache")
    args = parser.parse_args()

    identifiers = sorted({identifier for ids in collect_identifiers(CONTENT_DIRS).values() for identifier in ids})
    if not identifiers:
        print("resolve_nostr_mentions: no npub/nprofile mentions found")
        return 0

    cache = load_cache()
    missing = [identifier for identifier in identifiers if needs_lookup(identifier, cache, args.recheck_hours)]
    log(f"{len(identifiers)} identifiers in content, looking up {len(missing)}", args.verbose)

    resolved: Dict[str, dict] = {}
    if missing:
        pubkeys: Dict[str, List[str]] = {}
        descriptions: Dict[str, Dict[str, Optional[str]]] = {}
        for identifier in missing:
            try:
                description = describe(identifier)
            except Exception as error:  # noqa: BLE001 - a malformed mention must not fail the run
                # Mentions are sometimes pasted truncated, so they cannot be
                # decoded or linked; record that so the templates leave them be.
                resolved[identifier] = {"invalid": True}
                log(f"could not decode {identifier[:20]}…: {error}", args.verbose)
                continue
            descriptions[identifier] = description
            pubkey = description.get("pubkey")
            if pubkey:
                pubkeys.setdefault(pubkey, []).append(identifier)

        profiles: Dict[str, dict] = {}
        if pubkeys:
            try:
                import asyncio

                profiles = asyncio.run(fetch_profiles(list(pubkeys), load_relays(), args.verbose, args.timeout))
            except Exception as error:  # noqa: BLE001 - offline build keeps the old cache
                print(f"resolve_nostr_mentions: relay lookup failed ({error}); keeping cached names")

        for identifier, description in descriptions.items():
            resolved[identifier] = cache_entry(description, profiles)

    named = sum(1 for entry in list(cache.values()) + list(resolved.values()) if entry.get("name") or entry.get("display_name"))
    log(f"{named} of {len(identifiers)} mentions have a name", args.verbose)

    if args.dry_run:
        print(json.dumps({**cache, **resolved}, indent=2, sort_keys=True))
        return 0

    merged = {**cache, **resolved}
    if merged == cache:
        print(f"resolve_nostr_mentions: cache already covers all {len(cache)} mentions")
        return 0

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"resolve_nostr_mentions: wrote {len(merged)} profiles to {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
