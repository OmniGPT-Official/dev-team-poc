"""Unified Job Feed Tools — generates Indeed XML and LinkedIn XML from one job store.

How it works:
- Agent calls `add_job(...)` once
- Server serves two feeds:
    GET /indeed-feed.xml   → crawled by Indeed every 24-48h
    GET /linkedin-feed.xml → crawled by LinkedIn every 6h
- Register each URL with the platform ONCE (see setup instructions below)

## Indeed setup (one time)
  https://employers.indeed.com/jobs/feed-submit
  Submit: https://YOUR-APP.railway.app/indeed-feed.xml

## LinkedIn setup (one time)
  https://www.linkedin.com/talent/job-wrapping
  Submit: https://YOUR-APP.railway.app/linkedin-feed.xml
  You'll need your LinkedIn Page numeric Company ID (found in your Page Admin URL).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

from agno.tools import Toolkit

# Module-level shared job store (survives across agent calls in the same process)
# Phase 2: replace with Supabase table for persistence across restarts
_JOB_STORE: list[dict] = []


class JobFeedTools(Toolkit):
    """Manage a shared job store and generate Indeed + LinkedIn XML feeds."""

    def __init__(self, base_url: str = "", poster_email: str = "", linkedin_company_id: str = ""):
        super().__init__(name="job_feed_tools")
        self.base_url = base_url.rstrip("/")
        self.poster_email = poster_email
        self.linkedin_company_id = linkedin_company_id
        self.register(self.add_job)
        self.register(self.list_jobs)
        self.register(self.remove_job)
        self.register(self.get_feed_urls)

    # ------------------------------------------------------------------
    # Public tools
    # ------------------------------------------------------------------

    def add_job(
        self,
        title: str,
        description: str,
        company: str,
        location: str,
        apply_url: str,
        job_type: str = "FULL_TIME",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        salary_currency: str = "THB",
        experience_level: str = "MID_SENIOR_LEVEL",
        workplace_type: str = "On-site",
        reference_number: Optional[str] = None,
    ) -> str:
        """Add a job to both the Indeed feed and LinkedIn feed.

        Args:
            title: Job title (e.g. "Padel Coach")
            description: Full bilingual job description — HTML supported.
                         Use <p>, <ul>, <li>, <b>, <br> tags only.
            company: Company name (e.g. "Pad Thai Padel")
            location: Job location — format "City, Country" (e.g. "Bangkok, Thailand")
            apply_url: URL where candidates apply. MUST start with https://www
            job_type: FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, VOLUNTEER
            salary_min: Minimum monthly salary in THB (optional)
            salary_max: Maximum monthly salary in THB (optional)
            salary_currency: Currency code (default THB)
            experience_level: ENTRY_LEVEL, MID_SENIOR_LEVEL, DIRECTOR, EXECUTIVE, INTERNSHIP, ASSOCIATE
            workplace_type: On-site, Hybrid, Remote
            reference_number: Your internal job reference ID (auto-generated if not provided)

        Returns:
            JSON confirming the job was added and both feed URLs.
        """
        import uuid
        job_id = reference_number or str(uuid.uuid4())[:8].upper()

        job = {
            "id": job_id,
            "title": title,
            "description": description,
            "company": company,
            "location": location,
            "apply_url": apply_url,
            "job_type": job_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "experience_level": experience_level,
            "workplace_type": workplace_type,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "list_date": datetime.now(timezone.utc).strftime("%m/%d/%Y"),
        }
        _JOB_STORE.append(job)

        indeed_url = f"{self.base_url}/indeed-feed.xml"
        linkedin_url = f"{self.base_url}/linkedin-feed.xml"

        return json.dumps({
            "success": True,
            "job_id": job_id,
            "message": f"'{title}' added. Total jobs in feed: {len(_JOB_STORE)}.",
            "indeed_feed": indeed_url,
            "linkedin_feed": linkedin_url,
            "note": (
                "Jobs appear on Indeed within 24-48h and LinkedIn within 6h "
                "after their feeds are registered (one-time setup)."
            ),
        })

    def list_jobs(self) -> str:
        """List all active jobs in the feed.

        Returns:
            JSON list of all jobs currently in both feeds.
        """
        return json.dumps({
            "success": True,
            "count": len(_JOB_STORE),
            "jobs": [
                {
                    "id": j["id"],
                    "title": j["title"],
                    "company": j["company"],
                    "location": j["location"],
                    "job_type": j["job_type"],
                    "posted_at": j["posted_at"],
                }
                for j in _JOB_STORE
            ],
        })

    def remove_job(self, job_id: str) -> str:
        """Remove a job from both feeds (disappears on next crawl).

        Args:
            job_id: The job reference ID to remove.

        Returns:
            JSON confirming removal.
        """
        global _JOB_STORE
        before = len(_JOB_STORE)
        _JOB_STORE = [j for j in _JOB_STORE if j["id"] != job_id]
        if before - len(_JOB_STORE) > 0:
            return json.dumps({"success": True, "message": f"Job {job_id} removed from both feeds."})
        return json.dumps({"success": False, "error": f"Job ID '{job_id}' not found."})

    def get_feed_urls(self) -> str:
        """Get both feed URLs and one-time setup instructions.

        Returns:
            JSON with feed URLs and registration instructions for Indeed and LinkedIn.
        """
        return json.dumps({
            "indeed_feed_url": f"{self.base_url}/indeed-feed.xml",
            "linkedin_feed_url": f"{self.base_url}/linkedin-feed.xml",
            "indeed_setup": (
                "ONE-TIME: Go to https://employers.indeed.com/jobs/feed-submit "
                f"and submit: {self.base_url}/indeed-feed.xml"
            ),
            "linkedin_setup": (
                "ONE-TIME: Go to https://www.linkedin.com/talent/job-wrapping "
                f"and submit: {self.base_url}/linkedin-feed.xml — "
                "You'll need your LinkedIn Page numeric Company ID."
            ),
            "jobs_in_feed": len(_JOB_STORE),
        })

    # ------------------------------------------------------------------
    # XML generation (used by FastAPI endpoints, not agent tools)
    # ------------------------------------------------------------------

    def build_indeed_xml(self) -> str:
        """Generate Indeed-compliant XML feed string."""
        source = ET.Element("source")

        publisher = ET.SubElement(source, "publisher")
        publisher.text = _JOB_STORE[0]["company"] if _JOB_STORE else "Company"

        publish_date = ET.SubElement(source, "publishDate")
        publish_date.text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        for job in _JOB_STORE:
            j = ET.SubElement(source, "job")

            _t(j, "title", job["title"])
            _t(j, "date", datetime.fromisoformat(job["posted_at"]).strftime("%a, %d %b %Y %H:%M:%S +0000"))
            _t(j, "referencenumber", job["id"])
            _t(j, "url", job["apply_url"])
            _t(j, "company", job["company"])

            parts = [p.strip() for p in job["location"].split(",")]
            _t(j, "city", parts[0] if parts else job["location"])
            _t(j, "state", parts[1] if len(parts) > 2 else "")
            _t(j, "country", parts[-1] if len(parts) > 1 else "Thailand")

            _t(j, "description", job["description"])

            # Map FULL_TIME → Full-time for Indeed
            jtype_map = {
                "FULL_TIME": "Full-time", "PART_TIME": "Part-time",
                "CONTRACT": "Contract", "INTERNSHIP": "Internship", "VOLUNTEER": "Volunteer",
            }
            _t(j, "jobtype", jtype_map.get(job["job_type"], job["job_type"]))

            if job.get("salary_min") or job.get("salary_max"):
                lo = job.get("salary_min", "")
                hi = job.get("salary_max", "")
                currency = job.get("salary_currency", "THB")
                _t(j, "salary", f"{lo} - {hi} {currency}/month" if lo and hi else f"{lo or hi} {currency}/month")

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(source, encoding="unicode")

    def build_linkedin_xml(self) -> str:
        """Generate LinkedIn-compliant XML feed string."""
        source = ET.Element("source")

        _t(source, "lastBuildDate", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"))
        _t(source, "publisherUrl", self.base_url or "https://example.com")
        _t(source, "publisher", _JOB_STORE[0]["company"] if _JOB_STORE else "Company")
        _t(source, "expectedJobCount", str(len(_JOB_STORE)))

        for job in _JOB_STORE:
            j = ET.SubElement(source, "job")

            _cdata(j, "partnerJobId", job["id"])
            _cdata(j, "company", job["company"])
            _cdata(j, "title", job["title"])
            _cdata(j, "description", job["description"])
            _cdata(j, "applyUrl", job["apply_url"])
            _cdata(j, "location", job["location"])

            # Parse city / country for LinkedIn
            parts = [p.strip() for p in job["location"].split(",")]
            _cdata(j, "city", parts[0] if parts else job["location"])
            _cdata(j, "country", _country_code(parts[-1] if len(parts) > 1 else "Thailand"))

            _cdata(j, "jobtype", job["job_type"])  # LinkedIn uses FULL_TIME etc.
            _cdata(j, "experienceLevel", job.get("experience_level", "MID_SENIOR_LEVEL"))
            _cdata(j, "workplaceTypes", job.get("workplace_type", "On-site"))
            _cdata(j, "listDate", job["list_date"])
            _cdata(j, "posterEmail", self.poster_email or "hr@company.com")
            _cdata(j, "jobPostingAvailability", "PUBLIC")

            if self.linkedin_company_id:
                _cdata(j, "companyId", self.linkedin_company_id)

            if job.get("salary_min") or job.get("salary_max"):
                salaries = ET.SubElement(j, "salaries")
                salary = ET.SubElement(salaries, "salary")
                if job.get("salary_max"):
                    high = ET.SubElement(salary, "highEnd")
                    _cdata(high, "amount", str(job["salary_max"]))
                    _cdata(high, "currencyCode", job.get("salary_currency", "THB"))
                if job.get("salary_min"):
                    low = ET.SubElement(salary, "lowEnd")
                    _cdata(low, "amount", str(job["salary_min"]))
                    _cdata(low, "currencyCode", job.get("salary_currency", "THB"))
                _cdata(salary, "period", "MONTHLY")
                _cdata(salary, "type", "BASE_SALARY")

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(source, encoding="unicode")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _t(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Add a plain text child element."""
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _cdata(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Add a CDATA-wrapped child element (LinkedIn requirement)."""
    el = ET.SubElement(parent, tag)
    # ElementTree doesn't support CDATA natively — we post-process in build methods
    el.text = f"__CDATA__{text}__ENDCDATA__"
    return el


def _country_code(country_name: str) -> str:
    """Map country name to ISO 2-letter code."""
    mapping = {
        "thailand": "TH", "united states": "US", "usa": "US",
        "united kingdom": "GB", "uk": "GB", "singapore": "SG",
        "malaysia": "MY", "indonesia": "ID", "vietnam": "VN",
    }
    return mapping.get(country_name.lower().strip(), country_name[:2].upper())


# Singleton instance (shared across provider calls in the same process)
_FEED_INSTANCE: Optional[JobFeedTools] = None


def get_feed_instance(base_url: str = "", poster_email: str = "", linkedin_company_id: str = "") -> JobFeedTools:
    """Return (or create) the singleton JobFeedTools instance."""
    global _FEED_INSTANCE
    if _FEED_INSTANCE is None:
        _FEED_INSTANCE = JobFeedTools(
            base_url=base_url,
            poster_email=poster_email,
            linkedin_company_id=linkedin_company_id,
        )
    return _FEED_INSTANCE
