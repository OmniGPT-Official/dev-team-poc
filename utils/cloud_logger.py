"""
Cloud Logger - Dumps ALL logs (including agno framework) to Google Docs for Railway visibility

Usage:
    from utils.cloud_logger import CloudLogger, setup_agno_cloud_logging

    # Initialize at start of workflow
    logger = CloudLogger.get_instance()
    logger.start_session("Software Development Workflow")

    # Hook into agno's logging system to capture framework logs
    setup_agno_cloud_logging()

    # Log throughout your code
    logger.log("INFO", "STEP", "Starting process...")

    # At end, get the Google Doc URL
    doc_url = logger.end_session()
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Optional, Any, Dict, List


# ============================================================================
# CUSTOM LOGGING HANDLER - Forwards Python logs to CloudLogger
# ============================================================================

class CloudLogHandler(logging.Handler):
    """
    Custom logging handler that forwards all Python logging to CloudLogger.
    This captures agno framework debug logs.
    """

    def __init__(self):
        super().__init__()
        self.setLevel(logging.DEBUG)  # Capture all levels

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Get the CloudLogger instance
            cloud_logger = CloudLogger.get_instance()

            # Skip if no session is active
            if not cloud_logger._doc_id:
                return

            # Format the log message
            msg = self.format(record)
            if not msg:
                return

            # Determine source from logger name
            source = "AGNO"
            if "team" in record.name:
                source = "TEAM"
            elif "workflow" in record.name:
                source = "WORKFLOW"
            elif "agent" in record.name.lower():
                source = "AGENT"

            # Map log level
            level = record.levelname

            # Forward to cloud logger (but don't print again - already printed by agno)
            cloud_logger._log_internal(level, source, msg)

        except Exception:
            # Don't raise exceptions from logging
            pass


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
        self._flush_interval = 15  # Flush every N logs
        self._enabled = True
        self._agno_handler_installed = False

    @classmethod
    def get_instance(cls) -> "CloudLogger":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_session(
        self,
        session_name: str = "Agent-Os Session",
        use_existing_doc: Optional[str] = None
    ) -> str:
        """
        Start a new logging session.

        Args:
            session_name: Name for this session (appears in doc title)
            use_existing_doc: Optional existing Google Doc ID to append to

        Returns:
            Google Doc URL for the log document
        """
        with self._log_lock:
            self._logs = []
            self._session_name = session_name
            self._session_start = datetime.now()
            self._doc_id = None
            self._doc_url = None

        timestamp = self._session_start.strftime("%Y-%m-%d %H:%M:%S")

        # Check for hardcoded doc ID from environment
        hardcoded_doc = use_existing_doc or os.environ.get("CLOUD_LOG_DOC_ID")

        try:
            from tools.google_docs_tools import _get_docs_service
            service = _get_docs_service()

            if hardcoded_doc:
                # Use existing document - append new session
                self._doc_id = hardcoded_doc
                self._doc_url = f"https://docs.google.com/document/d/{self._doc_id}/edit"

                session_header = f"""

{'=' * 60}
NEW SESSION: {session_name}
{'=' * 60}

Started: {timestamp}
Environment: {'Railway' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Local'}

"""
                # Append to end of document
                doc = service.documents().get(documentId=self._doc_id).execute()
                end_index = doc["body"]["content"][-1]["endIndex"] - 1

                service.documents().batchUpdate(
                    documentId=self._doc_id,
                    body={"requests": [{"insertText": {"location": {"index": end_index}, "text": session_header}}]},
                ).execute()

            else:
                # Create new document
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
                doc = service.documents().create(body={"title": title}).execute()
                self._doc_id = doc["documentId"]
                self._doc_url = f"https://docs.google.com/document/d/{self._doc_id}/edit"

                service.documents().batchUpdate(
                    documentId=self._doc_id,
                    body={"requests": [{"insertText": {"location": {"index": 1}, "text": initial_content}}]},
                ).execute()

            self.log("INFO", "SESSION", f"Log document: {self._doc_url}")
            return self._doc_url

        except Exception as e:
            print(f"[CloudLogger] Failed to create/open log doc: {e}")
            self._enabled = False
            return ""

    def _log_internal(
        self,
        level: str,
        step: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        emoji: str = ""
    ) -> None:
        """Internal log method - doesn't print to stdout (used by CloudLogHandler)."""
        if not self._enabled:
            return

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

            # Auto-flush every N logs
            if len(self._logs) >= self._flush_interval:
                self._flush_logs()

    def log(
        self,
        level: str,
        step: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        emoji: str = ""
    ) -> None:
        """
        Log a message (also prints to stdout).

        Args:
            level: Log level (INFO, ERROR, WARN, DEBUG)
            step: Step or component name
            message: Log message
            data: Optional additional data
            emoji: Optional emoji prefix
        """
        # Print to stdout
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        prefix = f"{emoji} " if emoji else ""
        print(f"[{timestamp}] {prefix}[{step}] {message}")

        # Add to buffer
        self._log_internal(level, step, message, data, emoji)

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
        self._log_internal("INFO", "SESSION", f"Session ended. Duration: {duration}")

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


# ============================================================================
# AGNO LOGGING INTEGRATION
# ============================================================================

def setup_agno_cloud_logging() -> None:
    """
    Hook into agno's logging system to capture all framework logs.
    Call this after starting a CloudLogger session.
    """
    cloud_logger = CloudLogger.get_instance()

    if cloud_logger._agno_handler_installed:
        return  # Already installed

    # Create our custom handler
    handler = CloudLogHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))

    # Get all agno loggers and add our handler
    logger_names = ["agno", "agno-team", "agno-workflow"]

    for name in logger_names:
        try:
            agno_logger = logging.getLogger(name)
            agno_logger.addHandler(handler)
            # Ensure debug level is enabled to capture debug logs
            if agno_logger.level > logging.DEBUG:
                agno_logger.setLevel(logging.DEBUG)
        except Exception as e:
            print(f"[CloudLogger] Failed to hook {name} logger: {e}")

    cloud_logger._agno_handler_installed = True
    print("[CloudLogger] Agno logging integration enabled")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def cloud_log(level: str, step: str, message: str, data: Optional[Dict] = None) -> None:
    """Quick log function - uses singleton instance."""
    CloudLogger.get_instance().log(level, step, message, data)
