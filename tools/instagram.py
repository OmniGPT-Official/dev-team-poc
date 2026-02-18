"""Instagram posting toolkit using the Meta Graph API.

Known edge cases / TODOs
========================

1. USER-ATTACHED IMAGES HAVE NO VISIBLE IDs
   NanoBanana tool responses include "Image generated successfully (ID: ...)", so
   the LLM can pass those IDs to post_carousel(image_ids=[...]). But user-uploaded
   images get auto-generated UUIDs that the LLM never sees in conversation text.
   If a user says "post only the photo I uploaded, not the generated ones", the
   agent can't use image_ids for that — it falls back to ALL images (wrong).
   Fix idea: add a list_session_images tool that returns all image IDs with
   metadata (source, timestamp, description), or surface user-image IDs in the
   system prompt via session_state.

2. TOKEN EXPIRATION MID-CAROUSEL
   Instagram access tokens can expire. If we're uploading N images to Supabase
   Storage and the token dies partway through the Instagram API calls, we may
   have orphaned files in the bucket. The except block cleans up storage_paths
   collected so far, but any images already uploaded to storage before the
   _create_media_container call that fails will be cleaned up — however images
   whose _create_media_container succeeded but _publish_media fails won't be
   cleaned from Instagram's side (containers are abandoned, not our storage).

3. INSTAGRAM IMAGE VALIDATION
   Instagram rejects images that are too small (<320px), too large (>1080px on
   shortest side), wrong aspect ratio, or unsupported formats. We upload to
   Supabase Storage first, Instagram fetches the URL, then may reject with a
   cryptic "400 Bad Request". We should validate dimensions/format before
   uploading and return a human-readable error (e.g., "Image must be at least
   320x320 pixels").

4. NO DELETE POST CAPABILITY
   If the agent posts the wrong images (e.g., carousel with 5 instead of 2),
   there's no way to delete it from within the agent. Consider adding a
   delete_post tool using the Instagram Graph API DELETE /{media-id} endpoint.

5. SINGLE GENERATED IMAGE → CAROUSEL MISMATCH
   If NanoBanana generates only 1 image and the user says "post as carousel",
   post_carousel returns "requires at least 2 images". The error is clear but
   the agent should ideally suggest posting as a single image instead.

6. CDN PROPAGATION DELAY
   After uploading to Supabase Storage, we immediately send the public URL to
   Instagram. If there's any CDN propagation delay, Instagram might get a 404.
   Not observed in practice, but could add a small delay or a retry.

7. ORPHANED FILES ON SILENT CLEANUP FAILURE
   _delete_from_storage swallows all exceptions. If cleanup fails (network
   issue, permission change), files accumulate in the bucket indefinitely.
   Consider a scheduled cleanup job or at minimum logging failed deletions.

8. post_image LACKS image_id PARAMETER
   post_image uses images[-1] (most recent). If the user says "post the first
   image I sent", there's no way to select it. post_carousel has image_ids but
   post_image doesn't. Should add an image_id param for parity.
"""

import uuid
from mimetypes import guess_extension
from typing import Optional, Sequence

import requests
from agno.media import Image
from agno.tools import Toolkit

GRAPH_API_BASE = "https://graph.instagram.com/v22.0"
TIMEOUT = 30

# Map image formats to MIME types for attached images
FORMAT_TO_MIME = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


class InstagramConnectTools(Toolkit):
    """Provides an OAuth URL for connecting an Instagram account."""

    def __init__(self, auth_url: str):
        super().__init__(name="instagram_connect_tools")
        self._auth_url = auth_url
        self.register(self.connect_instagram)

    def connect_instagram(self) -> str:
        """Get the link to connect your Instagram account. The user must open this link to authorize."""
        return (
            "Instagram is not connected yet. "
            "Please open this link to connect your account:\n\n"
            f"{self._auth_url}\n\n"
            "After authorizing, come back and try again."
        )


class InstagramTools(Toolkit):
    """Post images and carousels to Instagram via the Graph API.

    Requires a Meta long-lived user access token and the Instagram Business
    Account ID for the target account.

    When supabase_url and supabase_key are provided, users can post images
    they attached in the chat — the tool uploads them to a temporary public
    URL via Supabase Storage, posts to Instagram, then cleans up.
    """

    def __init__(
        self,
        access_token: str,
        ig_user_id: str,
        supabase_url: str = "",
        supabase_key: str = "",
        storage_bucket: str = "media",
    ):
        super().__init__(name="instagram_tools")
        self.access_token = access_token
        self.ig_user_id = ig_user_id

        # Optional Supabase Storage for handling attached images
        self._storage = None
        if supabase_url and supabase_key:
            from supabase import create_client

            self._storage = create_client(supabase_url, supabase_key)
            self._bucket = storage_bucket
            self._ensure_bucket()

        self.register(self.post_image)
        self.register(self.post_carousel)

    # ------------------------------------------------------------------
    # Supabase Storage helpers (for attached images)
    # ------------------------------------------------------------------

    def _ensure_bucket(self) -> None:
        try:
            self._storage.storage.get_bucket(self._bucket)
        except Exception:
            self._storage.storage.create_bucket(self._bucket, options={"public": True})

    def _upload_to_storage(self, data: bytes, content_type: str) -> tuple[str, str]:
        """Upload bytes to Supabase Storage. Returns (public_url, storage_path)."""
        ext = guess_extension(content_type) or ".jpg"
        path = f"images/{uuid.uuid4().hex}{ext}"
        self._storage.storage.from_(self._bucket).upload(
            path, data, file_options={"content-type": content_type},
        )
        # TODO(edge-case-6): If there's CDN propagation delay, Instagram might
        # get a 404 when fetching this URL. Consider adding a small delay or retry.
        public_url = self._storage.storage.from_(self._bucket).get_public_url(path)
        return public_url, path

    def _delete_from_storage(self, paths: list[str]) -> None:
        """Delete files from Supabase Storage (best-effort cleanup)."""
        # TODO(edge-case-7): Silent failures here cause orphaned files. Consider
        # logging failed deletions or adding a scheduled bucket cleanup job.
        try:
            self._storage.storage.from_(self._bucket).remove(paths)
        except Exception:
            pass  # Non-critical — don't fail the post over cleanup

    def _get_image_url(self, img: Image) -> tuple[str, str]:
        """Get a public URL for an Image object. Returns (url, storage_path or "")."""
        if img.url:
            return img.url, ""

        if not self._storage:
            raise ValueError("Cannot upload attached images — Supabase Storage not configured")

        data = img.get_content_bytes()
        if not data:
            raise ValueError("Attached image is empty")

        # TODO(edge-case-3): Validate image dimensions/format before uploading.
        # Instagram requires min 320px, max 1080px shortest side, JPEG/PNG only.
        # Currently we upload first and get a cryptic 400 from Instagram later.
        content_type = img.mime_type or FORMAT_TO_MIME.get(img.format or "", "image/jpeg")
        return self._upload_to_storage(data, content_type)

    # ------------------------------------------------------------------
    # Instagram API helpers
    # ------------------------------------------------------------------
    # TODO(edge-case-2): If the access token expires mid-carousel (between
    # creating containers and publishing), containers are abandoned on
    # Instagram's side. Consider checking token validity before starting.
    #
    # TODO(edge-case-4): Add a delete_post(media_id) tool using the
    # Instagram Graph API DELETE /{media-id} endpoint so the agent can
    # undo accidental posts (e.g., carousel with wrong images).

    def _create_media_container(
        self,
        image_url: str,
        caption: Optional[str] = None,
        is_carousel_item: bool = False,
    ) -> str:
        """Create a media container and return the creation ID."""
        payload: dict = {
            "image_url": image_url,
            "access_token": self.access_token,
        }
        if is_carousel_item:
            payload["is_carousel_item"] = True
        if caption:
            payload["caption"] = caption

        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
            data=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def _publish_media(self, creation_id: str) -> str:
        """Publish a previously created media container and return the media ID."""
        resp = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": self.access_token,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    # ------------------------------------------------------------------
    # Public tools exposed to the LLM
    # ------------------------------------------------------------------

    # TODO(edge-case-8): Add image_id parameter for parity with post_carousel,
    # so the agent can select a specific image (not just the most recent one).
    def post_image(
        self,
        caption: str = "",
        image_url: str = "",
        images: Optional[Sequence[Image]] = None,
    ) -> str:
        """Post a single image to Instagram.

        If the user attached an image in the chat, it will be used automatically.
        Otherwise, provide a publicly accessible image URL.

        Args:
            caption: The caption text for the post.
            image_url: A direct, publicly accessible image URL. Not needed if the
                user attached an image in the chat.

        Returns:
            A success message with the media ID, or an error description.
        """
        storage_path = ""
        try:
            # Prefer attached image over URL
            if images:
                url, storage_path = self._get_image_url(images[-1])
            elif image_url:
                url = image_url
            else:
                return "No image provided. Please attach an image or provide a public image URL."

            creation_id = self._create_media_container(url, caption=caption)
            media_id = self._publish_media(creation_id)

            if storage_path:
                self._delete_from_storage([storage_path])

            return f"Image posted successfully. Media ID: {media_id}"
        except Exception as e:
            if storage_path:
                self._delete_from_storage([storage_path])
            return f"Failed to post image: {e}"

    def post_carousel(
        self,
        caption: str = "",
        image_urls: Optional[list[str]] = None,
        image_ids: Optional[list[str]] = None,
        images: Optional[Sequence[Image]] = None,
    ) -> str:
        """Post a carousel (multiple images) to Instagram.

        If the user attached images in the chat, they will be used automatically.
        Otherwise, provide a list of publicly accessible image URLs.

        To select specific images (e.g. only generated images), pass their IDs
        via image_ids. Image IDs are shown in tool responses when images are
        generated (e.g. by create_image).

        Args:
            caption: The caption text for the carousel post.
            image_urls: A list of 2-10 publicly accessible image URLs. Not needed
                if the user attached images in the chat.
            image_ids: Optional list of image IDs to select specific images from
                the session. When provided, only images matching these IDs are used.

        Returns:
            A success message with the media ID, or an error description.
        """
        storage_paths: list[str] = []
        try:
            # Filter images by ID if specified
            # TODO(edge-case-1): This only works for NanoBanana-generated images
            # whose IDs are visible in tool responses. User-attached images have
            # auto-generated UUIDs that the LLM never sees. Need a way to surface
            # user-image IDs (e.g., list_session_images tool or session_state).
            if image_ids and images:
                id_set = set(image_ids)
                images = [img for img in images if img.id in id_set]

            # Prefer attached images over URLs
            if images and len(images) >= 2:
                urls = []
                for img in images:
                    url, path = self._get_image_url(img)
                    urls.append(url)
                    if path:
                        storage_paths.append(path)
            elif image_urls:
                urls = image_urls
            else:
                # TODO(edge-case-5): If only 1 generated image exists, suggest
                # posting as a single image instead of just rejecting.
                return "A carousel requires at least 2 images. Please attach images or provide image URLs."

            if len(urls) < 2 or len(urls) > 10:
                return "A carousel requires between 2 and 10 images."

            # Create individual carousel item containers
            children_ids = []
            for url in urls:
                item_id = self._create_media_container(url, is_carousel_item=True)
                children_ids.append(item_id)

            # Create the carousel container
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
                data={
                    "media_type": "CAROUSEL",
                    "children": ",".join(children_ids),
                    "caption": caption,
                    "access_token": self.access_token,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            carousel_id = resp.json()["id"]

            # Publish the carousel
            media_id = self._publish_media(carousel_id)

            if storage_paths:
                self._delete_from_storage(storage_paths)

            return f"Carousel posted successfully with {len(urls)} images. Media ID: {media_id}"
        except Exception as e:
            if storage_paths:
                self._delete_from_storage(storage_paths)
            return f"Failed to post carousel: {e}"
