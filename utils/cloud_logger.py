"""
Cloud Logger - Dumps logs to Google Docs for Railway visibility

Usage:
    from utils.cloud_logger import CloudLogger

    # Initialize at start of workflow
    logger = CloudLogger.get_instance()
    logger.start_session("Software Development Workflow")

    # Log throughout your code
    logger.log("INFO", "STEP", "Starting process...")
    logger.log("ERROR", "STEP", "Something failed", {"error": "details"})

    # At end, get the Google Doc URL
    doc_url = logger.end_session()
    print(f"Logs: {doc_url}")
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path


class CloudLogger:
    """
    Singleton logger that buffers logs and dumps to Google Docs.
    Thread-safe for use in async/multi-threaded workflows.
    """

    _instance: Optional["CloudLogger"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._logs: List[Dict[str, Any]] = []
        self._session_name: str = ""
        self._session_start: Optional[datetime] = None
        self._doc_id: Optional[str] = None
        self._doc_url: Optional[str] = None
        self._log_lock = threading.Lock()
        self._flush_interval = 20  # Flush every N logs
        self._enabled = True

    @classmethod
    def get_instance(cls) -> "CloudLogger":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_session(self, session_name: str = "Agent-Os Session") -> str:
        """
        Start a new logging session. Creates a Google Doc for logs.

        Args:
            session_name: Name for this session (appears in doc title)

        Returns:
            Google Doc URL for the log document
        """
        with self._log_lock:
            self._logs = []
            self._session_name = session_name
            self._session_start = datetime.now()
            self._doc_id = None
            self._doc_url = None

        # Create the log document
        timestamp = self._session_start.strftime("%Y-%m-%d %H:%M:%S")
        title = f"Logs: {session_name} - {timestamp}"

        initial_content = f"""{'=' * 60}
AGENT-OS LOG SESSION
{'=' * 60}

Session: {session_name}
Started: {timestamp}
Environment: {'Railway' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Local'}

{'=' * 60}
LOGS
{'=' * 60}

"""

        try:
            from tools.google_docs_tools import _get_docs_service
            service = _get_docs_service()

            doc = service.documents().create(body={"title": title}).execute()
            self._doc_id = doc["documentId"]
            self._doc_url = f"https://docs.google.com/document/d/{self._doc_id}/edit"

            # Add initial content
            service.documents().batchUpdate(
                documentId=self._doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": initial_content}}]},
            ).execute()

            self.log("INFO", "SESSION", f"Log document created: {self._doc_url}")
            return self._doc_url

        except Exception as e:
            print(f"[CloudLogger] Failed to create log doc: {e}")
            self._enabled = False
            return ""

    def log(
        self,
        level: str,
        step: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        emoji: str = ""
    ) -> None:
        """
        Log a message.

        Args:
            level: Log level (INFO, ERROR, WARN, DEBUG)
            step: Step or component name
            message: Log message
            data: Optional additional data
            emoji: Optional emoji prefix
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "step": step,
            "message": message,
            "data": data,
            "emoji": emoji,
        }

        with self._log_lock:
            self._logs.append(log_entry)

            # Also print to stdout for local debugging
            prefix = f"{emoji} " if emoji else ""
            print(f"[{timestamp}] {prefix}[{step}] {message}")

            # Auto-flush every N logs
            if len(self._logs) >= self._flush_interval:
                self._flush_logs()

    def info(self, step: str, message: str, data: Optional[Dict] = None) -> None:
        """Log info message."""
        self.log("INFO", step, message, data, "")

    def error(self, step: str, message: str, data: Optional[Dict] = None) -> None:
        """Log error message."""
        self.log("ERROR", step, message, data, "")

    def warn(self, step: str, message: str, data: Optional[Dict] = None) -> None:
        """Log warning message."""
        self.log("WARN", step, message, data, "")

    def debug(self, step: str, message: str, data: Optional[Dict] = None) -> None:
        """Log debug message."""
        self.log("DEBUG", step, message, data, "")

    def step_start(self, step_name: str) -> None:
        """Log start of a workflow step."""
        self.log("INFO", step_name, f"Starting {step_name}...", emoji="")

    def step_end(self, step_name: str, success: bool = True) -> None:
        """Log end of a workflow step."""
        status = "completed" if success else "FAILED"
        self.log("INFO", step_name, f"{step_name} {status}", emoji="")

    def _flush_logs(self) -> None:
        """Flush buffered logs to Google Doc."""
        if not self._enabled or not self._doc_id or not self._logs:
            return

        try:
            from tools.google_docs_tools import _get_docs_service
            service = _get_docs_service()

            # Format logs for document
            log_text = ""
            for entry in self._logs:
                ts = entry["timestamp"]
                level = entry["level"]
                step = entry["step"]
                msg = entry["message"]
                emoji = entry.get("emoji", "")
                data = entry.get("data")

                prefix = f"{emoji} " if emoji else ""
                log_text += f"[{ts}] {level:5} | {prefix}{step}: {msg}\n"

                if data:
                    log_text += f"         DATA: {json.dumps(data, indent=2)}\n"

            # Append to document
            doc = service.documents().get(documentId=self._doc_id).execute()
            end_index = doc["body"]["content"][-1]["endIndex"] - 1

            service.documents().batchUpdate(
                documentId=self._doc_id,
                body={"requests": [{"insertText": {"location": {"index": end_index}, "text": log_text}}]},
            ).execute()

            self._logs = []

        except Exception as e:
            print(f"[CloudLogger] Flush failed: {e}")

    def end_session(self) -> str:
        """
        End the logging session and flush remaining logs.

        Returns:
            Google Doc URL with all logs
        """
        if not self._enabled:
            return ""

        # Calculate session duration
        duration = ""
        if self._session_start:
            elapsed = datetime.now() - self._session_start
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            duration = f"{minutes}m {seconds}s"

        # Add session end marker
        self.log("INFO", "SESSION", f"Session ended. Duration: {duration}")

        # Final flush
        with self._log_lock:
            self._flush_logs()

            # Add footer
            if self._doc_id:
                try:
                    from tools.google_docs_tools import _get_docs_service
                    service = _get_docs_service()

                    footer = f"""

{'=' * 60}
SESSION COMPLETE
{'=' * 60}

Duration: {duration}
End Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
                    doc = service.documents().get(documentId=self._doc_id).execute()
                    end_index = doc["body"]["content"][-1]["endIndex"] - 1

                    service.documents().batchUpdate(
                        documentId=self._doc_id,
                        body={"requests": [{"insertText": {"location": {"index": end_index}, "text": footer}}]},
                    ).execute()
                except Exception as e:
                    print(f"[CloudLogger] Footer failed: {e}")

        return self._doc_url or ""

    def get_doc_url(self) -> str:
        """Get the current log document URL."""
        return self._doc_url or ""


# Convenience function for quick logging
def cloud_log(level: str, step: str, message: str, data: Optional[Dict] = None) -> None:
    """Quick log function - uses singleton instance."""
    CloudLogger.get_instance().log(level, step, message, data)
