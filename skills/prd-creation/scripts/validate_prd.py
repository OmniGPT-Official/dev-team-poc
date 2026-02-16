#!/usr/bin/env python3
"""
PRD Validation Script

Validates that a PRD document contains all required sections and meets quality standards.
Can be called by agents to check PRD completeness before finalizing.

Usage:
    python validate_prd.py <prd_file_path>
    python validate_prd.py --content "<prd_content>"
"""

import sys
import re
from typing import Dict, List, Tuple


class PRDValidator:
    """Validates PRD documents for completeness and quality."""

    # Required sections for a PRD
    REQUIRED_SECTIONS = [
        "DOCUMENT TYPE",
        "PROJECT TYPE",
        "PROJECT ID",
        "PROJECT NAME",
        "EXECUTIVE SUMMARY",
        "PROBLEM STATEMENT",
        "TARGET USERS",
        "PRODUCT VISION",
        "GOALS & SUCCESS METRICS",
        "FEATURE REQUIREMENTS - P0",
        "USER FLOW",
        "CONTENT & ASSETS",
        "TECHNICAL CONSIDERATIONS",
        "OUT OF SCOPE",
    ]

    # Optional but recommended sections
    RECOMMENDED_SECTIONS = [
        "COMPETITIVE ANALYSIS",
        "ASSUMPTIONS MADE",
        "RESEARCH INSIGHTS",
        "BUSINESS MODEL",
        "TIMELINE & MILESTONES",
    ]

    def __init__(self, content: str):
        self.content = content
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate(self) -> Dict:
        """Run all validation checks."""
        self._check_header()
        self._check_required_sections()
        self._check_recommended_sections()
        self._check_section_content()
        self._check_links_preserved()
        self._check_assumptions_documented()

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "score": self._calculate_score(),
        }

    def _check_header(self):
        """Validate PRD header format."""
        header_pattern = r"DOCUMENT TYPE:\s*Product Requirements Document"
        if not re.search(header_pattern, self.content, re.IGNORECASE):
            self.errors.append("Missing or incorrect DOCUMENT TYPE header")

        required_header_fields = ["PROJECT TYPE", "PROJECT ID", "PROJECT NAME"]
        for field in required_header_fields:
            if not re.search(f"{field}:", self.content, re.IGNORECASE):
                self.errors.append(f"Missing {field} in document header")

    def _check_required_sections(self):
        """Check that all required sections are present."""
        for section in self.REQUIRED_SECTIONS:
            # Allow for variations in section formatting
            pattern = f"(?:^|\\n)#{{{1,3}}}?\\s*{re.escape(section)}"
            if not re.search(pattern, self.content, re.IGNORECASE | re.MULTILINE):
                # Also check for non-markdown heading (plain text)
                alt_pattern = f"(?:^|\\n){re.escape(section)}\\s*(?:\\n|$)"
                if not re.search(alt_pattern, self.content, re.IGNORECASE | re.MULTILINE):
                    self.errors.append(f"Missing required section: {section}")

    def _check_recommended_sections(self):
        """Check for recommended sections."""
        for section in self.RECOMMENDED_SECTIONS:
            pattern = f"(?:^|\\n)#{{{1,3}}}?\\s*{re.escape(section)}"
            if not re.search(pattern, self.content, re.IGNORECASE | re.MULTILINE):
                alt_pattern = f"(?:^|\\n){re.escape(section)}\\s*(?:\\n|$)"
                if not re.search(alt_pattern, self.content, re.IGNORECASE | re.MULTILINE):
                    self.warnings.append(f"Missing recommended section: {section}")

    def _check_section_content(self):
        """Check that sections have actual content (not just headings)."""
        # Find all sections and check for content
        sections = re.finditer(
            r"(?:^|\n)(#{1,3}|)([A-Z][A-Z\s&-]+)(?:\n|$)(.*?)(?=(?:^|\n)(?:#{1,3}|)[A-Z][A-Z\s&-]+(?:\n|$)|$)",
            self.content,
            re.MULTILINE | re.DOTALL
        )

        empty_sections = []
        for match in sections:
            section_name = match.group(2).strip()
            section_content = match.group(3).strip()

            # Check if section is in required list and has minimal content
            if section_name.upper() in [s.upper() for s in self.REQUIRED_SECTIONS]:
                if len(section_content) < 50:  # Less than 50 chars is likely empty
                    empty_sections.append(section_name)

        if empty_sections:
            self.warnings.append(f"Sections with minimal content: {', '.join(empty_sections)}")

    def _check_links_preserved(self):
        """Check if document contains user-provided links."""
        # Check for URLs in CONTENT & ASSETS section
        content_section_match = re.search(
            r"CONTENT\s*&\s*ASSETS.*?(?=(?:^|\n)(?:#{1,3}|)[A-Z][A-Z\s&-]+(?:\n|$)|$)",
            self.content,
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        if content_section_match:
            section_text = content_section_match.group(0)
            # Count URLs in the section
            urls = re.findall(r'https?://[^\s]+', section_text)
            if urls:
                self.info.append(f"Found {len(urls)} links in CONTENT & ASSETS section")
            else:
                self.warnings.append(
                    "No links found in CONTENT & ASSETS section. "
                    "If user provided any links (images, fonts, social media, etc.), they should be included."
                )

    def _check_assumptions_documented(self):
        """Check if assumptions are documented when present."""
        # Look for phrases indicating assumptions were made
        assumption_indicators = [
            r"assume",
            r"not sure",
            r"unclear",
            r"to be determined",
            r"tbd",
        ]

        has_assumption_indicators = any(
            re.search(pattern, self.content, re.IGNORECASE)
            for pattern in assumption_indicators
        )

        has_assumptions_section = re.search(
            r"ASSUMPTIONS?\s*(?:MADE)?",
            self.content,
            re.IGNORECASE
        )

        if has_assumption_indicators and not has_assumptions_section:
            self.warnings.append(
                "Document contains assumption indicators but no ASSUMPTIONS section. "
                "Consider adding an ASSUMPTIONS MADE section to document what was inferred."
            )

    def _calculate_score(self) -> int:
        """Calculate PRD quality score (0-100)."""
        # Start with 100
        score = 100

        # Deduct for errors (critical)
        score -= len(self.errors) * 15

        # Deduct for warnings (moderate)
        score -= len(self.warnings) * 5

        # Ensure score doesn't go below 0
        return max(0, score)

    def print_report(self):
        """Print validation report."""
        print("=" * 60)
        print("PRD VALIDATION REPORT")
        print("=" * 60)

        if self.errors:
            print("\n❌ ERRORS (must fix):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS (should fix):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.info:
            print("\nℹ️  INFO:")
            for info in self.info:
                print(f"  - {info}")

        score = self._calculate_score()
        print(f"\n📊 QUALITY SCORE: {score}/100")

        if score >= 90:
            print("✅ Excellent PRD quality!")
        elif score >= 70:
            print("🟡 Good PRD, but some improvements recommended")
        elif score >= 50:
            print("🟠 PRD needs improvements")
        else:
            print("🔴 PRD has significant issues that must be addressed")

        print("=" * 60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_prd.py <prd_file_path>")
        print("   or: python validate_prd.py --content '<prd_content>'")
        sys.exit(1)

    # Get content from file or command line
    if sys.argv[1] == "--content":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    # Validate PRD
    validator = PRDValidator(content)
    result = validator.validate()
    validator.print_report()

    # Exit with error code if validation failed
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
