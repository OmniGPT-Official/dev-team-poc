"""Content Creation Team - A team for creating content with strategist, writer, and image generator."""

from io import BytesIO
from typing import Optional, Sequence
from uuid import uuid4

from agno.agent import Agent
from agno.media import Image
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.team import Team
from agno.tools import nano_banana as _nb
from agno.tools.nano_banana import ALLOWED_RATIOS, NanoBananaTools
from agno.tools.function import ToolResult
from agno.utils.log import log_debug, logger
from google import genai
from google.genai import types
from PIL import Image as PILImage

# Allow Nano Banana Pro (gemini-3-pro-image-preview) until Agno adds it upstream
if "gemini-3-pro-image-preview" not in _nb.ALLOWED_MODELS:
    _nb.ALLOWED_MODELS.append("gemini-3-pro-image-preview")

# Supported output resolutions for gemini-3-pro-image-preview.
# gemini-2.5-flash-image always outputs at 1K and does not support this parameter.
ALLOWED_SIZES = ["1K", "2K", "4K"]


class DynamicNanoBananaTools(NanoBananaTools):
    """NanoBananaTools subclass with dynamic aspect_ratio, resolution control, and image editing.

    Exposes two tools to the LLM:

        create_image  — Text-to-image generation (no input images required).
        edit_image    — Image editing, composition, and style transfer using text
                        instructions combined with images from the conversation.

    The LLM chooses aspect_ratio and image_size per call.  For edit_image, Agno
    auto-injects all conversation images via the ``images`` parameter (excluded
    from the JSON schema so the LLM never sees it).

    INFO — Nano Banana capabilities NOT included (conversation-only limitations):
    ─────────────────────────────────────────────────────────────────────────────
    • Pixel-level mask painting / brush-based inpainting:
      Gemini supports mask-based inpainting, but defining a pixel mask requires a
      drawing UI.  In a text conversation the user can only describe regions
      semantically ("change only the sofa"), which edit_image already handles via
      Gemini's built-in semantic masking.

    • Precise region selection ("edit only this 50×50 px area at coordinates X,Y"):
      Needs a visual region-picker or bounding-box UI that doesn't exist in chat.

    • Multi-turn chat-based editing (persistent Gemini chat sessions):
      The Gemini API supports iterative editing via chat objects
      (client.chats.create → chat.send_message) that preserve full image context
      across turns.  However, Agno's tool invocation is single-shot per call —
      there is no mechanism to persist a Gemini chat session across multiple agent
      turns.  Each edit_image call is a fresh API request.  Implementing this
      would require session-level state management outside the toolkit.

    • Google Search grounding for image generation:
      Gemini 3 Pro can ground generated images in real-time data (weather, news,
      scores) via tools=[{"google_search": {}}].  Not included because the use
      case is narrow for content creation / brand rebranding.  Can be added as a
      boolean flag on create_image if a future workflow needs it.

    • Thought-image inspection (Gemini 3 Pro thinking mode):
      Gemini 3 Pro generates up to two interim "thought images" while reasoning
      about complex compositions.  These are visible in the raw API response
      (part.thought=True) but are filtered out here — only the final image is
      returned.  A future debug mode could surface them.
    ─────────────────────────────────────────────────────────────────────────────

    TODO — Known limitation: image accumulation in long sessions
    ─────────────────────────────────────────────────────────────────────────────
    Agno's collect_joint_images() (agno/utils/agent.py) injects ALL images from
    the entire session into every edit_image call — user uploads AND previously
    generated results.  There is no built-in filtering mechanism.

    Impact:
      • Short sessions (1-3 edits): works well, disambiguation instructions
        guide the agent to label images by upload order.
      • Long sessions (6+ edits): image count grows by ~2 per edit (upload +
        result).  By the 7th edit, ~14 images are injected, hitting Gemini's
        14-image limit.  Quality degrades as the model struggles to tell images
        apart.

    Future improvements (see PR #183 for full details):
      • Selective image passing — filter to only relevant images per call
        (e.g., current turn's uploads + most recent result), instead of the
        full session history.
      • Persistent Gemini chat sessions — use client.chats.create() to maintain
        editing context across agent turns without re-sending all images.
      • Google Search grounding — add use_search_grounding flag to create_image
        for real-time data in generated images.
      • Thought-image debug mode — surface part.thought=True images for
        diagnosing unexpected edit results.
      • Mask-based inpainting via frontend UI — expose a mask_image parameter
        on edit_image if a drawing UI is added to the frontend.
    ─────────────────────────────────────────────────────────────────────────────
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Re-register tools so Agno exposes the correct signatures to the LLM.
        # The parent class only registers create_image; we add edit_image.
        self.tools = [self.create_image, self.edit_image]

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_image_config(self, aspect_ratio: str, image_size: str) -> types.ImageConfig:
        """Build ImageConfig, only including image_size for models that support it.

        image_size is only recognised by gemini-3-pro-image-preview.  Sending it
        to gemini-2.5-flash-image may cause an API error, so we omit it for
        non-Pro models.
        """
        config_kwargs: dict = {"aspect_ratio": aspect_ratio}
        if "pro" in self.model:
            config_kwargs["image_size"] = image_size
        return types.ImageConfig(**config_kwargs)

    def _convert_agno_images_to_pil(self, images: Sequence[Image]) -> list:
        """Convert Agno Image objects to PIL Images for the Gemini API.

        Agno Images may arrive in one of three states:
          • url only   — common from the frontend; get_content_bytes() fetches via HTTP
          • content    — raw bytes already available
          • filepath   — local file path; get_content_bytes() reads the file

        The Gemini genai SDK accepts PIL Image objects directly in the contents
        list and auto-converts them to Blob(data=bytes, mime_type=...) internally.
        """
        pil_images = []
        for agno_img in images:
            try:
                img_bytes = agno_img.get_content_bytes()
                if img_bytes:
                    pil_images.append(PILImage.open(BytesIO(img_bytes)))
                else:
                    logger.warning(f"Image {agno_img.id} has no retrievable content, skipping")
            except Exception as exc:
                logger.error(f"Failed to convert image {agno_img.id}: {exc}")
        return pil_images

    def _process_response(self, response, prompt: str) -> ToolResult:
        """Extract images and text from a Gemini generate_content response.

        Filters out Gemini 3 Pro "thought" parts (interim reasoning images) so
        that only the final output images are returned to the agent.
        """
        generated_images: list[Image] = []
        response_str = ""

        if not hasattr(response, "candidates") or not response.candidates:
            logger.warning("No candidates in response")
            return ToolResult(content="No images were generated in the response")

        for candidate in response.candidates:
            if not hasattr(candidate, "content") or not candidate.content or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
                # Skip thought parts — these are interim reasoning images from
                # Gemini 3 Pro's thinking mode, not final output.
                if getattr(part, "thought", False):
                    continue

                if hasattr(part, "text") and part.text:
                    response_str += part.text + "\n"

                if hasattr(part, "inline_data") and part.inline_data:
                    try:
                        image_data = part.inline_data.data
                        mime_type = getattr(part.inline_data, "mime_type", "image/png")

                        if image_data:
                            pil_img = PILImage.open(BytesIO(image_data))
                            buffer = BytesIO()
                            image_format = "PNG" if "png" in mime_type.lower() else "JPEG"
                            pil_img.save(buffer, format=image_format)
                            buffer.seek(0)

                            agno_img = Image(
                                id=str(uuid4()),
                                content=buffer.getvalue(),
                                original_prompt=prompt,
                            )
                            generated_images.append(agno_img)

                            log_debug(f"Successfully processed image with ID: {agno_img.id}")
                            response_str += f"Image generated successfully (ID: {agno_img.id}).\n"

                    except Exception as img_exc:
                        logger.error(f"Failed to process image data: {img_exc}")
                        response_str += f"Failed to process image: {img_exc}\n"

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            log_debug(
                f"Token usage - Prompt: {response.usage_metadata.prompt_token_count}, "
                f"Response: {response.usage_metadata.candidates_token_count}, "
                f"Total: {response.usage_metadata.total_token_count}"
            )

        if generated_images:
            return ToolResult(
                content=response_str.strip() or "Image(s) generated successfully",
                images=generated_images,
            )
        else:
            return ToolResult(
                content=response_str.strip() or "No images were generated",
                images=None,
            )

    # ── Tools exposed to the LLM ────────────────────────────────────────────

    def create_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> ToolResult:
        """Generate an image from a text prompt (text-to-image, no input images).

        Args:
            prompt: The text prompt describing the image to generate.
            aspect_ratio: Output aspect ratio. Supported: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9.
            image_size: Output resolution — "1K" (default), "2K", or "4K". 2K and 4K only work with gemini-3-pro-image-preview.
        """
        if aspect_ratio not in ALLOWED_RATIOS:
            return ToolResult(
                content=f"Invalid aspect_ratio '{aspect_ratio}'. Supported: {', '.join(ALLOWED_RATIOS)}"
            )
        if image_size not in ALLOWED_SIZES:
            return ToolResult(
                content=f"Invalid image_size '{image_size}'. Supported: {', '.join(ALLOWED_SIZES)}"
            )

        try:
            client = genai.Client(api_key=self.api_key)
            log_debug(f"NanoBanana create_image — prompt: {prompt}, ratio: {aspect_ratio}, size: {image_size}")

            cfg = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=self._build_image_config(aspect_ratio, image_size),
            )

            response = client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=cfg,
            )

            return self._process_response(response, prompt)

        except Exception as exc:
            logger.error(f"NanoBanana create_image failed: {exc}")
            return ToolResult(content=f"Error generating image: {str(exc)}")

    def edit_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
        images: Optional[Sequence[Image]] = None,
    ) -> ToolResult:
        """Edit, transform, or compose images using text instructions.

        Automatically receives all images from the conversation context — the
        agent does not pass them explicitly.  Use this tool for any operation
        that modifies or builds upon existing images:

        - Adding or removing elements ("add a hat to the person")
        - Semantic editing / inpainting ("change only the sofa to brown leather")
        - Style transfer ("transform this photo into watercolor style")
        - Logo placement ("place this logo on the product, matching surface curvature")
        - Multi-image composition ("put this dress on this model")
        - Sketch to photo ("turn this pencil sketch into a photorealistic car")
        - Color grading ("apply warm sunset tones to this photo")
        - Upscaling / restoration ("restore this old photo to modern quality")

        Args:
            prompt: Text instructions describing what to do with the image(s).
                    Be specific about what to change and what to preserve.
            aspect_ratio: Output aspect ratio. Supported: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9.
            image_size: Output resolution — "1K" (default), "2K", or "4K". 2K and 4K only work with gemini-3-pro-image-preview.
        """
        # NOTE: ``images`` is auto-injected by Agno from the conversation context.
        # It is excluded from the JSON schema sent to the LLM.  Agno's agent
        # runtime calls collect_joint_images() which gathers every image the user
        # uploaded and every image previously generated in this session, then sets
        # func._images before invoking this method.  If the function signature
        # includes ``images``, Agno passes _images as the argument automatically.
        #
        # TODO: This injects ALL session images (uploads + generated results) with
        # no filtering.  In long sessions the list grows unboundedly and can hit
        # Gemini's 14-image limit.  Add selective filtering here once Agno supports
        # it, or implement custom filtering (e.g., keep only current-turn uploads +
        # most recent generated image).  See PR #183 for details.
        if not images:
            return ToolResult(
                content=(
                    "No images found in the conversation. "
                    "Ask the user to upload at least one image before calling edit_image."
                )
            )

        if aspect_ratio not in ALLOWED_RATIOS:
            return ToolResult(
                content=f"Invalid aspect_ratio '{aspect_ratio}'. Supported: {', '.join(ALLOWED_RATIOS)}"
            )
        if image_size not in ALLOWED_SIZES:
            return ToolResult(
                content=f"Invalid image_size '{image_size}'. Supported: {', '.join(ALLOWED_SIZES)}"
            )

        try:
            client = genai.Client(api_key=self.api_key)

            # Convert Agno Image objects → PIL Images.
            # Agno images may be URL-only (frontend uploads), raw bytes
            # (previously generated), or file paths.  _convert_agno_images_to_pil
            # handles all three via Image.get_content_bytes().
            pil_images = self._convert_agno_images_to_pil(images)
            if not pil_images:
                return ToolResult(
                    content=(
                        "Could not process any of the conversation images. "
                        "They may be corrupted or inaccessible."
                    )
                )

            log_debug(
                f"NanoBanana edit_image — {len(pil_images)} image(s), "
                f"prompt: {prompt}, ratio: {aspect_ratio}, size: {image_size}"
            )

            # Build contents list: text prompt first, then images.
            # This matches the cookbook convention (text, image1, image2, …).
            # Gemini treats the contents as a multimodal bag — ordering doesn't
            # affect results — but text-first is the canonical pattern from the
            # official Nano Banana Colab notebook.
            # The genai SDK accepts PIL Images directly and auto-converts them
            # to Blob(data=bytes, mime_type=...) internally.
            # Gemini 3 Pro supports up to 14 reference images per request.
            contents: list = [prompt] + list(pil_images)

            # Use TEXT + IMAGE response modalities so Gemini can describe what
            # it changed alongside the edited image.
            cfg = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=self._build_image_config(aspect_ratio, image_size),
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=cfg,
            )

            return self._process_response(response, prompt)

        except Exception as exc:
            logger.error(f"NanoBanana edit_image failed: {exc}")
            return ToolResult(content=f"Error editing image: {str(exc)}")

from services.tool_injector import make_tool_hook
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
        "However, you must NEVER re-ask something the user already told you — read the full conversation history first.",
        "",
        "Follow this process:",
        "1. Read the user's message AND the team conversation history. Identify what has already been provided about each of the 5 areas.",
        "2. Acknowledge what you understood — briefly list it back so the user feels heard.",
        "3. Only ask about what is genuinely MISSING, all in ONE consolidated message (never one question at a time).",
        "4. If the user provided nearly everything (like a detailed brief), just confirm your understanding and ask 1-2 small clarifying questions at most.",
        "",
        "80/20 rule: If the user gave you 80% of what you need, confirm the 80% and ask only about the remaining 20%.",
        "",
        "Note: The user can upload a file if they already have this information.",
        "",
        "## Output: Structured Brief",
        "Once you have enough information, output a structured content brief with these sections:",
        "- **Brand**: name, colors, visual identity notes",
        "- **Audience**: who the content is for",
        "- **Platform**: where it will be published (Instagram, LinkedIn, blog, etc.)",
        "- **Tone**: voice and style (professional, playful, bold, etc.)",
        "- **Goal**: what the content should achieve (awareness, sales, engagement, etc.)",
        "- **Key messages**: the core ideas to communicate",
        "",
        "This brief will guide the rest of the team. Keep it concise and actionable.",
    ],
    db=db,
    # enable_session_summaries=True,
    update_memory_on_run=False,
    add_history_to_context=True,
    num_history_messages=10,
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
        "",
        "## Writing Process",
        "1. Read the content brief and style direction from the conversation history.",
        "2. Write captions, copy, or articles that match the brief's tone, audience, and platform.",
        "3. Structure each piece clearly — if writing multiple pieces (e.g. carousel slides), number them.",
        "4. For social media: write platform-appropriate captions with hashtags where relevant.",
        "5. For long-form: use clear headings, logical flow, and a strong opening hook.",
        "",
        "## Quality Standards",
        "- Match the specified tone exactly (don't default to generic marketing voice).",
        "- Keep copy concise — every word should earn its place.",
        "- If writing for multiple slides/posts, ensure they tell a cohesive story together.",
        "- Include a call-to-action where appropriate.",
    ],
    db=db,
    # enable_session_summaries=True,
    update_memory_on_run=False,
    add_history_to_context=True,
    num_history_messages=10,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
    debug_mode=False,
)

# image_generator = Agent(
#     name="Image Generator",
#     model=Gemini(id="gemini-3-flash-preview"),
#     description="Generates images using Google's Nano Banana Pro model and manages visual assets for content. Creates high-quality images to enhance content.",
#     instructions=[
#         "You are an Image Generator who creates visual assets using Google's Nano Banana Pro image generation.",
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
#     tools=[NanoBananaTools(model="gemini-3-pro-image-preview")],
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

# Setup Content Creation Team (Supervisor Pattern - default)
# The leader controls: which members to use, what task to give them, and how to combine outputs
# NOTE: WorkflowTools was removed because WorkflowTools.run_workflow() creates a new workflow run
# on every call, losing all prior context and causing infinite intake loops. The team's built-in
# delegate_task_to_member is used instead — members receive team history via
# add_team_history_to_members=True, avoiding the fresh-run problem.
content_creation_team = Team(
    id="content-creation-team",
    name="Content Creation Team",
    description="A team that creates content including articles, blog posts, and other written materials with AI-generated images.",
    model=Claude(id="claude-sonnet-4-5-20250929"),
    db=db,
    members=[content_strategist, content_writer],
    tools=[DynamicNanoBananaTools(model="gemini-3-pro-image-preview")],
    pre_hooks=[make_tool_hook("instagram")],
    send_media_to_model=True,
    instructions=[
        "You are the leader of a Content Creation Team.",
        "",
        "## CRITICAL: State-Aware Progression",
        "Before EVERY response, read the full conversation history and determine which PHASE you are in.",
        "Do NOT re-trigger intake if requirements have already been gathered in this conversation.",
        "Do NOT repeat a phase that has already been completed.",
        "Progress forward through the phases — never go backward.",
        "",
        "## PHASE 1 — Intake (delegate to Content Strategist)",
        "When a user wants to create content, delegate to the Content Strategist to gather requirements.",
        "The Strategist will read what the user already provided, confirm it, and only ask about gaps.",
        "SKIP this phase entirely if the user's first message already covers all 5 areas (branding, audience, platform, tone, goal).",
        "If the Strategist asked gap questions, wait for the user to answer, then delegate to the Strategist ONE MORE TIME to compile the final brief.",
        "Once the Strategist returns a structured brief, move to PHASE 2. Do NOT re-start intake after a brief has been produced.",
        "",
        "## PHASE 2 — Scope",
        "Ask the user: 'What specifically do you want to create? Do you have any references or inspiration to share?'",
        "Wait for the user's answer before continuing.",
        "",
        "## PHASE 3 — Visual Exploration",
        "Call create_image 2-3 times with different visual styles using the brand colors and guidelines.",
        "The generated images will be attached automatically — do NOT write markdown image links or invent URLs.",
        "Ask the user which visual direction they prefer.",
        "",
        "## PHASE 4 — Style Template Lock",
        "After the user picks a visual direction, write a detailed 'style template' — a reusable prompt prefix.",
        "Include: color palette, mood, lighting style, composition approach, typography style, aspect ratio, and overall aesthetic.",
        "Example: 'Clean minimalist Instagram story, dark green (#3F5A3A) background, light green (#E3EDE3) accents, soft natural lighting, elegant serif typography, botanical photography style, 9:16 vertical, professional B2B aesthetic.'",
        "Share the style template with the user for confirmation.",
        "Every image generated from this point forward MUST start with this style template.",
        "",
        "## PHASE 5 — Copy (delegate to Content Writer)",
        "Delegate to the Content Writer to write captions/copy for each content piece.",
        "The Writer has access to the conversation history including the brief and style template.",
        "",
        "## PHASE 6 — Copy Approval",
        "Present the written copy/captions to the user for approval.",
        "Do NOT proceed to image generation until the user explicitly confirms the copy is good.",
        "If the user requests changes, delegate back to the Content Writer with the feedback.",
        "",
        "## PHASE 7 — Production (generate ALL images)",
        "Generate one image for EVERY slide or content piece in the deliverable.",
        "Prepend the style template to each image prompt to maintain visual consistency.",
        "Do NOT use placeholder descriptions like '[Image: ...]' — actually call the image generation tool for every single visual.",
        "If the project has 10 slides, generate 10 images. No exceptions.",
        "",
        "## PHASE 8 — Delivery & Publishing",
        "Package everything and deliver the final content with:",
        "- All generated images (already attached from PHASE 7 — do NOT re-link or write markdown image syntax)",
        "- Corresponding captions/copy next to each image",
        "- Any additional notes or recommendations",
        "",
        "If the user wants to post to Instagram, use the post_image or post_carousel tools.",
        "If Instagram is not connected, use connect_instagram to get the authorization link.",
        "Always confirm with the user before publishing to Instagram.",
        "",
        "## Premature Image Generation Guardrail",
        "If a user asks to 'just make an image' or 'generate an image' immediately without context:",
        "1. Acknowledge their request warmly (e.g. 'I'd love to help create that!')",
        "2. Briefly explain that aligning on direction first will make the result significantly better",
        "3. Begin PHASE 1 intake",
        "Do NOT generate final images until copy is approved in PHASE 6.",
        "The ONLY exception is PHASE 3, where you generate exploratory sample images for style selection.",
        "",
        "## Image Generation",
        "You have direct access to image generation tools via create_image.",
        "- Whenever an image is returned (e.g., as an image reference ID), render it in Markdown image format using the image reference ID exactly as provided.",
        "- Do NOT transform it into a URL, do NOT invent links, and do NOT wrap it in any external/invalid link.",
        "- Use this format: ![image](<IMAGE_REFERENCE_ID>) where <IMAGE_REFERENCE_ID> is the exact id string you received (unchanged).",
        "- ALWAYS prepend the style template to every image prompt after PHASE 4",
        "- Generate an image for EVERY content piece — never skip any visual",
        "",
        "## Team Member Roles",
        "- Content Strategist: Gathers requirements and creates the content brief (PHASE 1 only)",
        "- Content Writer: Writes captions, copy, and articles (PHASE 5)",
        "",
        "Use delegate_task_to_member to assign work to team members.",
    ],
    update_memory_on_run=False,
    add_history_to_context=True,
    num_history_messages=10,
    add_team_history_to_members=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    add_member_tools_to_context=True,
    show_members_responses=True,
    debug_mode=False,
)
