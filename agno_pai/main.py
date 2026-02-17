"""
Agno PAI — Entry point for the factory meta-agent.

Usage:
    # Single request
    python -m agno_pai "build me an agent that reads Gmail and creates Notion tasks"

    # Interactive mode (chat with the factory)
    python -m agno_pai
"""

import sys

from agno_pai.factory import factory_agent

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║              🏭  A G N O  F A C T O R Y                     ║
║     Describe what you need — I'll build the Agno code.      ║
╚══════════════════════════════════════════════════════════════╝

Examples:
  "build me an agent that reads Gmail and sends Slack notifications"
  "create a team that researches topics and writes blog posts"
  "make a workflow that processes a CSV and emails a summary"

Type 'exit' or Ctrl+C to quit.
"""


def main():
    if len(sys.argv) > 1:
        # Single request mode: python -m agno_pai "build me X"
        request = " ".join(sys.argv[1:])
        print(f"\n🏭 Agno Factory\n{'═' * 60}")
        print(f"Request: {request}")
        print('═' * 60 + "\n")
        factory_agent.print_response(request, stream=True)
    else:
        # Interactive mode
        print(BANNER)
        factory_agent.cli_app(markdown=True)


if __name__ == "__main__":
    main()
