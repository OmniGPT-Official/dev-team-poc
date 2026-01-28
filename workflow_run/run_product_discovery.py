#!/usr/bin/env python3
"""
Product Discovery Workflow Runner

Simple script to run the product discovery workflow from command line or programmatically.

Command Line Usage:
    python workflows/run_product_discovery.py \
        --product-name "AI Email Assistant" \
        --product-context "Helps sales teams write personalized follow-up emails" \
        --target-audience "B2B sales representatives"

Programmatic Usage:
    from workflows.run_product_discovery import run_discovery

    prd_path = run_discovery(
        product_name="AI Email Assistant",
        product_context="Helps sales teams write personalized follow-up emails",
        target_audience="B2B sales representatives"
    )
"""

import sys
import os
from typing import Optional
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.product_discovery_workflow import (
    product_discovery_workflow,
    ProductDiscoveryInput,
    run_product_discovery
)


def run_discovery(
    product_name: str,
    product_context: str,
    target_audience: Optional[str] = None,
    user_prompt: Optional[str] = None,
    include_competitor_analysis: bool = True,
    stream: bool = True
) -> str:
    """
    Run the product discovery workflow.

    Args:
        product_name: Name of the product/feature
        product_context: What needs to be built
        target_audience: Who will use it
        user_prompt: Original user request
        include_competitor_analysis: Include competitor analysis
        stream: Stream the output to console

    Returns:
        str: Path to generated PRD file
    """
    logger.info("="*70)
    logger.info("PRODUCT DISCOVERY WORKFLOW")
    logger.info("="*70)
    logger.info(f"Product: {product_name}")
    logger.info(f"Context: {product_context}")
    logger.info(f"Target Audience: {target_audience or 'Not specified'}")
    logger.info(f"Competitor Analysis: {'Enabled' if include_competitor_analysis else 'Disabled'}")
    logger.info("="*70)
    logger.info("")

    # Create workflow input
    workflow_input = ProductDiscoveryInput(
        product_name=product_name,
        product_context=product_context,
        target_audience=target_audience,
        user_prompt=user_prompt,
        include_competitor_analysis=include_competitor_analysis
    )

    # Run workflow
    if stream:
        logger.info("Starting workflow (streaming output)...\n")
        result = product_discovery_workflow.print_response(input=workflow_input)
    else:
        logger.info("Starting workflow...\n")
        result = product_discovery_workflow.run(input=workflow_input)

    logger.info("\n" + "="*70)
    logger.info("WORKFLOW COMPLETED!")
    logger.info("="*70)

    # Extract file path
    if hasattr(result, 'content') and "PRD saved to:" in result.content:
        filepath = result.content.split("`")[-2]
        logger.info(f"PRD saved to: {filepath}")
        return filepath
    elif isinstance(result, str) and "PRD saved to:" in result:
        filepath = result.split("`")[-2]
        logger.info(f"PRD saved to: {filepath}")
        return filepath
    else:
        logger.warning("Could not extract file path from result")
        return str(result)


def interactive_mode():
    """
    Run in interactive mode - asks user for input.
    """
    print("\n" + "="*70)
    print("PRODUCT DISCOVERY WORKFLOW - INTERACTIVE MODE")
    print("="*70)
    print("\nThis workflow will help you create a comprehensive PRD with market research.")
    print("Answer the following questions:\n")

    # Gather inputs
    product_name = input("Product/Feature Name: ").strip()
    if not product_name:
        print("Error: Product name is required!")
        sys.exit(1)

    product_context = input("What needs to be built? (Description): ").strip()
    if not product_context:
        print("Error: Product context is required!")
        sys.exit(1)

    target_audience = input("Who will use this? (Optional, press Enter to skip): ").strip()

    user_prompt = input("Original user request? (Optional, press Enter to skip): ").strip()

    competitor_input = input("Include competitor analysis? (Y/n): ").strip().lower()
    include_competitor_analysis = competitor_input != 'n'

    print("\n" + "="*70)
    print("Starting Product Discovery...")
    print("="*70 + "\n")

    # Run workflow
    run_discovery(
        product_name=product_name,
        product_context=product_context,
        target_audience=target_audience or None,
        user_prompt=user_prompt or None,
        include_competitor_analysis=include_competitor_analysis,
        stream=True
    )


def main():
    """
    Main entry point for command line usage.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Product Discovery Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Basic usage
  python workflows/run_product_discovery.py \\
      --product-name "AI Email Assistant" \\
      --product-context "Helps sales teams write personalized follow-up emails"

  # With target audience
  python workflows/run_product_discovery.py \\
      --product-name "AI Email Assistant" \\
      --product-context "Helps sales teams write personalized follow-up emails" \\
      --target-audience "B2B sales representatives"

  # Skip competitor analysis
  python workflows/run_product_discovery.py \\
      --product-name "Feature X" \\
      --product-context "Add dark mode to the app" \\
      --skip-competitors

  # Interactive mode
  python workflows/run_product_discovery.py --interactive
        """
    )

    parser.add_argument(
        "--product-name",
        help="Name of the product/feature"
    )
    parser.add_argument(
        "--product-context",
        help="Description of what needs to be built"
    )
    parser.add_argument(
        "--target-audience",
        help="Who will use this product/feature"
    )
    parser.add_argument(
        "--user-prompt",
        help="Original user request (for context)"
    )
    parser.add_argument(
        "--skip-competitors",
        action="store_true",
        help="Skip competitor analysis"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Don't stream output to console"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode (asks for input)"
    )

    args = parser.parse_args()

    # Interactive mode
    if args.interactive:
        interactive_mode()
        return

    # Validate required arguments
    if not args.product_name or not args.product_context:
        parser.error("--product-name and --product-context are required (or use --interactive)")

    # Run workflow
    run_discovery(
        product_name=args.product_name,
        product_context=args.product_context,
        target_audience=args.target_audience,
        user_prompt=args.user_prompt,
        include_competitor_analysis=not args.skip_competitors,
        stream=not args.no_stream
    )


if __name__ == "__main__":
    main()
