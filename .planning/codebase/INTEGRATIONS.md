# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**None detected** - This is a standalone desktop application that reads from a local serial port.

## Data Storage

**Databases:**
- None - Data is stored as CSV files on local filesystem

**File Storage:**
- Local filesystem only
- CSV files for EEG data (`eeg_rows.csv`) and markers (`markers.csv`)
- JSON metadata files (`session_meta.json`)
- Output directory: `sessions/` (gitignored)
- Legacy flat file: `mindtune_full_eeg_data.csv` (in project root)

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None - No authentication or user management

## Monitoring & Observability

**Error Tracking:**
- None - Errors printed to console and logged in marker files

**Logs:**
- Console output via `print()` statements
- Marker CSV files capture event logs (start/stop, serial connections, errors)

## CI/CD & Deployment

**Hosting:**
- Desktop application; no deployment target

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- None required - All configuration is hardcoded or entered via GUI

**Secrets location:**
- No secrets; configuration is non-sensitive (COM port, baud rate, session IDs)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Hardware Integration

**Serial Communication:**
- Interface: `pyserial` library
- Protocol: Custom binary protocol for EEG headset (MindTune px3809N-1ETC)
- Connection: Bluetooth dongle → COM port (COM1, COM3, etc.)
- Baud rate: 57600 (configurable)
- Data format: Binary packets with sync bytes (0xAA 0xAA), payload, checksum
- Payload codes: Signal quality (0x02), Attention (0x04), Meditation (0x05), ASIC EEG Power (0x83)

## File System Integration

**Session Management:**
- Creates session directories under configurable root (`sessions/`)
- Generates three files per session:
  - `eeg_rows.csv`: Timestamped EEG data with emotion/event markers
  - `markers.csv`: Event and annotation markers
  - `session_meta.json`: Session configuration and key mappings
- Files opened in append mode to support session resumption

---

*Integration audit: 2026-03-30*