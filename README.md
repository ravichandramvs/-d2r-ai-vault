# D2R Vault

AI-powered item vault and loot filter manager for **Diablo II: Resurrected** — built for the [Reign of the Warlock (RotW)](https://www.nexusmods.com/diablo2resurrected/mods/381) mod but adaptable to vanilla D2R.

## What it does

- **Item Parser** — Binary parser for D2R item DNA (hex). Handles RotW-specific quirks: 13-bit unique/set IDs, zero-bit marker stats, stat chaining for damage pairs, Huffman-encoded item codes.
- **Vault Manager** — Scans your shared stash and character saves, stores every item's raw DNA in a JSON vault. Supports injecting items back into the stash with correct grid placement.
- **Holy Grail Tracker** — Cross-references your vault against UniqueItems.txt and SetItems.txt to show found/missing items by tier.
- **Smart Loot Filter** — Generates D2R `.fltr` files based on your grail progress. Hides found uniques/sets, shows only unfound ones. Uses the correct HIDE ALL + SHOW whitelist pattern.
- **Build Ranker** — Scores vault items for a specific build (default: Echo Warlock). Ranks by slot with configurable stat weights.

## Setup

### Requirements

- Python 3.8+
- D2R installed with RotW mod (or vanilla D2R with minor adjustments)
- GoMule D2R data tables (armor.txt, weapons.txt, etc.) — download from [GoMule D2R releases](https://github.com/pairofdocs/gomern/releases)

### Configuration

The tool auto-detects paths. If auto-detection fails, create `config_local.py`:

```python
import os

MOD_SAVE_DIR = r'C:\Users\YOU\Saved Games\Diablo II Resurrected\mods\YourMod'
STASH_FILE = os.path.join(MOD_SAVE_DIR, 'SharedStashSoftCoreV2.d2i')
CHAR_FILE = os.path.join(MOD_SAVE_DIR, 'YourCharacter.d2s')
D2_DATA_DIR = r'C:\path\to\gomule\d2111'

# These are derived from D2_DATA_DIR:
ARMOR_TXT = os.path.join(D2_DATA_DIR, 'armor.txt')
WEAPONS_TXT = os.path.join(D2_DATA_DIR, 'weapons.txt')
MISC_TXT = os.path.join(D2_DATA_DIR, 'Misc.txt')
UNIQUE_TXT = os.path.join(D2_DATA_DIR, 'UniqueItems.txt')
SET_TXT = os.path.join(D2_DATA_DIR, 'SetItems.txt')
```

## Usage

### Vault Management

```bash
# Scan stash + character for new items, update chronicle
python stash_manager.py scan

# Show vault stats
python stash_manager.py status

# Wipe shared stash tabs 1-5 (preserves materials/chronicle tabs)
python stash_manager.py wipe

# Inject specific vault items into stash by index
python stash_manager.py inject 202 186 204
```

### Loot Filter

```bash
# Show holy grail progress
python loot_filter.py status

# Generate optimized filter from vault grail data
python loot_filter.py generate

# Apply filter to game (creates backup first)
python loot_filter.py apply

# Reset to default starter filter
python loot_filter.py reset
```

### Item Analysis

```bash
# Full vault scan with quality distribution
python vault_scanner.py

# Rank items for Echo Warlock build (top N per slot)
python build_ranker.py 3

# Test parser on first 30 items
python d2r_item_parser.py
```

## How the Loot Filter Works

D2R's filter engine has specific rules:

1. **SHOW always beats HIDE** — if any SHOW rule matches an item, it's visible regardless of HIDE rules
2. **Unmatched items are visible by default** — you need a catch-all HIDE rule
3. **Fields within a rule are AND'd** — item must match ALL specified fields
4. **Values within a field are OR'd** — `["unique", "set"]` matches either

The correct pattern is:

```
HIDE ALL (catch-all) → everything hidden
SHOW rules → whitelist specific items through
```

This tool generates filters that:
- **HIDE ALL** as the base layer (including gold via `goldFilterValue`)
- **SHOW unfound uniques/sets** only for base codes with missing grail items
- **SHOW socketed/ethereal** items (runeword bases)
- **SHOW rare** rings, amulets, circlets, boots, jewels
- **SHOW magic charms**
- **SHOW** HP5, MP5, rejuvenation potions

As your grail progresses, re-run `generate` + `apply` to automatically shrink what's visible.

## RotW-Specific Notes

The item parser handles several RotW differences from vanilla D2R:

- **13-bit unique/set IDs** (vanilla uses 12 bits)
- **Zero-bit marker stat IDs** in ItemStatCost (read 9-bit ID only, no value bits)
- **Stat chaining** for fire/light/cold/poison damage pairs
- **Chronicle** system (`C0EDEAC0` signature) for stash discovery logging
- **Modern Shared Stash** format with `55AA55AA` tab signatures
- **Warlock class** (class index 7) — only `item_allskills` benefits Warlock from item stats

## File Structure

```
d2r_item_parser.py   — Core binary item parser (Huffman, stats, quality)
stash_manager.py     — Scan/wipe/inject items to/from vault
loot_filter.py       — Holy grail tracker + smart loot filter generator
vault_scanner.py     — Full vault analysis and reporting
build_ranker.py      — Item ranking for specific builds
item_names.py        — Lookup tables for item/unique/set names
config.py            — Auto-detecting configuration
config_local.py      — Your local path overrides (gitignored)
PreciseModMap_v3.json — Stat ID → name/bits/offset mapping
D2R_AI_Bank.json     — Your vault data (gitignored)
```

## Credits

Built with [Claude Code](https://claude.ai/claude-code). Item binary format research via [GoMule D2R](https://github.com/pairofdocs/gomern) and [d2s format](https://github.com/dschu012/d2s).
