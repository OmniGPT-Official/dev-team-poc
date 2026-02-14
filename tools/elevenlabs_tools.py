"""
ElevenLabs Calling Tools

Tools for making outbound calls via ElevenLabs Conversational AI API.
Supports batch calling, status monitoring, retries, and result retrieval.
"""

import os
from typing import List, Dict, Any
from agno.tools import tool


@tool(show_result=True)
def submit_batch_call(campaign_name: str, recipients: List[Dict[str, Any]]) -> dict:
    """Submit a batch of outbound calls to ElevenLabs.

    Each recipient should be a dict with:
    - phone_number (required): The phone number to call
    - restaurant_name (optional): Name for personalization
    - city (optional): City for personalization
    - Any other custom fields your ElevenLabs agent uses

    Args:
        campaign_name: A name for this batch (e.g. "US Restaurants Feb 2026")
        recipients: List of dicts with phone_number and custom fields

    Returns:
        Dict with batch_id to track this job

    Example:
        recipients = [
            {"phone_number": "+1234567890", "restaurant_name": "Joe's Pizza", "city": "NYC"},
            {"phone_number": "+1987654321", "restaurant_name": "Pasta House", "city": "LA"}
        ]
        result = submit_batch_call("US Restaurants", recipients)
    """
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        phone_number_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")

        if not agent_id or not phone_number_id:
            return {
                "error": "Missing ElevenLabs configuration",
                "message": "Set ELEVENLABS_AGENT_ID and ELEVENLABS_PHONE_NUMBER_ID env vars"
            }

        response = client.conversational_ai.batch_calls.submit(
            call_name=campaign_name,
            agent_id=agent_id,
            agent_phone_number_id=phone_number_id,
            recipients=recipients,
        )

        return {
            "success": True,
            "batch_id": response.id,
            "status": "submitted",
            "total_recipients": len(recipients),
            "message": f"Batch call submitted successfully with {len(recipients)} recipients"
        }

    except ImportError:
        return {
            "error": "ElevenLabs SDK not installed",
            "message": "Run: pip install elevenlabs"
        }
    except Exception as e:
        return {
            "error": "Failed to submit batch call",
            "message": str(e)
        }


@tool(show_result=True)
def get_batch_status(batch_id: str) -> dict:
    """Check the current status of a batch calling job.

    Args:
        batch_id: The batch ID returned from submit_batch_call

    Returns:
        Status info including how many calls completed, failed, etc.

    Example:
        status = get_batch_status("batch_abc123")
        print(f"Completed: {status['completed']}/{status['total']}")
    """
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        response = client.conversational_ai.batch_calls.get(batch_id)

        return {
            "success": True,
            "batch_id": batch_id,
            "status": response.status,
            "total": response.total,
            "completed": response.completed,
            "failed": response.failed,
            "in_progress": response.total - response.completed - response.failed,
        }

    except ImportError:
        return {
            "error": "ElevenLabs SDK not installed",
            "message": "Run: pip install elevenlabs"
        }
    except Exception as e:
        return {
            "error": "Failed to get batch status",
            "message": str(e)
        }


@tool(show_result=True)
def retry_failed_calls(batch_id: str) -> dict:
    """Retry all failed/unanswered calls in a batch.

    Use this when get_batch_status shows failed calls.
    ElevenLabs will retry all unsuccessful calls.

    Args:
        batch_id: The batch to retry

    Returns:
        Confirmation of the retry

    Example:
        result = retry_failed_calls("batch_abc123")
        if result['success']:
            print("Retry submitted!")
    """
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        response = client.conversational_ai.batch_calls.retry(batch_id)

        return {
            "success": True,
            "batch_id": batch_id,
            "retry_status": "submitted",
            "message": "Failed calls queued for retry"
        }

    except ImportError:
        return {
            "error": "ElevenLabs SDK not installed",
            "message": "Run: pip install elevenlabs"
        }
    except Exception as e:
        return {
            "error": "Failed to retry calls",
            "message": str(e)
        }


@tool(show_result=True)
def get_call_result(conversation_id: str) -> dict:
    """Get the transcript and outcome of a specific call.

    Args:
        conversation_id: The ID of the individual call/conversation

    Returns:
        Transcript, duration, evaluation, and data collected

    Example:
        result = get_call_result("conv_abc123")
        print(f"Transcript: {result['transcript']}")
        print(f"Duration: {result['duration']} seconds")
    """
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        response = client.conversational_ai.conversations.get(conversation_id)

        return {
            "success": True,
            "conversation_id": conversation_id,
            "transcript": response.transcript,
            "duration": response.duration,
            "evaluation": response.evaluation,
            "data_collected": response.data_collection,
        }

    except ImportError:
        return {
            "error": "ElevenLabs SDK not installed",
            "message": "Run: pip install elevenlabs"
        }
    except Exception as e:
        return {
            "error": "Failed to get call result",
            "message": str(e)
        }
