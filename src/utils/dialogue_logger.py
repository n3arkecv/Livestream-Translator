import json
import csv
import time
import os
from datetime import datetime
from typing import Dict, Literal

class DialogueLogger:
    """
    Logs dialogue records (source, translation, context) to a file.
    """
    def __init__(self, output_dir: str = "logs/dialogue", format: Literal["jsonl", "csv"] = "jsonl"):
        self.output_dir = output_dir
        self.format = format
        self.current_file = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        self._open_file()

    def _open_file(self):
        filename = f"dialogue_{self.session_id}.{self.format}"
        filepath = os.path.join(self.output_dir, filename)
        self.filepath = filepath
        # We open in append mode each time or keep open? 
        # For safety, maybe open/close or keep open. 
        # Let's keep it simple: append mode open/close on write or keep open.
        # Keeping open is more efficient.
        
        if self.format == "csv":
            self.file_handle = open(filepath, "a", newline='', encoding='utf-8')
            self.writer = csv.writer(self.file_handle)
            # Write header if new file
            if os.path.getsize(filepath) == 0:
                self.writer.writerow(["timestamp", "session_id", "sentence_id", "source", "translation", "context", "latency"])
        else:
            self.file_handle = open(filepath, "a", encoding='utf-8')

    def append_record(self, record: Dict):
        """
        Appends a record to the log.
        """
        record["timestamp"] = datetime.now().isoformat()
        record["session_id"] = self.session_id
        
        if self.format == "jsonl":
            json.dump(record, self.file_handle, ensure_ascii=False)
            self.file_handle.write("\n")
        else:
            # CSV mapping
            self.writer.writerow([
                record.get("timestamp"),
                record.get("session_id"),
                record.get("sentence_id"),
                record.get("source_sentence"),
                record.get("translated_sentence"),
                record.get("scenario_context"),
                record.get("latency_ms")
            ])
            
        self.file_handle.flush()

    def close(self):
        if self.file_handle:
            self.file_handle.close()

