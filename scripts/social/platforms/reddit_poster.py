"""
Reddit PRAW poster for suplementi.deals.

Uses PRAW (Python Reddit API Wrapper) with proper rate limiting.

Account requirements:
  - A Reddit account with ≥50 karma (accounts with <50 karma cannot post links)
  - Recommended: complete the 30-day warmup schedule first (see RSS-29)
  - Create a Reddit App at https://www.reddit.com/prefs/apps
    Type: "script" for personal use, "web app" for server-based use
  - Store client_id, client_secret, username, password in config.yml

Risk notes:
  - New accounts posting promotional content will likely get flagged
  - r/serbia mods are active — natural, helpful tone is critical
  - Never post the same content twice
  - Never post more than 1 promotional link per thread
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import praw
import prawcore

logger = logging.getLogger(__name__)


@dataclass
class PostResult:
    success: bool
    post_id: str
    reddit_url: Optional[str] = None
    error: Optional[str] = None


class RedditPoster:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        user_agent: str = "suplementi.deals social poster v1.0",
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        if not dry_run:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                user_agent=user_agent,
            )
        else:
            self.reddit = None

    def verify_credentials(self) -> bool:
        """Check that credentials are valid."""
        if self.dry_run:
            return True
        try:
            me = self.reddit.user.me()
            logger.info("Reddit authenticated as u/%s (karma: %s)", me.name, me.comment_karma + me.link_karma)
            return True
        except prawcore.exceptions.OAuthException as exc:
            logger.error("Reddit auth failed: %s", exc)
            return False
        except Exception as exc:
            logger.exception("Reddit verification error: %s", exc)
            return False

    def post_comment(self, submission_url: str, body: str, post_id: str) -> PostResult:
        """
        Post a comment on an existing Reddit submission.

        Args:
            submission_url: Full URL of the Reddit post to comment on
            body: Comment text (markdown supported)
            post_id: Local content ID for tracking
        """
        if self.dry_run:
            logger.info("[DRY RUN] Reddit comment on %s:\n%s", submission_url, body[:200])
            return PostResult(success=True, post_id=post_id, reddit_url=submission_url)

        try:
            # Extract submission ID from URL
            submission = self.reddit.submission(url=submission_url)
            # Rate-limit courtesy pause
            time.sleep(random.uniform(2.0, 4.0))
            comment = submission.reply(body=body)
            url = f"https://reddit.com{comment.permalink}"
            logger.info("Reddit comment posted: %s", url)
            return PostResult(success=True, post_id=post_id, reddit_url=url)
        except prawcore.exceptions.Forbidden as exc:
            msg = f"Forbidden (subreddit restricted or account suspended): {exc}"
            logger.error(msg)
            return PostResult(success=False, post_id=post_id, error=msg)
        except prawcore.exceptions.TooManyRequests:
            msg = "Rate limited by Reddit API — back off and retry"
            logger.warning(msg)
            return PostResult(success=False, post_id=post_id, error=msg)
        except Exception as exc:
            logger.exception("Reddit comment error: %s", exc)
            return PostResult(success=False, post_id=post_id, error=str(exc))

    def submit_text_post(self, subreddit: str, title: str, body: str, post_id: str) -> PostResult:
        """
        Submit a new self-text post to a subreddit.

        Args:
            subreddit: subreddit name without r/ prefix (e.g. 'serbia')
            title: post title
            body: post body (markdown)
            post_id: local content ID for tracking
        """
        if self.dry_run:
            logger.info(
                "[DRY RUN] Reddit post to r/%s — '%s':\n%s",
                subreddit, title, body[:200],
            )
            return PostResult(success=True, post_id=post_id, reddit_url=f"https://reddit.com/r/{subreddit}/")

        try:
            sub = self.reddit.subreddit(subreddit)
            # Courtesy pause before submitting
            time.sleep(random.uniform(3.0, 6.0))
            submission = sub.submit(title=title, selftext=body)
            url = f"https://reddit.com{submission.permalink}"
            logger.info("Reddit post submitted: %s", url)
            return PostResult(success=True, post_id=post_id, reddit_url=url)
        except prawcore.exceptions.Forbidden as exc:
            msg = f"Forbidden (subreddit restricted or flair required): {exc}"
            logger.error(msg)
            return PostResult(success=False, post_id=post_id, error=msg)
        except prawcore.exceptions.TooManyRequests:
            msg = "Rate limited by Reddit API"
            logger.warning(msg)
            return PostResult(success=False, post_id=post_id, error=msg)
        except Exception as exc:
            logger.exception("Reddit submit error: %s", exc)
            return PostResult(success=False, post_id=post_id, error=str(exc))

    def find_target_threads(self, subreddit: str, keywords: list[str], limit: int = 5) -> list[dict]:
        """
        Search a subreddit for threads matching keywords.
        Returns list of {title, url, id} for the best matches.

        Useful for finding reply targets dynamically.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would search r/%s for: %s", subreddit, keywords)
            return []

        results = []
        query = " OR ".join(keywords[:3])  # Reddit search supports OR
        try:
            sub = self.reddit.subreddit(subreddit)
            for submission in sub.search(query, sort="new", time_filter="month", limit=limit):
                results.append({
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "id": submission.id,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                })
            logger.info("Found %d threads in r/%s for query: %s", len(results), subreddit, query)
        except Exception as exc:
            logger.warning("Reddit search error: %s", exc)
        return results


def post_to_reddit(
    post: dict,
    credentials: dict,
    dry_run: bool = False,
    target_url: Optional[str] = None,
) -> PostResult:
    """
    High-level helper called by the main poster CLI.

    Args:
        post: dict from reddit_posts.json
        credentials: {client_id, client_secret, username, password}
        dry_run: simulate without posting
        target_url: explicit URL to reply to (overrides dynamic search)
    """
    poster = RedditPoster(
        client_id=credentials.get("client_id", ""),
        client_secret=credentials.get("client_secret", ""),
        username=credentials.get("username", ""),
        password=credentials.get("password", ""),
        dry_run=dry_run,
    )

    if not poster.verify_credentials():
        return PostResult(success=False, post_id=post["id"], error="Invalid Reddit credentials")

    if post["type"] == "reply":
        # Find a thread if no explicit URL given
        if not target_url:
            threads = poster.find_target_threads(
                post["subreddit"],
                post.get("target_thread_keywords", []),
                limit=5,
            )
            if not threads:
                return PostResult(
                    success=False,
                    post_id=post["id"],
                    error="No matching threads found for reply",
                )
            # Pick the most recent thread with activity
            target = sorted(threads, key=lambda t: t["num_comments"], reverse=True)[0]
            target_url = target["url"]
            logger.info("Selected thread for reply: %s", target_url)

        return poster.post_comment(target_url, post["body"], post["id"])

    elif post["type"] == "new_post":
        return poster.submit_text_post(
            post["subreddit"],
            post["title"],
            post["body"],
            post["id"],
        )
    else:
        return PostResult(success=False, post_id=post["id"], error=f"Unknown post type: {post['type']}")
