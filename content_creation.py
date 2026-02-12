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
        "## Requirements Gathering — Adaptive Intake",
        "You need information across 5 areas: BRANDING, AUDIENCE, PLATFORM, TONE, and GOAL.",
        "However, you must NEVER re-ask something the user already told you.",
        "",
        "Follow this process:",
        "1. Carefully read the user's message and identify what they already provided about each area.",
        "2. Acknowledge what you understood — briefly list it back so the user feels heard.",
        "3. Only ask about what is genuinely missing, all in ONE message (not one question at a time).",
        "4. If the user provided nearly everything (like a detailed brief), just confirm your understanding and ask 1-2 small clarifying questions at most.",
        "",
        "Key rule: If the user gave you 80% of what you need, confirm the 80% and ask only about the remaining 20%.",
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
            description="""Analyze the user's message. Determine what information has already been provided about branding, audience, platform, tone, and goals. For areas well-covered, confirm your understanding. For areas missing, ask in a single consolidated message. If the user provided a very detailed brief, you may only need to confirm and ask 1-2 small gap questions. Never make the user repeat themselves. User can also upload a file if they already have this info. After gathering requirements, inform the team leader that requirements are complete and the next step is to ask the user: 'What specifically do you want to create? Do you have any references or inspiration to share?'""",
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
        "## CRITICAL: No Premature Image Generation",
        "Do NOT generate final deliverable images until ALL of these conditions are met:",
        "1. Requirements have been gathered and confirmed with the user",
        "2. The user has visually picked a style direction from the sample images in STEP 3",
        "3. Copy/captions have been written and approved by the user",
        "The ONLY exception is STEP 3, where you generate 2-3 exploratory sample images so the user can pick a visual direction.",
        "Final production images (STEP 7) are always the LAST step, never the first.",
        "If a user asks to 'just make an image' immediately: first acknowledge their request (e.g. 'I'd love to help create that image!'), then explain why aligning on direction first will make the result significantly better, and then begin the intake process.",
        "",
        "## Content Creation Flow",
        "STEP 1: Trigger Requirement Gathering Workflow - This gathers: branding, target audience, platform, tone, and goals",
        "STEP 2: After requirements are gathered, ask the user: 'What specifically do you want to create? Do you have any references or inspiration to share?'",
        "STEP 3: Generate 2-3 sample images in different visual styles using the brand colors and guidelines provided.",
        "- Present them to the user so they can visually pick a direction",
        "- Do NOT describe concepts in text paragraphs — show them as actual generated images",
        "STEP 4 (Style Template Lock): After the user picks a visual direction, write a detailed 'style template' — a reusable prompt prefix that captures the exact visual feel.",
        "- Include: color palette, mood, lighting style, composition approach, typography style, aspect ratio, and overall aesthetic",
        "- Example: 'Clean minimalist Instagram story, dark green (#3F5A3A) background, light green (#E3EDE3) accents, soft natural lighting, elegant serif typography, botanical photography style, 9:16 vertical, professional B2B aesthetic.'",
        "- Every image generated from this point forward MUST start with this style template to ensure all images feel cohesive and on-brand",
        "STEP 5: Delegate to Content Writer to write captions/copy for each content piece",
        "STEP 6: Present the written copy/captions to the user for approval. Do NOT proceed to image generation until the user confirms the copy is good.",
        "STEP 7: Generate one image for EVERY slide or content piece in the deliverable.",
        "- Prepend the style template to each image prompt to maintain consistency",
        "- Do not use placeholder descriptions like [Image: ...] — actually call the image generation tool for every single visual",
        "- If the project has 10 slides, generate 10 images",
        "STEP 8: Package everything and deliver the final content with captions and image URLs",
        "",
        "## IMPORTANT: Image Generation",
        "You have direct access to image generation tools. When creating final content:",
        "- Use your generate_image tool directly to create images",
        "- Include the returned image URLs in markdown format: ![description](url)",
        "- ALWAYS prepend the style template to every image prompt after STEP 4",
        "- Generate an image for EVERY content piece — never leave text placeholders",
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
