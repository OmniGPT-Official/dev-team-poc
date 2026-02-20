"""
ElevenLabs Batch Calling Toolkit

Custom Agno toolkit for ElevenLabs Conversational AI batch calling.
Uses REST API directly to avoid SDK version compatibility issues.
"""

import os
from typing import List, Dict, Any, Optional
import requests
from agno.tools import Toolkit


class ElevenLabsBatchCallingTools(Toolkit):
    """Toolkit for ElevenLabs Conversational AI batch calling operations.

    This toolkit uses the ElevenLabs REST API directly instead of the Python SDK
    to avoid version compatibility issues with the rapidly changing SDK.

    Required environment variables:
    - ELEVENLABS_API_KEY: Your ElevenLabs API key
    - ELEVENLABS_AGENT_ID: Your conversational AI agent ID
    - ELEVENLABS_PHONE_NUMBER_ID: Your ElevenLabs phone number ID
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        base_url: str = "https://api.elevenlabs.io/v1",
    ):
        """Initialize the ElevenLabs batch calling toolkit.

        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            agent_id: Conversational AI agent ID (defaults to ELEVENLABS_AGENT_ID env var)
            phone_number_id: Phone number ID (defaults to ELEVENLABS_PHONE_NUMBER_ID env var)
            base_url: Base URL for ElevenLabs API
        """
        super().__init__(name="elevenlabs_batch_calling")

        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.agent_id = agent_id or os.getenv("ELEVENLABS_AGENT_ID")
        self.phone_number_id = phone_number_id or os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
        self.base_url = base_url

        # Register all methods as tools
        self.register(self.submit_batch_call)
        self.register(self.get_batch_status)
        self.register(self.retry_failed_calls)
        self.register(self.get_call_result)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def submit_batch_call(self, campaign_name: str, recipients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Submit a batch of outbound calls to ElevenLabs.

        Each recipient should be a dict with:
        - phone_number (required): The phone number to call in E.164 format
        - restaurant_name (optional): Name for personalization
        - city (optional): City for personalization
        - country (optional): Country for personalization
        - Any other custom fields your ElevenLabs agent uses

        Args:
            campaign_name: A name for this batch (e.g. "US Restaurants Feb 2026")
            recipients: List of dicts with phone_number and custom fields

        Returns:
            Dict with batch_id to track this job

        Example:
            recipients = [
                {"phone_number": "+1234567890", "restaurant_name": "Joe's Pizza", "city": "NYC", "country": "US"},
                {"phone_number": "+1987654321", "restaurant_name": "Pasta House", "city": "LA", "country": "US"}
            ]
            result = toolkit.submit_batch_call("US Restaurants", recipients)
        """
        if not self.agent_id or not self.phone_number_id:
            return {
                "error": "Missing configuration",
                "message": "Set ELEVENLABS_AGENT_ID and ELEVENLABS_PHONE_NUMBER_ID env vars"
            }

        # ElevenLabs API requires:
        # {
        #   phone_number,
        #   conversation_initiation_client_data: {
        #     conversation_config_override: { agent: { language: "en" } },
        #     dynamic_variables: { restaurant_name, city, ... }
        #   }
        # }
        # `language` is an Override field — must NOT be placed in dynamic_variables.
        # All other non-phone fields go into dynamic_variables.
        formatted_recipients = []
        for r in recipients:
            if "phone_number" not in r:
                return {
                    "error": "Invalid recipient",
                    "message": f"Recipient missing required phone_number field: {r}"
                }
            recipient: Dict[str, Any] = {"phone_number": r["phone_number"]}
            language = r.get("language")
            dynamic_vars = {
                k: v for k, v in r.items()
                if k not in ("phone_number", "language") and v is not None and v != ""
            }
            conversation_data: Dict[str, Any] = {}
            if language:
                conversation_data["conversation_config_override"] = {
                    "agent": {"language": language}
                }
            if dynamic_vars:
                conversation_data["dynamic_variables"] = dynamic_vars
            if conversation_data:
                recipient["conversation_initiation_client_data"] = conversation_data
            formatted_recipients.append(recipient)

        try:
            url = f"{self.base_url}/convai/batch-calling/submit"
            payload = {
                "call_name": campaign_name,
                "agent_id": self.agent_id,
                "agent_phone_number_id": self.phone_number_id,
                "recipients": formatted_recipients
            }

            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            return {
                "success": True,
                "batch_id": data.get("id"),
                "status": "submitted",
                "total_recipients": len(recipients),
                "message": f"Batch call submitted successfully with {len(recipients)} recipients"
            }

        except requests.exceptions.HTTPError as e:
            error_body = None
            try:
                error_body = e.response.json()
            except Exception:
                error_body = e.response.text
            return {
                "error": "Failed to submit batch call",
                "message": str(e),
                "status_code": e.response.status_code,
                "api_error": error_body
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to submit batch call",
                "message": str(e),
                "status_code": None
            }

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Check the current status of a batch calling job.

        Args:
            batch_id: The batch ID returned from submit_batch_call

        Returns:
            Status info including how many calls completed, failed, etc.

        Example:
            status = toolkit.get_batch_status("batch_abc123")
            print(f"Completed: {status['completed']}/{status['total']}")
        """
        try:
            url = f"{self.base_url}/convai/batch-calling/{batch_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()

            data = response.json()
            return {
                "success": True,
                "batch_id": batch_id,
                "status": data.get("status"),
                "total": data.get("total", 0),
                "completed": data.get("completed", 0),
                "failed": data.get("failed", 0),
                "in_progress": data.get("total", 0) - data.get("completed", 0) - data.get("failed", 0)
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to get batch status",
                "message": str(e),
                "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            }

    def retry_failed_calls(self, batch_id: str) -> Dict[str, Any]:
        """Retry all failed/unanswered calls in a batch.

        Use this when get_batch_status shows failed calls.
        ElevenLabs will retry all unsuccessful calls.

        Args:
            batch_id: The batch to retry

        Returns:
            Confirmation of the retry

        Example:
            result = toolkit.retry_failed_calls("batch_abc123")
            if result['success']:
                print("Retry submitted!")
        """
        try:
            url = f"{self.base_url}/convai/batch-calling/{batch_id}/retry"
            response = requests.post(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()

            return {
                "success": True,
                "batch_id": batch_id,
                "retry_status": "submitted",
                "message": "Failed calls queued for retry"
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to retry calls",
                "message": str(e),
                "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            }

    def get_call_result(self, conversation_id: str) -> Dict[str, Any]:
        """Get the transcript and outcome of a specific call.

        Args:
            conversation_id: The ID of the individual call/conversation

        Returns:
            Transcript, duration, evaluation, and data collected

        Example:
            result = toolkit.get_call_result("conv_abc123")
            print(f"Transcript: {result['transcript']}")
            print(f"Duration: {result['duration']} seconds")
        """
        try:
            url = f"{self.base_url}/convai/conversations/{conversation_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()

            data = response.json()
            return {
                "success": True,
                "conversation_id": conversation_id,
                "transcript": data.get("transcript"),
                "duration": data.get("duration"),
                "evaluation": data.get("evaluation"),
                "data_collected": data.get("data_collection")
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to get call result",
                "message": str(e),
                "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            }
