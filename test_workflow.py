"""
Quick test script for Product Discovery Workflow
"""

from workflows.product_discovery_workflow import run_discovery_and_requirements

print("🚀 Testing Product Discovery Workflow\n")

# Test 1: Simple feature (no research)
print("=" * 60)
print("TEST 1: Simple Feature (No Research)")
print("=" * 60)

result = run_discovery_and_requirements(
    product_name="Export to CSV Button",
    product_context="Add a button to export dashboard data to CSV format",
    scope="feature",
    enable_research=False,
    enable_competitor_analysis=False
)

print(f"\n✅ Feature document created: {result}\n")

# Test 2: Product with research (uncomment to test)
# print("=" * 60)
# print("TEST 2: Product from Scratch (With Research)")
# print("=" * 60)
#
# result = run_discovery_and_requirements(
#     product_name="Team Collaboration Tool",
#     product_context="Real-time collaboration tool for remote teams",
#     target_audience="Remote software development teams",
#     scope="product",
#     enable_research=True,
#     enable_competitor_analysis=True
# )
#
# print(f"\n✅ Product PRD created: {result}\n")

print("\n🎉 Workflow test completed!")
