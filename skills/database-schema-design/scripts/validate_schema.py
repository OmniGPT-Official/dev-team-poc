#!/usr/bin/env python3
"""
Database Schema Validation Script

Validates SQL schema files for Supabase best practices.

Usage:
    python validate_schema.py <schema.sql>
    python validate_schema.py --content "<sql_content>"
"""

import sys
import re
from typing import List, Dict


class SchemaValidator:
    """Validates database schema files."""

    def __init__(self, content: str):
        self.content = content
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.tables: List[str] = []

    def validate(self) -> Dict:
        """Run all validation checks."""
        self._extract_tables()
        self._check_primary_keys()
        self._check_timestamps()
        self._check_foreign_key_indexes()
        self._check_rls_enabled()
        self._check_rls_policies()
        self._check_data_types()

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "score": self._calculate_score(),
        }

    def _extract_tables(self):
        """Extract table names from SQL."""
        # Match CREATE TABLE statements
        pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)"
        matches = re.finditer(pattern, self.content, re.IGNORECASE)
        self.tables = [match.group(1) for match in matches]
        self.info.append(f"Found {len(self.tables)} tables: {', '.join(self.tables)}")

    def _check_primary_keys(self):
        """Check that tables use UUID primary keys."""
        for table in self.tables:
            # Skip auth schema tables
            if table.startswith('auth.'):
                continue

            # Find table definition
            table_pattern = f"CREATE\\s+TABLE.*?{table}.*?\\((.*?)\\);"
            table_match = re.search(table_pattern, self.content, re.IGNORECASE | re.DOTALL)

            if table_match:
                table_def = table_match.group(1)

                # Check for UUID primary key
                if not re.search(r"id\s+UUID\s+PRIMARY\s+KEY", table_def, re.IGNORECASE):
                    self.warnings.append(
                        f"Table '{table}': Consider using UUID for primary key "
                        "(id UUID PRIMARY KEY DEFAULT gen_random_uuid())"
                    )

                # Check for gen_random_uuid()
                if re.search(r"id\s+UUID\s+PRIMARY\s+KEY", table_def, re.IGNORECASE):
                    if not re.search(r"DEFAULT\s+gen_random_uuid\(\)", table_def, re.IGNORECASE):
                        self.warnings.append(
                            f"Table '{table}': UUID primary key should have DEFAULT gen_random_uuid()"
                        )

    def _check_timestamps(self):
        """Check for created_at and updated_at columns."""
        for table in self.tables:
            if table.startswith('auth.'):
                continue

            table_pattern = f"CREATE\\s+TABLE.*?{table}.*?\\((.*?)\\);"
            table_match = re.search(table_pattern, self.content, re.IGNORECASE | re.DOTALL)

            if table_match:
                table_def = table_match.group(1)

                # Check for created_at
                if not re.search(r"created_at\s+TIMESTAMPTZ", table_def, re.IGNORECASE):
                    self.warnings.append(
                        f"Table '{table}': Missing created_at TIMESTAMPTZ DEFAULT NOW()"
                    )

                # Check for updated_at
                if not re.search(r"updated_at\s+TIMESTAMPTZ", table_def, re.IGNORECASE):
                    self.warnings.append(
                        f"Table '{table}': Missing updated_at TIMESTAMPTZ DEFAULT NOW()"
                    )

    def _check_foreign_key_indexes(self):
        """Check that foreign keys have indexes."""
        # Find all foreign key columns
        fk_pattern = r"(\w+)\s+UUID.*?REFERENCES\s+(\w+)"
        fk_matches = re.finditer(fk_pattern, self.content, re.IGNORECASE)

        foreign_keys = []
        for match in fk_matches:
            column_name = match.group(1)
            foreign_keys.append(column_name)

        # Check for indexes on foreign key columns
        for fk_column in foreign_keys:
            index_pattern = f"CREATE\\s+INDEX.*?ON.*?\\({fk_column}\\)"
            if not re.search(index_pattern, self.content, re.IGNORECASE):
                self.warnings.append(
                    f"Missing index on foreign key column '{fk_column}'. "
                    f"Add: CREATE INDEX idx_tablename_{fk_column} ON tablename({fk_column});"
                )

    def _check_rls_enabled(self):
        """Check that RLS is enabled on tables."""
        for table in self.tables:
            if table.startswith('auth.'):
                continue

            # Check for ALTER TABLE ... ENABLE ROW LEVEL SECURITY
            rls_pattern = f"ALTER\\s+TABLE\\s+{table}\\s+ENABLE\\s+ROW\\s+LEVEL\\s+SECURITY"
            if not re.search(rls_pattern, self.content, re.IGNORECASE):
                self.warnings.append(
                    f"Table '{table}': RLS not enabled. "
                    f"Add: ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
                )

    def _check_rls_policies(self):
        """Check for RLS policies."""
        for table in self.tables:
            if table.startswith('auth.'):
                continue

            # Check if table has RLS enabled
            rls_pattern = f"ALTER\\s+TABLE\\s+{table}\\s+ENABLE\\s+ROW\\s+LEVEL\\s+SECURITY"
            if re.search(rls_pattern, self.content, re.IGNORECASE):
                # Check for at least one policy
                policy_pattern = f"CREATE\\s+POLICY.*?ON\\s+{table}"
                if not re.search(policy_pattern, self.content, re.IGNORECASE):
                    self.errors.append(
                        f"Table '{table}': RLS enabled but no policies defined. "
                        f"Add policies for SELECT, INSERT, UPDATE, DELETE."
                    )

    def _check_data_types(self):
        """Check for deprecated or inefficient data types."""
        # Check for VARCHAR (should use TEXT)
        if re.search(r"VARCHAR\(\d+\)", self.content, re.IGNORECASE):
            self.info.append(
                "Found VARCHAR type. Consider using TEXT instead (no performance difference in PostgreSQL)"
            )

        # Check for JSON (should use JSONB)
        if re.search(r"\s+JSON\s+", self.content, re.IGNORECASE):
            self.warnings.append(
                "Found JSON type. Consider using JSONB for better performance and indexing"
            )

        # Check for SERIAL (should use UUID)
        if re.search(r"SERIAL|BIGSERIAL", self.content, re.IGNORECASE):
            self.warnings.append(
                "Found SERIAL type. Consider using UUID PRIMARY KEY DEFAULT gen_random_uuid() instead"
            )

    def _calculate_score(self) -> int:
        """Calculate schema quality score."""
        score = 100
        score -= len(self.errors) * 20
        score -= len(self.warnings) * 5
        return max(0, score)

    def print_report(self):
        """Print validation report."""
        print("=" * 60)
        print("DATABASE SCHEMA VALIDATION REPORT")
        print("=" * 60)

        if self.info:
            print("\nℹ️  INFO:")
            for info in self.info:
                print(f"  - {info}")

        if self.errors:
            print("\n❌ ERRORS (must fix):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS (should fix):")
            for warning in self.warnings:
                print(f"  - {warning}")

        score = self._calculate_score()
        print(f"\n📊 QUALITY SCORE: {score}/100")

        if score >= 90:
            print("✅ Excellent schema quality!")
        elif score >= 70:
            print("🟡 Good schema, but some improvements recommended")
        elif score >= 50:
            print("🟠 Schema needs improvements")
        else:
            print("🔴 Schema has significant issues")

        print("=" * 60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_schema.py <schema.sql>")
        print("   or: python validate_schema.py --content '<sql_content>'")
        sys.exit(1)

    # Get content
    if sys.argv[1] == "--content":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        try:
            with open(sys.argv[1], 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Validate
    validator = SchemaValidator(content)
    result = validator.validate()
    validator.print_report()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
