"""
Facebook Graph API poster for suplementi.deals.

Uses the Facebook Graph API v21.0 to post content to a Facebook Page.
Does NOT use headless browser — API-only, lower risk of bans.

Requirements:
  - A Facebook Page created for suplementi.deals
  - A Facebook App with pages_manage_posts + pages_read_engagement permissions
  - A long-lived Page Access Token stored in config

Token generation flow (one-time, manual):
  1. Create a Facebook App at developers.facebook.com
  2. Add "Facebook Login" and "Pages API" products
  3. Generate a User Access Token with pages_manage_posts scope
  4. Exchange for long-lived token:
       GET /oauth/access_token
         ?grant_type=fb_exchange_token
         &client_id={app_id}
         &client_secret={app_secret}
         &fb_exchange_token={short_lived_token}
  5. Get your Page Access Token:
       GET /{page_id}?fields=access_token&access_token={long_lived_user_token}
  6. Store the page_access_token in config.yml
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


@dataclass
class PostResult:
    success: bool
    post_id: str
    facebook_post_id: Optional[str] = None
    error: Optional[str] = None


class FacebookPoster:
    def __init__(self, page_id: str, page_access_token: str, dry_run: bool = False):
        """
        Args:
            page_id: Facebook Page ID (numeric string)
            page_access_token: Long-lived Page Access Token
            dry_run: if True, log what would be posted but do not call API
        """
        self.page_id = page_id
        self.token = page_access_token
        self.dry_run = dry_run

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{GRAPH_API_BASE}/{endpoint}"
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post_text(self, message: str, post_id: str) -> PostResult:
        """
        Post a plain text message to the Facebook Page feed.

        Args:
            message: Full post text (including hashtags)
            post_id: Local content ID for tracking
        """
        if self.dry_run:
            logger.info("[DRY RUN] Facebook post:\n%s", message[:200])
            return PostResult(success=True, post_id=post_id, facebook_post_id="dry-run-id")

        try:
            result = self._post(
                f"{self.page_id}/feed",
                {
                    "message": message,
                    "access_token": self.token,
                },
            )
            fb_id = result.get("id")
            logger.info("Facebook post published: %s", fb_id)
            return PostResult(success=True, post_id=post_id, facebook_post_id=fb_id)
        except requests.HTTPError as exc:
            error_body = exc.response.text if exc.response else str(exc)
            logger.error("Facebook API error: %s", error_body)
            return PostResult(success=False, post_id=post_id, error=error_body)
        except Exception as exc:
            logger.exception("Unexpected Facebook error: %s", exc)
            return PostResult(success=False, post_id=post_id, error=str(exc))

    def schedule_post(self, message: str, publish_unix_timestamp: int, post_id: str) -> PostResult:
        """
        Schedule a post to publish at a future time.

        Args:
            message: Full post text
            publish_unix_timestamp: Unix timestamp (must be 10 min–6 months in future)
            post_id: Local content ID for tracking
        """
        if self.dry_run:
            logger.info(
                "[DRY RUN] Facebook scheduled post at %s:\n%s",
                time.strftime("%Y-%m-%d %H:%M", time.localtime(publish_unix_timestamp)),
                message[:200],
            )
            return PostResult(success=True, post_id=post_id, facebook_post_id="dry-run-scheduled")

        try:
            result = self._post(
                f"{self.page_id}/feed",
                {
                    "message": message,
                    "published": "false",
                    "scheduled_publish_time": str(publish_unix_timestamp),
                    "access_token": self.token,
                },
            )
            fb_id = result.get("id")
            logger.info(
                "Facebook post scheduled for %s: %s",
                time.strftime("%Y-%m-%d %H:%M", time.localtime(publish_unix_timestamp)),
                fb_id,
            )
            return PostResult(success=True, post_id=post_id, facebook_post_id=fb_id)
        except requests.HTTPError as exc:
            error_body = exc.response.text if exc.response else str(exc)
            logger.error("Facebook API error: %s", error_body)
            return PostResult(success=False, post_id=post_id, error=error_body)
        except Exception as exc:
            logger.exception("Unexpected Facebook error: %s", exc)
            return PostResult(success=False, post_id=post_id, error=str(exc))

    def verify_token(self) -> bool:
        """Check that the page access token is valid."""
        try:
            resp = requests.get(
                f"{GRAPH_API_BASE}/me",
                params={"access_token": self.token, "fields": "id,name"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Facebook token valid for page: %s (%s)", data.get("name"), data.get("id"))
            return True
        except Exception as exc:
            logger.error("Facebook token verification failed: %s", exc)
            return False


def build_post_message(template: dict) -> str:
    """
    Build the final message from a facebook_posts.json template.
    Returns the body as-is (board fills in [PLACEHOLDERS] before posting).
    """
    return template["body"]


def post_to_facebook(
    post: dict,
    page_id: str,
    page_access_token: str,
    dry_run: bool = False,
    schedule_timestamp: Optional[int] = None,
) -> PostResult:
    """
    High-level helper called by the main poster CLI.

    Args:
        post: dict from facebook_posts.json
        page_id: Facebook Page ID
        page_access_token: Page Access Token
        dry_run: simulate without calling API
        schedule_timestamp: if provided, schedule post instead of publishing immediately
    """
    poster = FacebookPoster(page_id, page_access_token, dry_run=dry_run)

    if not dry_run and not poster.verify_token():
        return PostResult(success=False, post_id=post["id"], error="Invalid Facebook page access token")

    message = build_post_message(post)

    if schedule_timestamp:
        return poster.schedule_post(message, schedule_timestamp, post["id"])
    else:
        return poster.post_text(message, post["id"])
