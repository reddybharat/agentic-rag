import threading
from typing import List

class InMemoryLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(InMemoryLogger, cls).__new__(cls)
                cls._instance._logs = []
            return cls._instance

    def log(self, message: str):
        self._logs.append(message)

    def get_logs(self) -> List[str]:
        return self._logs.copy()

    def clear(self):
        self._logs.clear()

# Singleton instance
logger = InMemoryLogger() 