# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

**Files:**
- Snake_case with descriptive names: `main.py`, `collector_ui.py`
- No underscores for UI module: `collector_ui.py` (underscore separates module purpose)

**Functions:**
- snake_case: `timestamp_ms()`, `start_recording()`, `_build_ui()`
- Private methods prefixed with underscore: `_build_ui()`, `_refresh_ui()`

**Variables:**
- snake_case for locals and instance variables: `com_port`, `baud_rate`, `latest_eeg`
- UPPER_SNAKE_CASE for constants: `COM_PORT`, `BAUD_RATE`, `EEG_FIELDS`, `EMOTIONS`, `EVENTS`
- No global variables beyond constants

**Types:**
- PascalCase for classes: `CollectorApp`
- Type hints used consistently in collector_ui.py, less in main.py
- Use `Optional[T]` for nullable types (e.g., `Optional[Serial]`)
- Use lowercase generic types (`list`, `dict`) from Python 3.9+

## Code Style

**Formatting:**
- Indentation: 4 spaces (consistent across files)
- Line length: moderate (no strict limit observed, but lines generally under 100 characters)
- String quotes: double quotes for multi-word strings, single quotes for short literals (mixed usage)
- Trailing commas: used in multi-line lists and dicts (see `EEG_FIELDS` definition)

**Linting:**
- Ruff is present (`.ruff_cache` directory) but no configuration file found
- Likely using default ruff rules

## Import Organization

**Order:**
1. Standard library imports (grouped together)
2. Third-party imports (separated by blank line)
3. Local imports (if any)

**Example from `collector_ui.py`:**
```python
import csv
import json
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Optional

import serial
```

**Path Aliases:**
- No path aliases detected

## Error Handling

**Patterns:**
- Specific exception catching: `SerialException`, `OSError`, `ValueError`
- Graceful degradation with `continue` or early returns
- Logging errors via print statements or UI markers
- No bare `except:` clauses observed

**Example:**
```python
try:
    self.ser = Serial(com_port, baud_rate, timeout=1)
except SerialException as exc:
    with self.lock:
        self.serial_connected = False
    self._queue_marker(f"Serial reconnect failed: {exc}")
```

## Logging

**Framework:** No logging module used; print statements for console output, custom marker system for UI logging.

**Patterns:**
- Print statements with timestamps: `print(f"[{time.strftime('%H:%M:%S')}] Signal Warning: ...")`
- UI marker system via `_append_marker_list()` and `_queue_marker()`
- Errors logged to UI queue, not to files

## Comments

**When to Comment:**
- Section headers: `# Setup`, `# Code 0x02 = Poor Signal`
- Inline explanations for complex logic (checksum calculation, packet parsing)
- No docstrings observed

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Type hints serve as documentation

## Function Design

**Size:** Functions are moderate length (up to ~50 lines). Complex parsing logic kept in loops.

**Parameters:**
- Clear parameter names with type hints
- Use of `self` as first parameter for methods
- Default parameters used (e.g., `threshold_ms: int = 180`)

**Return Values:**
- Functions return `None` implicitly or explicitly
- Some functions return computed values (e.g., `timestamp_ms() -> int`)

## Module Design

**Exports:**
- No `__all__` definitions
- Classes and functions are public by default
- Private methods prefixed with underscore

**Barrel Files:**
- No barrel files (only two modules)

## Threading Patterns

**Locks:** Use `threading.Lock` for shared state protection
**Queues:** `queue.Queue` for UI thread communication
**Threads:** Daemon threads for background serial reading

## UI Patterns (tkinter)

**Structure:**
- Single main class `CollectorApp` encapsulating all UI logic
- UI built in `_build_ui()` method
- Key bindings in `_bind_keys()`
- Periodic UI refresh via `root.after(200, self._refresh_ui)`

**State Management:**
- Shared state protected by locks
- UI updates via queue from background threads

---

*Convention analysis: 2026-03-30*
