# Codebase Concerns

**Analysis Date:** 2026-03-30

## Tech Debt

**Unused dependency (`pypdf`):**
- Issue: `pypdf` is listed in `pyproject.toml` dependencies but never imported or used in any Python file.
- Files: `pyproject.toml`
- Impact: Increases installation size and dependency resolution time unnecessarily.
- Fix approach: Remove `pypdf` from dependencies if not needed for future functionality.

**Hardcoded configuration in `main.py`:**
- Issue: Serial port (`COM1`) and baud rate (`57600`) are hardcoded constants, unlike the configurable UI version.
- Files: `main.py` (lines 14‑15)
- Impact: Requires editing source code to change settings, error‑prone for non‑technical users.
- Fix approach: Accept command‑line arguments or environment variables, or deprecate `main.py` in favor of the UI.

**Inconsistent logging triggers:**
- Issue: EEG data rows are only written to CSV when the `meditation` value updates (line 88‑95 in `main.py`, line 850‑851 in `collector_ui.py`). Changes in other bands (delta, theta, alpha, beta, gamma) or in `attention` are not recorded unless accompanied by a meditation update.
- Files: `main.py`, `collector_ui.py`
- Impact: Loss of continuous data for other metrics; analysis may be skewed.
- Fix approach: Log rows on a fixed timer interval (e.g., every 1 s) or whenever any EEG field changes.

**Session directory path traversal risk:**
- Issue: `session_id` is used directly in `os.path.join(output_root, session_id)` without sanitization. A malicious session ID containing `..` or absolute paths could write files outside the intended directory.
- Files: `collector_ui.py` (line 535)
- Impact: Potential data leakage or overwriting of arbitrary files.
- Fix approach: Validate `session_id` to contain only safe characters (alphanumeric, hyphens, underscores) and reject path separators.

**Missing error‑handling for partial file opens:**
- Issue: If `_open_session_files` succeeds in opening the first CSV file but fails on the second, the first file handle is left open and never closed because `self.recording` remains `False`, preventing `stop_recording` from cleaning up.
- Files: `collector_ui.py` (lines 574‑582, 430, 473)
- Impact: Resource leak (file descriptor) and potential data loss.
- Fix approach: Use `try/except` around each open and close any already‑opened files on failure, or open both files before assigning to `self.*`.

## Known Bugs

**Nested `sessions/sessions/` directory:**
- Symptoms: Some session data is stored under `sessions/sessions/NNNN/` instead of `sessions/NNNN/`.
- Files: `sessions/sessions/` (multiple subdirectories)
- Trigger: Likely caused by setting `output_root` to `"sessions"` and `session_id` to something like `"sessions/0091"` (perhaps via a previous UI run that concatenated paths incorrectly).
- Workaround: Manually move the misplaced directories. Prevent future occurrences by validating that `session_id` does not contain path separators.

**CSV flush on every row:**
- Symptoms: High I/O latency and potential disk thrashing when recording at high rates.
- Files: `main.py` (line 94), `collector_ui.py` (lines 705, 645)
- Trigger: Every call to `_write_eeg_row` and `_write_marker` calls `file.flush()`.
- Workaround: None.
- Fix approach: Flush periodically (e.g., every 10 rows) or rely on the OS buffer.

**Possible unbound variable in `main.py` `finally` block:**
- Symptoms: LSP warning that `ser` may be unbound when accessing `ser.is_open`.
- Files: `main.py` (lines 126‑127)
- Trigger: If the `Serial` constructor raises an exception before `ser` is assigned, the `finally` block still references `ser` in the condition.
- Workaround: The check `'ser' in locals()` mitigates the actual runtime error, but the warning indicates a code smell.
- Fix approach: Move the `ser.is_open` check inside the `if 'ser' in locals():` block, or use a try‑except around the entire `finally` block.

## Security Considerations

**No input validation for serial data:**
- Risk: Malformed serial packets could cause index errors or infinite loops in parsing logic.
- Files: `main.py` (lines 40‑119), `collector_ui.py` (lines 739‑852)
- Current mitigation: Length checks and checksum validation; but many `continue` statements silently drop packets.
- Recommendations: Add a maximum retry limit for consecutive bad packets and log warnings to help diagnose hardware issues.

**Unrestricted file‑system paths:**
- Risk: As noted above, `session_id` and `output_root` are not sanitized, allowing path traversal.
- Files: `collector_ui.py` (lines 535‑536)
- Current mitigation: None.
- Recommendations: Implement allow‑list validation for user‑supplied path components.

**Large CSV file in repository root:**
- Risk: `all_sessions_eeg_with_markers.csv` (≈12k rows) is present in the workspace but not listed in `.gitignore`. If accidentally committed, it could bloat the repository and expose sensitive EEG data.
- Files: `all_sessions_eeg_with_markers.csv`, `.gitignore`
- Current mitigation: The file is currently untracked (`git status` shows `??`).
- Recommendations: Add `*.csv` or `all_sessions_eeg_with_markers.csv` to `.gitignore`, or move the file to a `data/` directory that is ignored.

## Performance Bottlenecks

**Frequent `flush()` calls:**
- Problem: Each EEG row and each marker row triggers a disk flush, turning a buffered write into a synchronous operation.
- Files: `main.py` (line 94), `collector_ui.py` (lines 705, 645)
- Cause: Defensive coding to ensure data is persisted immediately.
- Improvement path: Flush only after a batch of writes (e.g., every 100 ms) or on a timer, while still guaranteeing data loss is limited.

**Blocking serial reads without back‑pressure:**
- Problem: The serial reader loops continuously, parsing packets as fast as they arrive. If the UI thread cannot keep up with writing rows, the `ui_queue` may grow unbounded.
- Files: `collector_ui.py` (lines 708‑738)
- Cause: No limit on the UI queue size; only the marker list is capped at 100 entries.
- Improvement path: Add a maximum queue length and drop old UI updates when the queue is full.

## Fragile Areas

**Thread‑based serial reader with complex state sharing:**
- Files: `collector_ui.py` (lines 708‑852)
- Why fragile: Multiple locks (`self.lock`, `self.file_lock`), a `threading.Event`, and a `queue.Queue` interact. A deadlock or race condition could freeze the UI or corrupt data.
- Safe modification: Ensure locks are always acquired in the same order; avoid holding `self.lock` while performing I/O (e.g., writing to CSV).
- Test coverage: No automated tests exist for the threading logic.

**Silent packet‑parsing failures:**
- Files: `main.py` (lines 40‑119), `collector_ui.py` (lines 739‑852)
- Why fragile: Many `continue` statements drop malformed packets without any logging, making debugging hardware communication difficult.
- Safe modification: Add a debug log that prints the raw packet bytes when checksum fails or when an unexpected code is encountered.
- Test coverage: No unit tests for the parsing logic.

**GUI‑thread file operations:**
- Files: `collector_ui.py` (lines 619‑645, 697‑706)
- Why fragile: File writes and flushes happen inside the UI thread (via `_write_eeg_row` and `_write_marker`), which could block the event loop and cause the interface to become unresponsive.
- Safe modification: Move file I/O to a separate worker thread, or use `after()` to schedule writes in idle periods.
- Test coverage: No tests for UI responsiveness under load.

## Scaling Limits

**Single‑threaded CSV writing:**
- Current capacity: Roughly one row per meditation update (typically a few per second).
- Limit: Disk I/O may become a bottleneck if the meditation update rate increases (e.g., if the headset firmware changes).
- Scaling path: Switch to a binary format (e.g., Parquet) or use a buffered writer that batches rows.

**Memory growth of the marker listbox:**
- Current capacity: Capped at 100 entries (line 652‑653).
- Limit: N/A (already bounded).
- Scaling path: Not needed.

## Dependencies at Risk

**`pypdf`:**
- Risk: Unused dependency that may become outdated or introduce vulnerabilities.
- Impact: None (not imported).
- Migration plan: Remove from `pyproject.toml`.

**`pyserial`:**
- Risk: Critical dependency for hardware communication; if a breaking change is introduced, both `main.py` and `collector_ui.py` will fail.
- Impact: Complete loss of functionality.
- Migration plan: Pin to a known‑good version (currently `>=3.5`).

## Missing Critical Features

**No automated tests:**
- Problem: The project lacks any unit or integration tests, making refactoring risky.
- Blocks: Safe evolution of the parsing logic, UI, and data‑logging pipelines.

**No data validation or schema enforcement for CSV output:**
- Problem: The CSV columns are defined ad‑hoc; there is no guarantee that the number of columns matches the header.
- Blocks: Reliable downstream analysis; silent data corruption could go unnoticed.

## Test Coverage Gaps

**Serial packet parsing:**
- What's not tested: All code paths in `main.py` (lines 40‑119) and `collector_ui.py` (lines 739‑852).
- Files: `main.py`, `collector_ui.py`
- Risk: A regression in parsing logic could corrupt recorded data without being detected.
- Priority: High (core functionality).

**Thread synchronization logic:**
- What's not tested: The interaction between `_serial_reader_loop`, `_refresh_ui`, and the file‑writing methods.
- Files: `collector_ui.py` (lines 708‑852, 325‑375)
- Risk: Deadlocks or race conditions could cause the UI to freeze or data to be lost.
- Priority: High.

**File‑path validation:**
- What's not tested: The sanitization (or lack thereof) of `session_id` and `output_root`.
- Files: `collector_ui.py` (lines 525‑540)
- Risk: Path‑traversal attacks could write files outside the intended directory.
- Priority: Medium.

---

*Concerns audit: 2026-03-30*