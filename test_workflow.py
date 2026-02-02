"""
Quick test script for Product Discovery Workflow
"""

from workflows.product_discovery_workflow import discovery_and_requirements_workflow

print("Testing Product Discovery Workflow\n")

print("=" * 60)
print("TEST: Simple Feature Request")
print("=" * 60)

# Workflows take a simple string input
request = """
Product: Export to CSV Button
Context: Add a button to export dashboard data to CSV format
Scope: Feature enhancement
"""

result = discovery_and_requirements_workflow.run(input=request)
print(f"\nResult:\n{result.content}\n")

print("\nWorkflow test completed!")
