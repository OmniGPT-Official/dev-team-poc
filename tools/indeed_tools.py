"""Indeed Employer API tools for posting jobs programmatically."""

from __future__ import annotations

import json
from typing import Optional

import httpx
from agno.tools import Toolkit


class IndeedTools(Toolkit):
    """Tools for posting and managing jobs on Indeed via the Employer API."""

    BASE_URL = "https://apis.indeed.com/employer/v1"

    def __init__(self, api_key: str):
        super().__init__(name="indeed_tools")
        self.api_key = api_key
        self.register(self.post_job)
        self.register(self.list_jobs)
        self.register(self.close_job)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def post_job(
        self,
        title: str,
        description_html: str,
        company: str,
        location: str,
        job_type: str = "FULLTIME",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        salary_currency: str = "THB",
        remote: bool = False,
        apply_email: Optional[str] = None,
        apply_url: Optional[str] = None,
    ) -> str:
        """Post a new job listing to Indeed.

        Args:
            title: Job title (e.g. "Padel Coach")
            description_html: Full job description in HTML format (bilingual EN+TH)
            company: Company name (e.g. "Pad Thai Padel")
            location: Job location (e.g. "Bangkok, Thailand")
            job_type: FULLTIME, PARTTIME, CONTRACT, TEMPORARY, INTERNSHIP
            salary_min: Minimum salary (optional)
            salary_max: Maximum salary (optional)
            salary_currency: Currency code (default THB)
            remote: Whether the job allows remote work
            apply_email: Email address for applications (optional)
            apply_url: URL for applications (optional, overrides apply_email)

        Returns:
            JSON string with job ID and posting URL, or error message.
        """
        payload: dict = {
            "title": title,
            "description": description_html,
            "company": {"name": company},
            "location": {"address": location, "country": "TH"},
            "employmentType": job_type,
            "remote": remote,
        }

        if salary_min or salary_max:
            payload["salary"] = {
                "currency": salary_currency,
                "salaryRole": "EXACT",
            }
            if salary_min:
                payload["salary"]["min"] = salary_min
            if salary_max:
                payload["salary"]["max"] = salary_max

        if apply_url:
            payload["applicationContact"] = {"url": apply_url}
        elif apply_email:
            payload["applicationContact"] = {"email": apply_email}

        try:
            response = httpx.post(
                f"{self.BASE_URL}/jobs",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps({
                "success": True,
                "job_id": data.get("id"),
                "url": data.get("url", "https://www.indeed.com/viewjob?jk=" + data.get("id", "")),
                "message": f"Job '{title}' posted successfully to Indeed.",
            })
        except httpx.HTTPStatusError as e:
            return json.dumps({
                "success": False,
                "error": f"Indeed API error {e.response.status_code}: {e.response.text}",
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def list_jobs(self, limit: int = 20) -> str:
        """List currently active job postings on Indeed.

        Args:
            limit: Maximum number of jobs to return (default 20)

        Returns:
            JSON string with list of active jobs.
        """
        try:
            response = httpx.get(
                f"{self.BASE_URL}/jobs",
                headers=self._headers(),
                params={"limit": limit, "status": "OPEN"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            jobs = data.get("jobs", [])
            return json.dumps({
                "success": True,
                "count": len(jobs),
                "jobs": [
                    {
                        "id": j.get("id"),
                        "title": j.get("title"),
                        "location": j.get("location", {}).get("address"),
                        "posted_at": j.get("createdAt"),
                        "url": j.get("url"),
                    }
                    for j in jobs
                ],
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def close_job(self, job_id: str) -> str:
        """Close (remove) an active job posting on Indeed.

        Args:
            job_id: The Indeed job ID to close.

        Returns:
            JSON string confirming closure or error.
        """
        try:
            response = httpx.patch(
                f"{self.BASE_URL}/jobs/{job_id}",
                headers=self._headers(),
                json={"status": "CLOSED"},
                timeout=30,
            )
            response.raise_for_status()
            return json.dumps({"success": True, "message": f"Job {job_id} closed successfully."})
        except httpx.HTTPStatusError as e:
            return json.dumps({
                "success": False,
                "error": f"Indeed API error {e.response.status_code}: {e.response.text}",
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
