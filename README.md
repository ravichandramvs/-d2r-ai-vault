# D2R Vault

AI-powered item vault, holy grail tracker, and smart loot filter for **Diablo II: Resurrected** — built for the [Reign of the Warlock (RotW)](https://www.nexusmods.com/diablo2resurrected/mods/381) mod but adaptable to vanilla D2R.

## What it does

- **Item Parser** (`d2r_item_parser.py`) — Binary parser for D2R item DNA (hex). Handles RotW-specific quirks: 13-bit unique/set IDs, zero-bit marker stats, stat chaining, Huffman-encoded item codes. Maps DNA row indices to `*ID` values using the mod's data tables.
- **Stash Manager** (`stash_manager.py`) — Scans shared stash (`.d2i`) and character (`.d2s`) saves, backs up every item's raw DNA to a JSON vault. Can wipe specific stash tabs. Supports item injection with grid placement (experimental).
- **Holy Grail Tracker** (`loot_filter.py status`) — Tracks found/missing uniques and sets using two sources: the in-game chronicle (`C0EDEAC0` binary section) and the vault. Shows progress by tier.
- **Smart Loot Filter** (`loot_filter.py apply`) — Generates D2R `.fltr` files based on vault contents. Hides found items, shows unfound uniques/sets, valuable elite bases, rare crafting gear, charms, and potions. Items in chronicle but not in vault still show so you can re-collect them.
- **Build Ranker** (`build_ranker.py`) — Scores vault items for specific builds. Supports Echo Warlock (FCR/+skills/DS) and Act 2 Might Merc (LL/ED/IAS/CB) profiles.

## Setup

### Requirements

- Python 3.8+
- D2R installed with RotW mod (or vanilla D2R with adjustments)
- RotW mod data tables are used automatically from `D2RMM.mpq/data/global/excel/`

### Configuration

Path auto-detection works out of the box for standard installs. Override with `config_local.py` if needed:

```python
import os
MOD_SAVE_DIR = r'C:\Users\YOU\Saved Games\Diablo II Resurrected\mods\YourMod'
STASH_FILE = os.path.join(MOD_SAVE_DIR, 'ModernSharedStashSoftCoreV2.d2i')
CHAR_FILE = os.path.join(MOD_SAVE_DIR, 'YourCharacter.d2s')
```

## Usage

### Typical workflow after a play session

```bash
python stash_manager.py scan      # Back up stash items to vault
python stash_manager.py wipe      # Clear shared stash tabs 1-5
python loot_filter.py apply       # Regenerate + apply filter
```

### Stash Manager

```bash
python stash_manager.py scan      # Scan stash + character, add new items to vault
python stash_manager.py status    # Show vault stats
python stash_manager.py wipe      # Wipe shared stash tabs 1-5 (keeps tabs 6-7)
python stash_manager.py wipe 1,3  # Wipe only tabs 1 and 3
python stash_manager.py inject 42 186 204  # Inject vault items into stash (experimental)
```

### Loot Filter

```bash
python loot_filter.py status      # Show holy grail progress (chronicle vs vault)
python loot_filter.py apply       # Generate filter from vault + apply to game
python loot_filter.py generate    # Generate filter without applying
python loot_filter.py reset       # Reset to default starter filter
```

### Item Analysis

```bash
python vault_scanner.py           # Full vault scan with quality breakdown
python build_ranker.py 5          # Top 5 items per slot for Echo Warlock
python build_ranker.py 5 merc     # Top 5 items per slot for Act 2 merc
python d2r_item_parser.py         # Test parser on first 30 vault items
```

## How the Loot Filter Works

### D2R filter engine rules

1. **SHOW always beats HIDE** — if any SHOW rule matches, item is visible
2. **Unmatched items are visible by default** — only explicitly hidden items disappear
3. **Fields within a rule are AND'd** — item must match ALL fields
4. **Values within a field are OR'd** — `["unique", "set"]` matches either
5. **`equipmentItemCode`** for ALL gear (including rings, amulets, jewels, charms) — `itemCode` is only for consumables (potions, scrolls)

### Filter strategy

The generated filter uses targeted HIDE + selective SHOW:

**HIDE rules:**
- Found uniques/sets (by base code — only hidden when ALL uniques/sets for that code are in vault)
- White/magic/rare items (broad catch-all)
- Inferior gear, gold, gems, runes, ammo, scrolls, keys, weak potions

**SHOW rules (override HIDE):**
- Elite runeword bases (42 specific codes: Archon Plate, Monarch, Phase Blade, Thresher, etc.)
- Elite socketed/ethereal items (same codes)
- Rare gloves, boots, circlets (all tiers)
- Rare rings, amulets, jewels
- Magic/rare jewels
- Magic charms (small/large/grand)
- Good potions (HP5, MP5, full rejuv)
- Quest items

### Vault-based vs chronicle-based filtering

The filter uses **vault contents** (not the in-game chronicle) to determine found/unfound. This means:
- Items you found and sold/dropped (in chronicle but not vault) **still show** in the filter
- Only items actually backed up to the vault are considered "found"
- Re-running `apply` after `scan` updates the filter with your latest finds

## RotW-Specific Notes

The parser handles several RotW differences from vanilla D2R:

- **13-bit unique/set IDs** (vanilla uses 12 bits)
- **Row index to `*ID` mapping** — DNA stores row indices (including "Expansion" placeholder rows at index 129 for uniques, 62 for sets). The parser maps these to `*ID` values for correct chronicle matching.
- **Zero-bit marker stat IDs** in ItemStatCost (read 9-bit ID only, no value bits)
- **Stat chaining** for fire/light/cold/poison damage pairs
- **Chronicle** (`C0EDEAC0`) — two sections: set IDs (first `set_count` entries), then unique IDs. Each entry is 10 bytes with item ID at bytes 6-7 (16-bit LE).
- **Modern Shared Stash** (`.d2i`) — 7 tabs with `55AA55AA` signatures, 64-byte headers, tab size at offset 16-19 (4 bytes LE).
- **`disableChronicle`** column — items like Warlord's Glory set (IDs 127-131) are excluded from grail tracking.
- **Warlock class** (class index 7, skill IDs 373-402)

## File Structure

```
d2r_item_parser.py      Core binary item parser (Huffman, stats, quality)
stash_manager.py        Scan/wipe/inject items to/from vault
loot_filter.py          Holy grail tracker + smart loot filter generator
vault_scanner.py        Full vault analysis and reporting
build_ranker.py         Item ranking for specific builds (warlock, merc)
item_names.py           Lookup tables for item/unique/set names and slots
config.py               Auto-detecting configuration (paths, signatures)
config_local.py         Your local path overrides (gitignored)
PreciseModMap_v3.json   Stat ID -> name/bits/offset mapping
D2R_AI_Bank.json        Current vault data (gitignored)
D2R_AI_Bank_Legacy.json Legacy GoMule/backup vault (gitignored)
```

## Known Limitations

- **Stat parser accuracy** — `PreciseModMap_v3.json` bit widths may not match RotW's `ItemStatCost.txt` for all stats. This affects build ranking scores but not item identification or grail tracking.
- **Character stash clearing** — Cannot safely wipe character stash from `.d2s` files (requires recalculating checksums and item counts in the file header). Shared stash (`.d2i`) wipe works fine.
- **Item injection** — Experimental. May corrupt the game save. Always creates backups before modifying files.
- **Filter granularity** — D2R filters work by base item code, not specific unique/set ID. If two uniques share a base (e.g., two unique amulets), both show until all uniques for that base are found.

## Credits

Built with [Claude Code](https://claude.ai/claude-code). Item binary format research via [GoMule D2R](https://github.com/pairofdocs/gomern) and [d2s format](https://github.com/dschu012/d2s).
