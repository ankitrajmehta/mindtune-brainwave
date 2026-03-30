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

try:
    import serial

    Serial = serial.Serial
    SerialException = serial.SerialException
except AttributeError as exc:
    raise SystemExit(
        "PySerial is not available. Uninstall 'serial' and install 'pyserial' (e.g. 'uv add pyserial')."
    ) from exc


EEG_FIELDS = [
    "signal_quality",
    "attention",
    "meditation",
    "delta",
    "theta",
    "low_alpha",
    "high_alpha",
    "low_beta",
    "high_beta",
    "low_gamma",
    "mid_gamma",
]

EMOTIONS = ["calm", "stressed", "delighted", "angry", "unknown"]

EVENTS = [
    "ev_speaking",
    "ev_question",
    "ev_scolded",
    "ev_praised",
    "ev_qna",
    "ev_tech_issue",
]

EVENT_KEY_MAP = {
    "s": "ev_speaking",
    "q": "ev_question",
    "x": "ev_scolded",
    "p": "ev_praised",
    "a": "ev_qna",
    "t": "ev_tech_issue",
}

EMOTION_KEY_MAP = {
    "1": "calm",
    "2": "stressed",
    "3": "delighted",
    "4": "angry",
    "0": "unknown",
}


def timestamp_ms() -> int:
    return int(time.time() * 1000)


class CollectorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MindTune Live Collector")
        self.root.geometry("1100x700")
        self.root.minsize(960, 640)

        self.lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.ui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.reader_thread: Optional[threading.Thread] = None
        self.ser: Optional[Serial] = None

        self.recording = False
        self.serial_connected = False
        self.packet_count = 0

        self.session_id = ""
        self.participant_id = ""
        self.annotator_name = ""

        self.current_emotion = "unknown"
        self.annotator_confidence = 2
        self.events_state = {event_name: 0 for event_name in EVENTS}

        self.latest_eeg = {field: 0 for field in EEG_FIELDS}
        self.last_row_write_ms = 0

        self.last_keypress_ms = {}

        self.session_dir = ""
        self.eeg_file = None
        self.eeg_writer = None
        self.marker_file = None
        self.marker_writer = None

        self.event_labels = {}
        self.marker_listbox: Optional[tk.Listbox] = None
        self.signal_label: Optional[tk.Label] = None
        self.emotion_label: Optional[tk.Label] = None
        self.confidence_label: Optional[tk.Label] = None
        self.recording_label: Optional[tk.Label] = None
        self.serial_label: Optional[tk.Label] = None
        self.packet_label: Optional[tk.Label] = None

        self._build_ui()
        self._bind_keys()
        self.root.after(200, self._refresh_ui)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, padx=12, pady=10)
        top.pack(fill="x")

        now_str = datetime.now().strftime("S%Y%m%d_%H%M%S")

        self.session_var = tk.StringVar(value=now_str)
        self.participant_var = tk.StringVar(value="P001")
        self.annotator_var = tk.StringVar(value="A001")
        self.com_var = tk.StringVar(value="COM1")
        self.baud_var = tk.StringVar(value="57600")
        self.output_root_var = tk.StringVar(value="sessions")

        self._add_labeled_entry(top, "Session ID", self.session_var, 0, 0)
        self._add_labeled_entry(top, "Participant ID", self.participant_var, 0, 2)
        self._add_labeled_entry(top, "Annotator", self.annotator_var, 0, 4)
        self._add_labeled_entry(top, "COM Port", self.com_var, 1, 0)
        self._add_labeled_entry(top, "Baud Rate", self.baud_var, 1, 2)
        self._add_labeled_entry(top, "Output Root", self.output_root_var, 1, 4)

        self.start_button = tk.Button(
            top, text="Start Recording", width=18, command=self.start_recording
        )
        self.start_button.grid(row=0, column=6, rowspan=1, padx=8, pady=4, sticky="ew")

        self.stop_button = tk.Button(
            top,
            text="Stop Recording",
            width=18,
            command=self.stop_recording,
            state="disabled",
        )
        self.stop_button.grid(row=1, column=6, rowspan=1, padx=8, pady=4, sticky="ew")

        status_frame = tk.Frame(self.root, padx=12, pady=8)
        status_frame.pack(fill="x")

        self.recording_label = tk.Label(
            status_frame,
            text="Recording: OFF",
            fg="#a00000",
            font=("Segoe UI", 12, "bold"),
        )
        self.recording_label.pack(side="left", padx=(0, 20))

        self.serial_label = tk.Label(
            status_frame,
            text="Serial: DISCONNECTED",
            fg="#a00000",
            font=("Segoe UI", 11, "bold"),
        )
        self.serial_label.pack(side="left", padx=(0, 20))

        self.packet_label = tk.Label(
            status_frame, text="Packets: 0", font=("Segoe UI", 11)
        )
        self.packet_label.pack(side="left", padx=(0, 20))

        self.signal_label = tk.Label(
            status_frame, text="Signal: N/A", font=("Segoe UI", 11)
        )
        self.signal_label.pack(side="left")

        content = tk.Frame(self.root, padx=12, pady=8)
        content.pack(fill="both", expand=True)

        left = tk.Frame(content)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = tk.Frame(content)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        events_frame = tk.LabelFrame(
            left, text="Active Events (Toggle)", padx=10, pady=10
        )
        events_frame.pack(fill="x", pady=(0, 8))

        for idx, event_name in enumerate(EVENTS):
            pretty_name = event_name.replace("ev_", "").replace("_", " ").title()
            row = tk.Frame(events_frame)
            row.pack(fill="x", pady=3)

            hotkey = self._find_hotkey_for_event(event_name)
            text = f"[{hotkey.upper()}] {pretty_name}"
            tk.Label(
                row, text=text, width=28, anchor="w", font=("Segoe UI", 10, "bold")
            ).pack(side="left")

            status = tk.Label(
                row,
                text="OFF",
                width=10,
                bg="#f2dede",
                fg="#a94442",
                font=("Segoe UI", 10, "bold"),
            )
            status.pack(side="left")
            self.event_labels[event_name] = status

        emotion_frame = tk.LabelFrame(left, text="Emotion", padx=10, pady=10)
        emotion_frame.pack(fill="x", pady=(0, 8))

        self.emotion_label = tk.Label(
            emotion_frame, text="Current: UNKNOWN", font=("Segoe UI", 12, "bold")
        )
        self.emotion_label.pack(anchor="w", pady=(0, 6))

        tk.Label(
            emotion_frame,
            text="Keys: 1=Calm, 2=Stressed, 3=Delighted, 4=Angry, 0=Unknown",
            anchor="w",
            justify="left",
        ).pack(anchor="w")

        confidence_frame = tk.LabelFrame(
            left, text="Annotator Confidence", padx=10, pady=10
        )
        confidence_frame.pack(fill="x", pady=(0, 8))

        self.confidence_label = tk.Label(
            confidence_frame, text="Confidence: 2", font=("Segoe UI", 12, "bold")
        )
        self.confidence_label.pack(anchor="w", pady=(0, 6))

        tk.Label(
            confidence_frame, text="Use [ to decrease and ] to increase (range 1-3)"
        ).pack(anchor="w")

        hotkeys_frame = tk.LabelFrame(left, text="Hotkeys", padx=10, pady=10)
        hotkeys_frame.pack(fill="both", expand=True)

        hotkeys_text = (
            "Event toggles: q=Question, s=Speaking, x=Scolded, p=Praised, a=QnA, t=Tech issue\n"
            "Emotion set: 1=Calm, 2=Stressed, 3=Delighted, 4=Angry, 0=Unknown\n"
            "Confidence: [ lower, ] raise\n"
            "Escape: Stop recording safely"
        )
        tk.Label(hotkeys_frame, text=hotkeys_text, justify="left", anchor="nw").pack(
            fill="both", expand=True
        )

        markers_frame = tk.LabelFrame(
            right, text="Recent Marker Actions", padx=10, pady=10
        )
        markers_frame.pack(fill="both", expand=True)

        self.marker_listbox = tk.Listbox(markers_frame, height=25)
        self.marker_listbox.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_labeled_entry(self, parent, label, text_var, row, column):
        tk.Label(parent, text=label).grid(
            row=row, column=column, padx=4, pady=4, sticky="e"
        )
        entry = tk.Entry(parent, textvariable=text_var, width=18)
        entry.grid(row=row, column=column + 1, padx=4, pady=4, sticky="w")

    def _bind_keys(self) -> None:
        self.root.bind("<Key>", self._on_keypress)
        self.root.bind("<Escape>", self._on_escape)

    def _find_hotkey_for_event(self, event_name: str) -> str:
        for key, value in EVENT_KEY_MAP.items():
            if value == event_name:
                return key
        return "?"

    def _is_debounced(self, key: str, threshold_ms: int = 180) -> bool:
        now_ms = timestamp_ms()
        last = self.last_keypress_ms.get(key, 0)
        if now_ms - last < threshold_ms:
            return True
        self.last_keypress_ms[key] = now_ms
        return False

    def _on_escape(self, _event=None) -> None:
        if self.recording:
            self.stop_recording()

    def _on_keypress(self, event) -> None:
        if not self.recording:
            return

        key = event.keysym.lower()

        if self._is_debounced(key):
            return

        if key in EVENT_KEY_MAP:
            self.toggle_event(EVENT_KEY_MAP[key])
            return

        if key in EMOTION_KEY_MAP:
            self.set_emotion(EMOTION_KEY_MAP[key])
            return

        if key == "bracketleft":
            self.adjust_confidence(-1)
            return

        if key == "bracketright":
            self.adjust_confidence(1)
            return

    def _refresh_ui(self) -> None:
        if (
            self.packet_label is None
            or self.serial_label is None
            or self.signal_label is None
            or self.emotion_label is None
            or self.confidence_label is None
        ):
            self.root.after(200, self._refresh_ui)
            return

        while not self.ui_queue.empty():
            try:
                marker_text = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            self._append_marker_list(marker_text)

        with self.lock:
            signal_quality = self.latest_eeg["signal_quality"]
            packet_count = self.packet_count
            serial_connected = self.serial_connected

        self.packet_label.config(text=f"Packets: {packet_count}")

        if serial_connected:
            self.serial_label.config(text="Serial: CONNECTED", fg="#1f7a1f")
        else:
            self.serial_label.config(text="Serial: DISCONNECTED", fg="#a00000")

        if signal_quality == 0:
            text = "Signal: Good (0)"
            color = "#1f7a1f"
        elif signal_quality == 200:
            text = "Signal: Not worn (200)"
            color = "#a00000"
        else:
            text = f"Signal: {signal_quality}"
            color = "#9a6c00"
        self.signal_label.config(text=text, fg=color)

        for event_name, label in self.event_labels.items():
            if self.events_state[event_name]:
                label.config(text="ON", bg="#dff0d8", fg="#3c763d")
            else:
                label.config(text="OFF", bg="#f2dede", fg="#a94442")

        self.emotion_label.config(text=f"Current: {self.current_emotion.upper()}")
        self.confidence_label.config(text=f"Confidence: {self.annotator_confidence}")

        self.root.after(200, self._refresh_ui)

    def start_recording(self) -> None:
        if self.recording:
            return

        try:
            baud_rate = int(self.baud_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Baud rate must be an integer.")
            return

        session_id = self.session_var.get().strip()
        participant_id = self.participant_var.get().strip()
        annotator = self.annotator_var.get().strip()
        com_port = self.com_var.get().strip()
        output_root = self.output_root_var.get().strip()

        if (
            not session_id
            or not participant_id
            or not annotator
            or not com_port
            or not output_root
        ):
            messagebox.showerror(
                "Missing input", "Please fill all fields before starting."
            )
            return

        self.session_id = session_id
        self.participant_id = participant_id
        self.annotator_name = annotator

        with self.lock:
            self.events_state = {event_name: 0 for event_name in EVENTS}
            self.current_emotion = "unknown"
            self.annotator_confidence = 2
            self.latest_eeg = {field: 0 for field in EEG_FIELDS}
            self.packet_count = 0
            self.serial_connected = False

        self.last_row_write_ms = 0
        self.stop_event.clear()

        try:
            self._open_session_files(
                output_root, session_id, participant_id, annotator, com_port, baud_rate
            )
        except OSError as exc:
            messagebox.showerror(
                "File error", f"Could not create session files:\n{exc}"
            )
            return

        self.recording = True
        if self.recording_label is not None:
            self.recording_label.config(text="Recording: ON", fg="#1f7a1f")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self._append_marker_list("Recording START")
        self._write_marker("lifecycle", "recording", "start", "1", "")

        self.reader_thread = threading.Thread(
            target=self._serial_reader_loop,
            args=(com_port, baud_rate),
            daemon=True,
        )
        self.reader_thread.start()

        self.root.focus_set()

    def stop_recording(self) -> None:
        if not self.recording:
            return

        self.recording = False
        self.stop_event.set()

        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except SerialException:
                pass

        if self.reader_thread is not None and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1.5)

        with self.lock:
            self.serial_connected = False

        self._close_active_events()

        self._write_marker("lifecycle", "recording", "stop", "0", "")
        self._append_marker_list("Recording STOP")

        self._close_session_files()

        if self.recording_label is not None:
            self.recording_label.config(text="Recording: OFF", fg="#a00000")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def toggle_event(self, event_name: str) -> None:
        with self.lock:
            if event_name not in self.events_state:
                return
            new_value = 0 if self.events_state[event_name] else 1
            self.events_state[event_name] = new_value

        action = "start" if new_value == 1 else "end"
        self._write_marker("event", event_name, action, str(new_value), "")

        pretty = event_name.replace("ev_", "").replace("_", " ").title()
        suffix = "ON" if new_value == 1 else "OFF"
        self._append_marker_list(f"{pretty}: {suffix}")

    def set_emotion(self, emotion: str) -> None:
        if emotion not in EMOTIONS:
            return
        with self.lock:
            self.current_emotion = emotion
        self._write_marker("emotion", "emotion", "set", emotion, "")
        self._append_marker_list(f"Emotion -> {emotion.upper()}")

    def adjust_confidence(self, delta: int) -> None:
        with self.lock:
            current = self.annotator_confidence
            new_conf = max(1, min(3, current + delta))
            if new_conf == current:
                return
            self.annotator_confidence = new_conf
        self._write_marker("annotation", "confidence", "set", str(new_conf), "")
        self._append_marker_list(f"Confidence -> {new_conf}")

    def _close_active_events(self) -> None:
        to_close = []
        with self.lock:
            for event_name, active in self.events_state.items():
                if active:
                    to_close.append(event_name)
                    self.events_state[event_name] = 0

        for event_name in to_close:
            self._write_marker("event", event_name, "end", "0", "auto-closed on stop")
            pretty = event_name.replace("ev_", "").replace("_", " ").title()
            self._append_marker_list(f"{pretty}: OFF (auto)")

    def _open_session_files(
        self,
        output_root: str,
        session_id: str,
        participant_id: str,
        annotator: str,
        com_port: str,
        baud_rate: int,
    ) -> None:
        os.makedirs(output_root, exist_ok=True)
        self.session_dir = os.path.join(output_root, session_id)
        os.makedirs(self.session_dir, exist_ok=True)

        eeg_path = os.path.join(self.session_dir, "eeg_rows.csv")
        markers_path = os.path.join(self.session_dir, "markers.csv")
        meta_path = os.path.join(self.session_dir, "session_meta.json")

        eeg_headers = [
            "timestamp_ms",
            "session_id",
            "participant_id",
            *EEG_FIELDS,
            "emo_calm",
            "emo_stressed",
            "emo_delighted",
            "emo_angry",
            "emo_unknown",
            *EVENTS,
            "annotator_confidence",
        ]

        marker_headers = [
            "timestamp_ms",
            "session_id",
            "participant_id",
            "annotator",
            "marker_type",
            "field",
            "action",
            "value",
            "confidence",
            "note",
        ]

        eeg_has_data = os.path.exists(eeg_path) and os.path.getsize(eeg_path) > 0
        markers_has_data = (
            os.path.exists(markers_path) and os.path.getsize(markers_path) > 0
        )

        self.eeg_file = open(eeg_path, mode="a", newline="", encoding="utf-8")
        self.eeg_writer = csv.writer(self.eeg_file)
        if not eeg_has_data:
            self.eeg_writer.writerow(eeg_headers)

        self.marker_file = open(markers_path, mode="a", newline="", encoding="utf-8")
        self.marker_writer = csv.writer(self.marker_file)
        if not markers_has_data:
            self.marker_writer.writerow(marker_headers)

        metadata = {
            "session_id": session_id,
            "participant_id": participant_id,
            "annotator": annotator,
            "com_port": com_port,
            "baud_rate": baud_rate,
            "start_time_iso": datetime.now().isoformat(),
            "events": EVENTS,
            "event_key_map": EVENT_KEY_MAP,
            "emotion_key_map": EMOTION_KEY_MAP,
            "emotion_classes": EMOTIONS,
        }
        with open(meta_path, mode="w", encoding="utf-8") as meta_file:
            json.dump(metadata, meta_file, indent=2)

    def _close_session_files(self) -> None:
        with self.file_lock:
            if self.eeg_file is not None:
                try:
                    self.eeg_file.flush()
                    self.eeg_file.close()
                except OSError:
                    pass
            self.eeg_file = None
            self.eeg_writer = None

            if self.marker_file is not None:
                try:
                    self.marker_file.flush()
                    self.marker_file.close()
                except OSError:
                    pass
            self.marker_file = None
            self.marker_writer = None

    def _write_marker(
        self, marker_type: str, field: str, action: str, value: str, note: str
    ) -> None:
        if self.marker_writer is None:
            return

        with self.lock:
            confidence = self.annotator_confidence

        row = [
            timestamp_ms(),
            self.session_id,
            self.participant_id,
            self.annotator_name,
            marker_type,
            field,
            action,
            value,
            confidence,
            note,
        ]
        with self.file_lock:
            if self.marker_writer is None:
                return
            self.marker_writer.writerow(row)
            if self.marker_file is not None:
                self.marker_file.flush()

    def _append_marker_list(self, text: str) -> None:
        if self.marker_listbox is None:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        self.marker_listbox.insert(0, f"[{ts}] {text}")
        if self.marker_listbox.size() > 100:
            self.marker_listbox.delete(100, tk.END)

    def _queue_marker(self, text: str) -> None:
        self.ui_queue.put(text)

    def _build_eeg_row(self) -> list:
        with self.lock:
            eeg = dict(self.latest_eeg)
            events = dict(self.events_state)
            emotion = self.current_emotion
            confidence = self.annotator_confidence

        emotions = {f"emo_{name}": 1 if emotion == name else 0 for name in EMOTIONS}

        row = [
            timestamp_ms(),
            self.session_id,
            self.participant_id,
            eeg["signal_quality"],
            eeg["attention"],
            eeg["meditation"],
            eeg["delta"],
            eeg["theta"],
            eeg["low_alpha"],
            eeg["high_alpha"],
            eeg["low_beta"],
            eeg["high_beta"],
            eeg["low_gamma"],
            eeg["mid_gamma"],
            emotions["emo_calm"],
            emotions["emo_stressed"],
            emotions["emo_delighted"],
            emotions["emo_angry"],
            emotions["emo_unknown"],
            events["ev_speaking"],
            events["ev_question"],
            events["ev_scolded"],
            events["ev_praised"],
            events["ev_qna"],
            events["ev_tech_issue"],
            confidence,
        ]
        return row

    def _write_eeg_row(self) -> None:
        if not self.recording or self.eeg_writer is None:
            return

        row = self._build_eeg_row()
        with self.file_lock:
            self.eeg_writer.writerow(row)
            if self.eeg_file is not None:
                self.eeg_file.flush()
        self.last_row_write_ms = row[0]

    def _serial_reader_loop(self, com_port: str, baud_rate: int) -> None:
        while not self.stop_event.is_set():
            if self.ser is None or not self.ser.is_open:
                try:
                    self.ser = Serial(com_port, baud_rate, timeout=1)
                    with self.lock:
                        self.serial_connected = True
                    self._write_marker("serial", "connection", "open", "1", "")
                    self._queue_marker(f"Serial connected on {com_port}")
                except SerialException as exc:
                    with self.lock:
                        self.serial_connected = False
                    self._queue_marker(f"Serial reconnect failed: {exc}")
                    time.sleep(2)
                    continue

            try:
                self._read_and_parse_packet()
            except SerialException as exc:
                with self.lock:
                    self.serial_connected = False
                self._write_marker("serial", "connection", "error", "0", str(exc))
                self._queue_marker(f"Serial error: {exc}")
                try:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                except SerialException:
                    pass
                self.ser = None
                time.sleep(1)

    def _read_and_parse_packet(self) -> None:
        ser = self.ser
        if ser is None:
            return

        if ser.read(1) != b"\xaa":
            return
        if ser.read(1) != b"\xaa":
            return

        plen_byte = ser.read(1)
        if not plen_byte:
            return
        plen = plen_byte[0]
        if plen > 169:
            return

        payload = ser.read(plen)
        if len(payload) < plen:
            return

        chksum_byte = ser.read(1)
        if not chksum_byte:
            return
        chksum = chksum_byte[0]

        calc_chksum = (~(sum(payload) & 0xFF)) & 0xFF
        if calc_chksum != chksum:
            return

        with self.lock:
            self.packet_count += 1

        i = 0
        meditation_updated = False
        while i < plen:
            code = payload[i]
            i += 1

            if code == 0x02:
                if i >= plen:
                    break
                with self.lock:
                    self.latest_eeg["signal_quality"] = payload[i]
                i += 1

            elif code == 0x04:
                if i >= plen:
                    break
                with self.lock:
                    self.latest_eeg["attention"] = payload[i]
                i += 1

            elif code == 0x05:
                if i >= plen:
                    break
                with self.lock:
                    self.latest_eeg["meditation"] = payload[i]
                i += 1
                meditation_updated = True

            elif code == 0x83:
                if i >= plen:
                    break
                vlen = payload[i]
                i += 1
                if vlen == 24 and i + 24 <= plen:
                    bands = [
                        (payload[i] << 16) | (payload[i + 1] << 8) | payload[i + 2],
                        (payload[i + 3] << 16) | (payload[i + 4] << 8) | payload[i + 5],
                        (payload[i + 6] << 16) | (payload[i + 7] << 8) | payload[i + 8],
                        (payload[i + 9] << 16)
                        | (payload[i + 10] << 8)
                        | payload[i + 11],
                        (payload[i + 12] << 16)
                        | (payload[i + 13] << 8)
                        | payload[i + 14],
                        (payload[i + 15] << 16)
                        | (payload[i + 16] << 8)
                        | payload[i + 17],
                        (payload[i + 18] << 16)
                        | (payload[i + 19] << 8)
                        | payload[i + 20],
                        (payload[i + 21] << 16)
                        | (payload[i + 22] << 8)
                        | payload[i + 23],
                    ]
                    with self.lock:
                        self.latest_eeg["delta"] = bands[0]
                        self.latest_eeg["theta"] = bands[1]
                        self.latest_eeg["low_alpha"] = bands[2]
                        self.latest_eeg["high_alpha"] = bands[3]
                        self.latest_eeg["low_beta"] = bands[4]
                        self.latest_eeg["high_beta"] = bands[5]
                        self.latest_eeg["low_gamma"] = bands[6]
                        self.latest_eeg["mid_gamma"] = bands[7]
                    i += 24
                else:
                    i += min(vlen, plen - i)

            elif code >= 0x80:
                if i >= plen:
                    break
                vlen = payload[i]
                i += 1
                i += min(vlen, max(0, plen - i))

            else:
                if i < plen:
                    i += 1

        if meditation_updated:
            self._write_eeg_row()

    def _on_close(self) -> None:
        if self.recording:
            self.stop_recording()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = CollectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
