import time
from typing import Dict

class LatencyTracker:
    """
    Tracks latency for translation tasks.
    """
    def __init__(self):
        self.start_times: Dict[int, float] = {}

    def start(self, sentence_id: int):
        """
        Starts tracking latency for a sentence ID.
        """
        self.start_times[sentence_id] = time.time()

    def stop(self, sentence_id: int) -> float:
        """
        Stops tracking and returns the latency in milliseconds.
        Returns 0.0 if start time not found.
        """
        if sentence_id in self.start_times:
            start_time = self.start_times.pop(sentence_id)
            return (time.time() - start_time) * 1000.0
        return 0.0

