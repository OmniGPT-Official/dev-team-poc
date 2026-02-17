"""Instagram Agent - Posts content to Instagram using the Instagram Graph API."""

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.nano_banana import NanoBananaTools

from services.tool_injector import make_tool_hook

from db import db


instagram_agent = Agent(
    name="Instagram Agent",
    model=Gemini(id="gemini-3-flash-preview"),
    description="Posts content to Instagram using the Instagram Graph API.",
    instructions=[
        "You are an Instagram Agent that helps users publish content to Instagram.",
        "You can create photo posts, carousel posts, and reels.",
        "You can also generate images using the create_image tool when the user asks.",
        "When the user attaches an image, use it directly — do NOT ask them to provide a URL.",
        "When asked to post, confirm the caption before publishing.",
        "If Instagram is not connected, use the connect_instagram tool to get the authorization link for the user.",
        "",
        "## Image Selection for Carousels",
        "When posting a carousel, ALL session images are included by default.",
        "To post only specific images (e.g. only generated ones), pass their IDs via the image_ids parameter.",
        "Image IDs are shown in create_image tool responses (e.g. 'Image generated successfully (ID: abc123)').",
        "Always use image_ids when the user asks to post a subset of images.",
    ],
    tools=[NanoBananaTools()],
    pre_hooks=[make_tool_hook("instagram")],
    db=db,
    update_memory_on_run=False,
    add_history_to_context=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
