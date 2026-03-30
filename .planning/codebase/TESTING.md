# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework

**Runner:**
- Not detected - no test framework configured
- No test dependencies in `pyproject.toml`

**Assertion Library:**
- Not applicable

**Run Commands:**
```bash
# No test commands available
# To add testing, install pytest:
# uv add --dev pytest
# Then run: pytest
```

## Test File Organization

**Location:**
- No test files exist in the project
- Recommended: `tests/` directory at project root

**Naming:**
- Not applicable
- Recommended pattern: `test_*.py` or `*_test.py`

**Structure:**
```
mindtune/
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_collector_ui.py
└── ...
```

## Test Structure

**Suite Organization:**
- Not applicable
- Recommended pattern:
```python
import pytest
from collector_ui import CollectorApp

class TestCollectorApp:
    def test_timestamp_ms(self):
        result = timestamp_ms()
        assert isinstance(result, int)
        assert result > 0

    def test_toggle_event(self):
        # Mock tkinter root
        pass
```

**Patterns:**
- Not applicable
- Recommended: Use pytest fixtures for tkinter root mocking
- Use `pytest.mark.parametrize` for multiple test cases

## Mocking

**Framework:** Not applicable
- Recommended: `unittest.mock` or `pytest-mock`

**Patterns:**
- Not applicable
- Recommended mocking for serial port:
```python
from unittest.mock import Mock, patch

def test_serial_reader_loop():
    with patch('collector_ui.Serial') as mock_serial:
        mock_serial.return_value.read.return_value = b'\xaa\xaa'
        # Test parsing logic
```

**What to Mock:**
- Serial port communications (`serial.Serial`)
- File I/O operations (`open`, `csv.writer`)
- Time functions (`time.time`, `time.sleep`)
- UI components (`tkinter` widgets)

**What NOT to Mock:**
- Pure data structures and constants
- Simple utility functions like `timestamp_ms()`

## Fixtures and Factories

**Test Data:**
- Not applicable
- Recommended fixtures:
```python
@pytest.fixture
def sample_eeg_packet():
    return bytes([0xAA, 0xAA, 0x20, 0x02, 0x00, ...])

@pytest.fixture
def collector_app():
    root = tk.Tk()
    app = CollectorApp(root)
    yield app
    root.destroy()
```

**Location:**
- Not applicable
- Recommended: `tests/conftest.py` for shared fixtures

## Coverage

**Requirements:** Not enforced
- Recommended: Minimum 70% coverage for new code

**View Coverage:**
```bash
# After adding pytest-cov:
pytest --cov=.
# Generate HTML report:
pytest --cov=. --cov-report=html
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Test pure logic, mock external dependencies
- Priority: Packet parsing, checksum calculation, data transformation

**Integration Tests:**
- Scope: Component interactions
- Approach: Test serial reader with mocked serial port
- Priority: File writing, UI state updates, threading synchronization

**E2E Tests:**
- Framework: Not used
- Recommended: Avoid for UI-heavy application; focus on integration tests

## Common Patterns

**Async Testing:**
```python
# Testing threaded code
def test_serial_reader_thread():
    app = CollectorApp(tk.Tk())
    app.start_recording()
    # Allow thread to run
    time.sleep(0.1)
    app.stop_recording()
    assert not app.recording
```

**Error Testing:**
```python
def test_serial_exception_handling():
    with pytest.raises(SerialException):
        # Simulate serial port failure
        pass
```

## Missing Test Areas

**Critical untested functionality:**
1. Packet parsing logic (`_read_and_parse_packet`)
2. Checksum calculation and verification
3. File I/O and CSV writing
4. Thread synchronization and lock handling
5. UI state management and event handling

**Recommended test priorities:**
1. Data parsing functions (high priority)
2. File writing operations (medium priority)
3. UI logic with mocked tkinter (medium priority)
4. Threading behavior (low priority, hard to test)

---

*Testing analysis: 2026-03-30*
