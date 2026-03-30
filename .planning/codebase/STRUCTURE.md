# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
mindtune/
├── .gitignore           # Git ignore rules
├── .python-version      # Python version specification (3.11)
├── .ruff_cache/         # Ruff linter cache (generated)
├── .venv/               # Python virtual environment (managed by uv)
├── __pycache__/         # Python bytecode cache (generated)
├── sessions/            # Output directory for session data (git-ignored)
│   ├── {session_id}/    # Individual session directories
│   │   ├── eeg_rows.csv
│   │   ├── markers.csv
│   │   └── session_meta.json
│   └── sessions/        # Nested sessions directory (appears to be duplication)
├── collector_ui.py      # GUI application entry point (866 lines)
├── main.py              # Headless data logger entry point (127 lines)
├── pyproject.toml       # Project configuration and dependencies
├── uv.lock              # uv package manager lock file
├── README.md            # Project documentation
├── all_sessions_eeg_with_markers.csv  # Aggregated session data (generated)
└── mindtune_full_eeg_data.csv         # Raw EEG output from main.py (generated)
```

## Directory Purposes

**Root Directory:**
- Purpose: Project root containing all source code, configuration, and generated data
- Contains: Python scripts, configuration files, aggregated data files
- Key files: `main.py`, `collector_ui.py`, `pyproject.toml`

**sessions/:**
- Purpose: Output directory for annotated data collection sessions
- Contains: Session-specific directories with EEG data, markers, and metadata
- Key files: `eeg_rows.csv`, `markers.csv`, `session_meta.json`
- Note: Listed in `.gitignore` - session data is not version controlled

**.venv/:**
- Purpose: Python virtual environment managed by uv package manager
- Contains: Installed dependencies (pypdf, pyserial)
- Generated: Yes (by `uv sync`)
- Committed: No (listed in `.gitignore`)

**.ruff_cache/:**
- Purpose: Cache for Ruff Python linter
- Contains: Cached analysis results
- Generated: Yes (by Ruff)
- Committed: No (but not explicitly git-ignored)

## Key File Locations

**Entry Points:**
- `main.py`: Headless EEG data logger - serial connection to CSV logging
- `collector_ui.py`: GUI application with annotation capabilities

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, Python version requirement
- `.python-version`: Python 3.11 specification for version managers

**Core Logic:**
- `main.py` (lines 18-120): Serial communication and raw data parsing
- `collector_ui.py` (lines 708-851): Enhanced serial reader with threading
- `collector_ui.py` (lines 525-617): Session file management
- `collector_ui.py` (lines 480-523): Event and emotion tracking

**Testing:**
- No test files detected - codebase lacks automated testing

**Documentation:**
- `README.md`: Setup instructions and basic usage

## Naming Conventions

**Files:**
- Snake case for Python files: `collector_ui.py`, `main.py`
- Descriptive names indicating purpose: `collector_ui.py` for GUI, `main.py` for simple logger
- CSV files follow data naming: `eeg_rows.csv`, `markers.csv`, `session_meta.json`

**Directories:**
- Session directories use numeric or alphanumeric IDs: `002/`, `11_aman/`, `bikash/`
- Output directories use descriptive names: `sessions/`

**Variables:**
- Snake case throughout: `signal_quality`, `low_beta`, `session_id`
- Constants in UPPER_CASE: `EEG_FIELDS`, `EMOTIONS`, `EVENTS`
- Hungarian-like prefixes for events: `ev_speaking`, `ev_question`

## Where to Add New Code

**New Feature - Data Analysis:**
- Primary code: New file `analysis.py` in root directory
- Could also be added as functions in existing files if simple

**New Feature - Additional Entry Points:**
- Create new file with descriptive name (e.g., `export_tool.py`)
- Follow existing pattern of self-contained scripts

**New Configuration:**
- Add to `pyproject.toml` for dependencies
- Create separate `.ini` or `.json` config files if needed

**New Output Formats:**
- Extend existing CSV writing functions in `collector_ui.py` (lines 697-705)
- Or create new writer classes if substantial logic needed

**Utilities:**
- Shared helpers: Could create `utils.py` in root directory
- Currently no shared utility module exists

## Special Directories

**sessions/:**
- Purpose: Generated output from data collection sessions
- Generated: Yes (by `collector_ui.py`)
- Committed: No (git-ignored)

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes (by `uv sync`)
- Committed: No (git-ignored)

**Generated Data Files:**
- `mindtune_full_eeg_data.csv`: Output from `main.py` raw logger
- `all_sessions_eeg_with_markers.csv`: Likely aggregated session data (purpose unclear)
- Generated: Yes
- Committed: Yes (not git-ignored, currently tracked)

---

*Structure analysis: 2026-03-30*