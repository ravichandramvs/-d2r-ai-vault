"""
Configuration for D2R Vault tools.

Auto-detects paths where possible. Override by creating config_local.py
with any variables you want to change (it's gitignored).
"""
import os, sys, glob

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- Auto-detect D2R save directory ---
_SAVE_BASE = os.path.expanduser(r'~\Saved Games\Diablo II Resurrected')
_MOD_DIRS = glob.glob(os.path.join(_SAVE_BASE, 'mods', '*'))

# Default: first mod dir found, or base D2R saves
if _MOD_DIRS:
    MOD_SAVE_DIR = _MOD_DIRS[0]
else:
    MOD_SAVE_DIR = _SAVE_BASE

# --- Stash file (auto-detect Modern or Classic shared stash) ---
_STASH_CANDIDATES = glob.glob(os.path.join(MOD_SAVE_DIR, '*SharedStash*.d2i'))
STASH_FILE = _STASH_CANDIDATES[0] if _STASH_CANDIDATES else os.path.join(MOD_SAVE_DIR, 'SharedStashSoftCoreV2.d2i')

# --- Character file (auto-detect first .d2s) ---
_CHAR_CANDIDATES = glob.glob(os.path.join(MOD_SAVE_DIR, '*.d2s'))
CHAR_FILE = _CHAR_CANDIDATES[0] if _CHAR_CANDIDATES else ''

# --- Vault data (lives in this repo) ---
VAULT_FILE = os.path.join(_HERE, 'D2R_AI_Bank.json')
STAT_MAP_FILE = os.path.join(_HERE, 'PreciseModMap_v3.json')

# --- D2 data tables ---
# Prefer RotW mod data (actual game tables) over GoMule vanilla data.
# RotW data lives inside D2RMM.mpq/data/global/excel/ in the game install.
_D2R_INSTALL = r'C:\Program Files (x86)\Diablo II Resurrected'
_ROTW_DATA = os.path.join(_D2R_INSTALL, 'mods', 'D2RMM', 'D2RMM.mpq', 'data', 'global', 'excel')
_DATA_SEARCH = [
    _ROTW_DATA,
    os.path.expanduser(r'~\Downloads\gomule-d2r-*\*\gomule\d2111'),
    os.path.expanduser(r'~\gomule\d2111'),
    os.path.join(_HERE, 'data'),
]
D2_DATA_DIR = ''
for path in _DATA_SEARCH:
    candidates = glob.glob(path) if '*' in path else ([path] if os.path.isdir(path) else [])
    if candidates:
        D2_DATA_DIR = candidates[0]
        break

ARMOR_TXT = os.path.join(D2_DATA_DIR, 'armor.txt')
WEAPONS_TXT = os.path.join(D2_DATA_DIR, 'weapons.txt')
# RotW uses lowercase filenames; GoMule uses mixed case
_misc_lower = os.path.join(D2_DATA_DIR, 'misc.txt')
_misc_upper = os.path.join(D2_DATA_DIR, 'Misc.txt')
MISC_TXT = _misc_lower if os.path.exists(_misc_lower) else _misc_upper
_unique_lower = os.path.join(D2_DATA_DIR, 'uniqueitems.txt')
_unique_upper = os.path.join(D2_DATA_DIR, 'UniqueItems.txt')
UNIQUE_TXT = _unique_lower if os.path.exists(_unique_lower) else _unique_upper
_set_lower = os.path.join(D2_DATA_DIR, 'setitems.txt')
_set_upper = os.path.join(D2_DATA_DIR, 'SetItems.txt')
SET_TXT = _set_lower if os.path.exists(_set_lower) else _set_upper

# --- Binary signatures (D2R format constants) ---
TAB_SIG = b'\x55\xAA\x55\xAA'
CHRONICLE_SIG = b'\xC0\xED\xEA\xC0'
ITEM_START_RE = b'\x10\x00[\x80\xA0\xC0]\x00\x05'

# --- Local overrides (gitignored) ---
_LOCAL = os.path.join(_HERE, 'config_local.py')
if os.path.exists(_LOCAL):
    exec(open(_LOCAL).read())
