# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.11 - Entire application logic, GUI, data collection

**Secondary:**
- None

## Runtime

**Environment:**
- Python 3.11 (specified in `.python-version`)
- Package Manager: `uv` (modern Python package manager)
- Lockfile: `uv.lock` present (36 lines, pins pypdf and pyserial)

## Frameworks

**Core:**
- Tkinter (standard library) - GUI framework for collector UI
- No web frameworks; desktop-only application

**Testing:**
- No test framework detected; no test files found

**Build/Dev:**
- `uv` for dependency management and script execution
- No formal build system (scripts run directly via `uv run`)

## Key Dependencies

**Critical:**
- `pyserial` 3.5 - Serial port communication with EEG headset (Bluetooth dongle)
- `pypdf` 6.9.0 - PDF library (present in dependencies but not imported in current codebase; may be for future PDF reporting)

**Infrastructure:**
- Standard library modules: `csv`, `json`, `tkinter`, `threading`, `queue`, `time`, `os`, `datetime`

## Configuration

**Environment:**
- No `.env` files detected
- Configuration hardcoded in scripts (COM port, baud rate, output paths)
- Session parameters entered via GUI fields

**Build:**
- `pyproject.toml` defines project metadata and dependencies
- `uv.lock` ensures reproducible dependency resolution

## Platform Requirements

**Development:**
- Windows (COM port serial communication)
- Bluetooth dongle and EEG headset driver required for data collection

**Production:**
- Desktop application; no deployment pipeline
- Output directories (`sessions/`) created at runtime

---

*Stack analysis: 2026-03-30*