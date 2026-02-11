"""Content Creation Team - A team for creating content with strategist, writer, and image generator."""

from agno.agent import Agent
from agno.models.google import Gemini
from agno.team import Team
from agno.tools.openai import OpenAITools
# from agno.tools.reasoning import ReasoningTools
from agno.tools.workflow import WorkflowTools
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow

from db import db

# Setup Content Creation Team agents
content_strategist = Agent(
    name="Content Strategist",
    model=Gemini(id="gemini-3-flash-preview"),
    description="Analyzes content requirements, identifies target audience, and develops content strategy. Asks clarifying questions to understand the content goals and scope.",
    instructions=[
        "You are a Content Strategist who helps plan and strategize content creation.",
        "",
        "## Requirements Gathering",
        "When gathering requirements, ask about these 5 key areas:",
        "1. BRANDING: Brand identity, guidelines, colors, fonts, style",
        "2. AUDIENCE: Target audience demographics, interests, pain points",
        "3. PLATFORM: Which platform(s) the content is for",
        "4. TONE: Desired tone (professional, casual, playful, etc.)",
        "5. GOAL: Content goal (engagement, awareness, sales, education)",
        "",
        "Note: User can upload a file if they already have this information.",
        "",
        "## Strategy Development",
        "Create a content brief that guides the writing process.",
        "Consider SEO, engagement, and the purpose of the content.",
        "Identify key messages and content structure.",
    ],
    db=db,
    # enable_session_summaries=True,
    update_memory_on_run=False,
    add_history_to_context=True,
    # num_history_runs=3,
    # num_history_messages=10,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
    debug_mode=False,
)

content_writer = Agent(
    name="Content Writer",
    model=Gemini(id="gemini-3-flash-preview"),
    description="Writes articles, blog posts, social media content, and other written materials based on the content strategy and requirements.",
    instructions=[
        "You are a Content Writer who creates engaging written content.",
        "Write articles, blog posts, social media posts, and other content as requested.",
        "Follow the content brief and strategy provided.",
        "Ensure the writing matches the target audience and tone.",
        "Structure content with clear headings, paragraphs, and flow.",
    ],
    db=db,
    # enable_session_summaries=True,
    update_memory_on_run=False,
    add_history_to_context=True,
    # num_history_runs=3,
    # num_history_messages=10,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
    debug_mode=False,
)

# image_generator = Agent(
#     name="Image Generator",
#     model=Gemini(id="gemini-3-flash-preview"),
#     description="Generates images using OpenAI's image generation and manages visual assets for content. Creates high-quality images to enhance content.",
#     instructions=[
#         "You are an Image Generator who creates visual assets using OpenAI's image generation.",
#         "",
#         "## CRITICAL: Always Use Image Generation Tool",
#         "When asked to generate, create, or make an image, you MUST:",
#         "1. ALWAYS call the image generation tool - never skip this step",
#         "2. NEVER describe, imagine, or pretend to generate an image without actually calling the tool",
#         "3. NEVER respond with text descriptions of what an image would look like",
#         "4. If the tool call fails, report the error - do not pretend it succeeded",
#         "",
#         "## Image Generation Guidelines",
#         "Use the image generation tool to create high-quality, photorealistic images that complement the content.",
#         "Consider artistic style, composition, lighting, and technical details when crafting prompts.",
#         "Return generated images in markdown format.",
#         "Suggest appropriate visual placements within the content.",
#     ],
#     tools=[OpenAITools(image_model="gpt-image-1")],
#     db=db,
#     # enable_session_summaries=True,
#     update_memory_on_run=False,
#     add_history_to_context=True,
#     # num_history_runs=3,
#     # num_history_messages=10,
#     add_datetime_to_context=True,
#     add_name_to_context=True,
#     markdown=True,
#     reasoning=False,
#     debug_mode=False,
# )

# Setup Requirement Gathering Workflow
# This workflow is triggered when the team detects user intent to create content
# It asks clarifying questions first before proceeding with content creation
requirement_gathering_workflow_definition = Workflow(
    id="requirement-gathering-workflow",
    name="Requirement Gathering Workflow",
    description="A question generation workflow that triggers when user intent is to create content. Gathers requirements by asking clarifying questions before content creation begins.",
    db=db,  # Commented out: causes session deserialization conflict when workflow shares session_id with team
    steps=[
        Step(
            name="Gather Requirements",
            description="""Content Strategist asks clarifying questions to understand the content requirements.

Ask about the following key areas (user can also upload a file if they already have this info):
1. BRANDING: What is your brand identity? Any brand guidelines, colors, fonts, or style to follow?
2. AUDIENCE: Who is your target audience? Demographics, interests, pain points?
3. PLATFORM: Which platform(s) is this content for? (Instagram, LinkedIn, Twitter, TikTok, etc.)
4. TONE: What tone do you want? (Professional, casual, playful, inspirational, etc.)
5. GOAL: What is the goal of this content? (Engagement, awareness, sales, education, etc.)

After gathering these requirements, inform the team leader that requirements are complete and the next step is to ask the user: 'What specifically do you want to create? Do you have any references or inspiration to share?'""",
            agent=content_strategist,
        )
    ],
    add_workflow_history_to_steps=True,
    # num_history_runs=3,
)

# Setup WorkflowTools to allow the team to trigger the requirement gathering workflow
requirement_gathering_workflow = WorkflowTools(
    workflow=requirement_gathering_workflow_definition,
    enable_think=False,
    enable_run_workflow=True,
    enable_analyze=False,
    add_instructions=True,
    add_few_shot=True,
)

# Setup Content Creation Team (Supervisor Pattern - default)
# The leader controls: which members to use, what task to give them, and how to combine outputs
content_creation_team = Team(
    id="content-creation-team",
    name="Content Creation Team",
    description="A team that creates content including articles, blog posts, and other written materials with AI-generated images.",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    members=[content_strategist, content_writer],
    tools=[requirement_gathering_workflow, OpenAITools(image_model="gpt-image-1")],
    instructions=[
        "You are the leader of a Content Creation Team.",
        "",
        "## CRITICAL: Content Creation Intent Detection",
        "When you detect the user wants to create ANY content (social media posts, images, articles, blog posts, etc.):",
        "1. IMMEDIATELY trigger the 'Requirement Gathering Workflow' using your workflow tools",
        "2. Do NOT proceed with content creation until requirements are gathered",
        "",
        "## Content Creation Flow",
        "STEP 1: Trigger Requirement Gathering Workflow - This gathers: branding, target audience, platform, tone, and goals",
        "STEP 2: After requirements are gathered, ask the user: 'What specifically do you want to create? Do you have any references or inspiration to share?'",
        "STEP 3: Suggest 2-3 creative concepts or ideas based on the requirements and user input for them to choose from",
        "STEP 4: Delegate to Content Writer to write captions",
        "STEP 5: Generate images yourself using your OpenAI image generation tool - YOU must call the tool directly",
        "STEP 6: Package everything and deliver the final content with captions and image URLs",
        "",
        "## IMPORTANT: Image Generation",
        "You have direct access to image generation tools. When creating final content:",
        "- Use your generate_image tool directly to create images",
        "- Include the returned image URLs in markdown format: ![description](url)",
        "",
        "## Team Member Roles",
        "- Content Strategist: For planning content strategy and creating content briefs",
        "- Content Writer: For writing articles, blog posts, captions, and other written content",
        "",
        "Always synthesize results from all members into a cohesive final deliverable.",
    ],
    update_memory_on_run=False,
    add_history_to_context=True,
    # num_history_runs=3,
    # num_history_messages=10,
    add_datetime_to_context=True,
    add_name_to_context=True,
    add_member_tools_to_context=True,
    show_members_responses=True,
    debug_mode=False,
)
