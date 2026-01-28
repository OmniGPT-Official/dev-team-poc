"""
Code Review Workflow

This workflow orchestrates the code review process performed by the Lead Engineer.
It reviews code, identifies changes, makes approval decisions, and optionally updates architecture docs.
"""

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.workflow.condition import Condition
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow


# === REVIEW AGENTS ===

review_agent = Agent(
    name="Code Reviewer",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You are an expert code reviewer. Your task is to:

1. REVIEW CODE STRUCTURE:
   - Analyze the code organization and file structure
   - Check naming conventions and code style consistency
   - Evaluate modularity and separation of concerns
   - Assess code readability and documentation

2. ARCHITECTURE ALIGNMENT:
   - Compare implementation against the architecture document (if provided)
   - Check if design patterns are correctly applied
   - Verify API contracts and interfaces match specifications
   - Ensure data flow follows the documented architecture

Output your findings as a structured review with:
- **Structure Analysis**: Code organization findings
- **Architecture Alignment**: How well it matches the architecture doc
- **Quality Assessment**: Overall code quality observations""",
)

identify_agent = Agent(
    name="Change Identifier",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You are an expert at identifying code improvements. Based on the code review provided, you must:

1. IDENTIFY NECESSARY CHANGES (Must Fix):
   - Security vulnerabilities
   - Bugs or logic errors
   - Breaking changes to existing functionality
   - Performance issues that impact user experience
   - Missing error handling for critical paths

2. IDENTIFY OPTIONAL IMPROVEMENTS (Nice to Have):
   - Code style improvements
   - Additional test coverage suggestions
   - Documentation enhancements
   - Minor refactoring opportunities
   - Performance optimizations for non-critical paths

Output your findings as:
- **Necessary Changes**: List each required change with severity (Critical/High/Medium)
- **Optional Improvements**: List each suggestion with impact level (High/Medium/Low)
- **Summary**: Brief overview of changes needed""",
)

decision_agent = Agent(
    name="Review Decision Maker",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You are the final decision maker for code reviews. Based on the identified changes, you must:

1. EVALUATE the necessary changes:
   - If there are Critical or High severity necessary changes -> CHANGES_REQUESTED
   - If there are only Medium severity changes that are minor -> Consider APPROVED with notes
   - If there are no necessary changes -> APPROVED

2. PROVIDE a clear decision with:
   - **review_status**: Either "approved" or "changes_requested"
   - **review_notes**: Detailed notes explaining the decision
   - **action_items**: Specific items the developer needs to address (if any)

Be fair but thorough. Approve good code, but don't let issues slip through.""",
)

architecture_update_agent = Agent(
    name="Architecture Doc Updater",
    model=Claude(id="claude-sonnet-4-5"),
    instructions="""You update architecture documentation when implementation intentionally diverges from the original design.

Only propose updates when:
1. The implementation is correct but differs from the documented architecture
2. The divergence was intentional (better approach discovered during implementation)
3. The change should be reflected in the architecture for future reference

Output:
- **architecture_updates**: List of specific documentation changes needed
- **rationale**: Why the implementation diverged and why it's acceptable
- **no_updates_needed**: True if the architecture doc is still accurate""",
)


# === WORKFLOW STEPS ===

review_step = Step(
    name="review",
    description="Review code structure and architecture alignment",
    agent=review_agent,
)

identify_step = Step(
    name="identify",
    description="Identify necessary changes and optional improvements",
    agent=identify_agent,
)

decision_step = Step(
    name="decide",
    description="Make approval decision based on identified issues",
    agent=decision_agent,
)

update_architecture_step = Step(
    name="update_architecture",
    description="Update architecture docs if implementation intentionally diverged",
    agent=architecture_update_agent,
)


# === CONDITION EVALUATOR ===

def needs_architecture_update(step_input: StepInput) -> bool:
    """
    Determine if architecture documentation needs to be updated.
    This happens when implementation intentionally diverged from the original design.
    """
    content = step_input.previous_step_content or ""
    content_lower = content.lower()

    # Check for indicators that architecture docs might need updating
    divergence_indicators = [
        "diverged from architecture",
        "different approach",
        "implementation differs",
        "architecture update needed",
        "design changed",
        "modified the architecture",
        "updated approach",
        "better pattern",
        "refactored to",
        "intentionally changed",
    ]

    return any(indicator in content_lower for indicator in divergence_indicators)


# === OUTPUT FORMATTER ===

def format_review_output(step_input: StepInput) -> StepOutput:
    """
    Format the final output of the code review workflow.
    Extracts key information and structures it consistently.
    """
    content = step_input.previous_step_content or ""

    # Determine review status from the content
    status = "changes_requested"
    if "approved" in content.lower() and "changes_requested" not in content.lower():
        status = "approved"
    elif '"review_status": "approved"' in content.lower():
        status = "approved"

    formatted_output = f"""
## Code Review Complete

**Review Status**: `{status}`

### Review Details
{content}

---
*Code review performed by Lead Engineer workflow*
"""

    return StepOutput(content=formatted_output)


# === CODE REVIEW WORKFLOW ===

code_review_workflow = Workflow(
    name="Code Review Workflow",
    stream=False,
    description="""Lead Engineer code review workflow that:
    1. Reviews code structure and architecture alignment
    2. Identifies necessary changes and optional improvements
    3. Decides to approve or request changes
    4. Optionally updates architecture docs if implementation diverged intentionally

    Outputs: review_status (approved | changes_requested), review_notes, architecture_updates (optional)""",
    steps=[
        review_step,
        identify_step,
        decision_step,
        Condition(
            name="architecture_update_condition",
            description="Check if architecture documentation needs updating",
            evaluator=needs_architecture_update,
            steps=[update_architecture_step],
        ),
        format_review_output,
    ],
)


