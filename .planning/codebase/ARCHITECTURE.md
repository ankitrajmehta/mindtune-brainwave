# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Monolithic Desktop Application with Two Entry Points

**Key Characteristics:**
- Simple script-based architecture with no external service dependencies
- Two distinct operational modes: headless data logging and GUI-annotated collection
- Shared serial communication logic between both entry points
- File-based persistence using CSV and JSON formats
- Real-time data acquisition and processing pipeline

## Layers

**Data Acquisition Layer:**
- Purpose: Handles serial port communication and raw packet reading
- Location: `main.py` (lines 18-120), `collector_ui.py` (lines 708-851)
- Contains: Serial port configuration, packet synchronization, checksum validation
- Depends on: `pyserial` library
- Used by: Both entry points for raw EEG data ingestion

**Data Processing Layer:**
- Purpose: Parses raw byte payloads into structured EEG data fields
- Location: `main.py` (lines 64-119), `collector_ui.py` (lines 773-851)
- Contains: Payload parsing logic, band extraction, event detection
- Depends on: Data Acquisition Layer
- Used by: Both entry points for converting binary data to meaningful values

**Data Persistence Layer:**
- Purpose: Writes processed data to CSV files for storage and analysis
- Location: `main.py` (lines 25-95), `collector_ui.py` (lines 525-705)
- Contains: CSV writer configuration, file I/O, session management
- Depends on: Data Processing Layer
- Used by: Both entry points for data output

**Presentation Layer (GUI only):**
- Purpose: Provides user interface for annotation and real-time monitoring
- Location: `collector_ui.py` (lines 70-375)
- Contains: Tkinter UI components, event handling, status display
- Depends on: Data Persistence Layer and Data Processing Layer
- Used by: `collector_ui.py` entry point only

## Data Flow

**Raw Data Logging Flow (main.py):**

1. Configure serial port connection (COM_PORT, BAUD_RATE)
2. Open CSV file with predefined header row
3. Continuously read serial packets (sync bytes 0xAA 0xAA)
4. Validate packet structure and checksum
5. Parse payload codes and extract EEG bands
6. Write complete row to CSV when meditation updates
7. Repeat until interrupted (Ctrl+C)

**Annotated Collection Flow (collector_ui.py):**

1. Initialize GUI with session configuration inputs
2. On "Start Recording": open session directory with EEG and marker files
3. Spawn background serial reader thread
4. Continuously parse packets and update in-memory state
5. Write EEG rows when meditation updates (includes emotion/event states)
6. Handle keyboard events for real-time annotations
7. Write marker events to separate CSV file
8. On "Stop Recording": close files, join threads, write stop markers

**State Management:**
- Thread-safe state using `threading.Lock` for shared variables
- UI updates via `queue.Queue` from reader thread to main thread
- Periodic UI refresh via `tkinter.after()` callback

## Key Abstractions

**Serial Packet Parser:**
- Purpose: Encapsulates EEG device protocol (NeuroSky ThinkGear compatible)
- Examples: `main.py` (lines 40-119), `collector_ui.py` (lines 739-851)
- Pattern: State machine parsing byte-by-byte with code-based branching

**Session Manager:**
- Purpose: Handles file organization and metadata for data collection sessions
- Examples: `collector_ui.py` (lines 525-617)
- Pattern: Directory creation, file handles, JSON metadata serialization

**Event/Emotion Tracker:**
- Purpose: Maintains real-time annotation state during collection
- Examples: `collector_ui.py` (lines 480-523)
- Pattern: Dictionary-based state with toggle/set operations

**UI State Binder:**
- Purpose: Synchronizes internal state with GUI elements
- Examples: `collector_ui.py` (lines 325-375)
- Pattern: Periodic polling of state variables and label updates

## Entry Points

**main.py:**
- Location: `main.py`
- Triggers: Direct execution via `python main.py` or `uv run main.py`
- Responsibilities: Raw EEG data logging only, no annotations, outputs single CSV file

**collector_ui.py:**
- Location: `collector_ui.py`
- Triggers: Direct execution via `python collector_ui.py` or `uv run collector_ui.py`
- Responsibilities: Full annotation suite with GUI, session management, multiple output files

## Error Handling

**Strategy:** Defensive programming with graceful degradation

**Patterns:**
- Try-except blocks around serial operations with user-friendly error messages
- Silent continuation on malformed packets (skipped but logged)
- File I/O error handling with messagebox notifications in GUI
- KeyboardInterrupt handling for clean shutdown in main.py
- SerialException catching with automatic reconnection attempts in collector_ui.py

## Cross-Cutting Concerns

**Logging:** Console print statements for status and warnings, no formal logging framework
**Validation:** Basic input validation for GUI fields (required fields, integer parsing)
**Authentication:** Not applicable (local desktop application)

---

*Architecture analysis: 2026-03-30*