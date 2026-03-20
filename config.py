"""
Configuration for D2R Vault tools.
Edit these paths to match your setup.
"""
import os

# --- Save file paths ---
MOD_SAVE_DIR = os.path.expanduser(r'~\Saved Games\Diablo II Resurrected\mods\D2RMM')
STASH_FILE = os.path.join(MOD_SAVE_DIR, 'ModernSharedStashSoftCoreV2.d2i')
CHAR_FILE = os.path.join(MOD_SAVE_DIR, 'lazylock.d2s')

# --- Vault data ---
VAULT_FILE = os.path.join(os.path.dirname(__file__), 'D2R_AI_Bank.json')
STAT_MAP_FILE = os.path.join(os.path.dirname(__file__), 'PreciseModMap_v3.json')

# --- D2 data tables (from GoMule or extracted) ---
D2_DATA_DIR = os.path.expanduser(r'~\Downloads\gomule-d2r-0.24\gomule-d2r-0.24\gomule\d2111')
ARMOR_TXT = os.path.join(D2_DATA_DIR, 'armor.txt')
WEAPONS_TXT = os.path.join(D2_DATA_DIR, 'weapons.txt')
MISC_TXT = os.path.join(D2_DATA_DIR, 'Misc.txt')
UNIQUE_TXT = os.path.join(D2_DATA_DIR, 'UniqueItems.txt')
SET_TXT = os.path.join(D2_DATA_DIR, 'SetItems.txt')

# --- Binary signatures ---
TAB_SIG = b'\x55\xAA\x55\xAA'
CHRONICLE_SIG = b'\xC0\xED\xEA\xC0'
ITEM_START_RE = b'\x10\x00[\x80\xA0\xC0]\x00\x05'
