#!/usr/bin/env python3
"""
suplementi.deals Social Posting CLI

Usage:
  # Show pending posts in queue
  python poster.py queue

  # Dry-run: see what would be posted without submitting
  python poster.py post --platform forums --dry-run
  python poster.py post --platform reddit --dry-run
  python poster.py post --platform facebook --dry-run

  # Post a specific item by ID
  python poster.py post --id forum-b1 --dry-run

  # Post all pending items for a platform (live)
  python poster.py post --platform forums
  python poster.py post --platform reddit
  python poster.py post --platform facebook

  # Mark a post as done manually (if posted outside this tool)
  python poster.py mark-done --id forum-a1

  # Verify credentials for all platforms
  python poster.py verify

  # Run in cron/heartbeat mode: post one item per platform if schedule is due
  python poster.py cron
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "content"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("poster")


# ─────────────────────────────────────────
# Config loading
# ─────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        logger.error("Config not found: %s — copy config.example.yml to config.yml and fill credentials", config_path)
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────
# Queue management (in-place JSON updates)
# ─────────────────────────────────────────

def load_queue(json_path: Path) -> list[dict]:
    with open(json_path) as f:
        data = json.load(f)
    return data.get("posts", [])


def save_queue(json_path: Path, posts: list[dict]):
    with open(json_path) as f:
        data = json.load(f)
    data["posts"] = posts
    with open(json_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_posted(json_path: Path, post_id: str, url: Optional[str] = None):
    posts = load_queue(json_path)
    for p in posts:
        if p["id"] == post_id:
            p["posted"] = True
            if url:
                p["posted_url"] = url
            p["posted_at"] = int(time.time())
            break
    save_queue(json_path, posts)
    logger.info("Marked %s as posted", post_id)


def pending_posts(json_path: Path) -> list[dict]:
    return [p for p in load_queue(json_path) if not p.get("posted", False)]


def has_unfilled_placeholders(post: dict) -> bool:
    text = post.get("body", "") + post.get("title", "") + post.get("subject", "")
    return "[FILL_" in text or "[PRODUCT_" in text or "[KREATIN_" in text or "[PROTEIN_" in text


# ─────────────────────────────────────────
# Queue command
# ─────────────────────────────────────────

def cmd_queue(args, config):
    queues = {
        "forums": CONTENT_DIR / "forum_posts.json",
        "reddit": CONTENT_DIR / "reddit_posts.json",
        "facebook": CONTENT_DIR / "facebook_posts.json",
    }
    total_pending = 0
    for platform, path in queues.items():
        posts = pending_posts(path)
        total_pending += len(posts)
        print(f"\n=== {platform.upper()} ({len(posts)} pending) ===")
        for p in posts:
            flags = []
            if has_unfilled_placeholders(p):
                flags.append("[NEEDS PRICE FILL]")
            print(f"  {p['id']} — {p.get('type','?')} — {p.get('subject') or p.get('title') or p['body'][:80]!r}  {' '.join(flags)}")
    print(f"\nTotal pending: {total_pending}")


# ─────────────────────────────────────────
# Verify command
# ─────────────────────────────────────────

def cmd_verify(args, config):
    results = {}

    # Facebook
    if config.get("facebook", {}).get("enabled"):
        from platforms.facebook import FacebookPoster
        fb_cfg = config["facebook"]
        poster = FacebookPoster(fb_cfg["page_id"], fb_cfg["page_access_token"])
        results["facebook"] = poster.verify_token()
    else:
        logger.info("Facebook: disabled in config")
        results["facebook"] = None

    # Reddit
    if config.get("reddit", {}).get("enabled"):
        from platforms.reddit_poster import RedditPoster
        rc = config["reddit"]
        poster = RedditPoster(rc["client_id"], rc["client_secret"], rc["username"], rc["password"])
        results["reddit"] = poster.verify_credentials()
    else:
        logger.info("Reddit: disabled in config")
        results["reddit"] = None

    # Forums (just check credentials exist)
    for forum_key, forum_cfg in config.get("forums", {}).items():
        if forum_cfg.get("enabled"):
            has_creds = bool(forum_cfg.get("username")) and bool(forum_cfg.get("password"))
            results[f"forum:{forum_key}"] = has_creds
            if not has_creds:
                logger.warning("Forum %s: missing username or password in config", forum_key)

    print("\nVerification results:")
    for k, v in results.items():
        status = "OK" if v else ("DISABLED" if v is None else "FAILED")
        print(f"  {k}: {status}")


# ─────────────────────────────────────────
# Mark-done command
# ─────────────────────────────────────────

def cmd_mark_done(args, config):
    post_id = args.id
    queues = {
        "forums": CONTENT_DIR / "forum_posts.json",
        "reddit": CONTENT_DIR / "reddit_posts.json",
        "facebook": CONTENT_DIR / "facebook_posts.json",
    }
    for platform, path in queues.items():
        posts = load_queue(path)
        for p in posts:
            if p["id"] == post_id:
                mark_posted(path, post_id)
                print(f"Marked {post_id} as posted in {platform} queue.")
                return
    print(f"Post ID '{post_id}' not found in any queue.")


# ─────────────────────────────────────────
# Post command
# ─────────────────────────────────────────

async def post_forums(config, dry_run: bool, post_id: Optional[str] = None):
    from platforms.forum_sr import post_to_forum

    forums_cfg = config.get("forums", {})
    session_dir = Path(config.get("settings", {}).get("session_dir", ".sessions"))
    queue_path = CONTENT_DIR / "forum_posts.json"

    posts = pending_posts(queue_path)
    if post_id:
        posts = [p for p in posts if p["id"] == post_id]

    if not posts:
        logger.info("No pending forum posts.")
        return

    for post in posts:
        if has_unfilled_placeholders(post) and not dry_run:
            logger.warning("Skipping %s — contains unfilled price placeholders. Fill them first.", post["id"])
            continue

        platform_key = post.get("platform")
        forum_cfg = forums_cfg.get(platform_key, {})
        if not forum_cfg.get("enabled", False) and not dry_run:
            logger.info("Skipping %s — forum %s is disabled in config.", post["id"], platform_key)
            continue

        credentials = {
            "username": forum_cfg.get("username", ""),
            "password": forum_cfg.get("password", ""),
        }

        # Determine URLs based on post type
        thread_url = None
        section_url = None
        if post["type"] == "reply":
            thread_url = forum_cfg.get("supplement_thread_url")
        elif post["type"] == "new_post":
            section_url = forum_cfg.get("section_url")

        logger.info("Posting %s to %s (dry_run=%s)...", post["id"], platform_key, dry_run)
        result = await post_to_forum(
            platform_key, credentials, post, thread_url, section_url, session_dir, dry_run=dry_run
        )

        if result.success:
            if not dry_run:
                mark_posted(queue_path, post["id"], result.url)
            logger.info("SUCCESS: %s → %s", post["id"], result.url)
        else:
            logger.error("FAILED: %s — %s", post["id"], result.error)


def post_reddit(config, dry_run: bool, post_id: Optional[str] = None):
    from platforms.reddit_poster import post_to_reddit

    reddit_cfg = config.get("reddit", {})
    if not reddit_cfg.get("enabled") and not dry_run:
        logger.info("Reddit is disabled in config.")
        return

    queue_path = CONTENT_DIR / "reddit_posts.json"
    posts = pending_posts(queue_path)
    if post_id:
        posts = [p for p in posts if p["id"] == post_id]

    if not posts:
        logger.info("No pending Reddit posts.")
        return

    credentials = {
        "client_id": reddit_cfg.get("client_id", ""),
        "client_secret": reddit_cfg.get("client_secret", ""),
        "username": reddit_cfg.get("username", ""),
        "password": reddit_cfg.get("password", ""),
    }

    for post in posts:
        if has_unfilled_placeholders(post) and not dry_run:
            logger.warning("Skipping %s — contains unfilled placeholders.", post["id"])
            continue

        logger.info("Posting %s to Reddit (dry_run=%s)...", post["id"], dry_run)
        result = post_to_reddit(post, credentials, dry_run=dry_run)

        if result.success:
            if not dry_run:
                mark_posted(queue_path, post["id"], result.reddit_url)
            logger.info("SUCCESS: %s → %s", post["id"], result.reddit_url)
        else:
            logger.error("FAILED: %s — %s", post["id"], result.error)


def post_facebook(config, dry_run: bool, post_id: Optional[str] = None):
    from platforms.facebook import post_to_facebook

    fb_cfg = config.get("facebook", {})
    if not fb_cfg.get("enabled") and not dry_run:
        logger.info("Facebook is disabled in config.")
        return

    queue_path = CONTENT_DIR / "facebook_posts.json"
    posts = pending_posts(queue_path)
    if post_id:
        posts = [p for p in posts if p["id"] == post_id]

    if not posts:
        logger.info("No pending Facebook posts.")
        return

    for post in posts:
        if has_unfilled_placeholders(post) and not dry_run:
            logger.warning("Skipping %s — contains unfilled price placeholders.", post["id"])
            continue

        logger.info("Posting %s to Facebook (dry_run=%s)...", post["id"], dry_run)
        result = post_to_facebook(
            post,
            page_id=fb_cfg.get("page_id", ""),
            page_access_token=fb_cfg.get("page_access_token", ""),
            dry_run=dry_run,
        )

        if result.success:
            if not dry_run:
                mark_posted(queue_path, post["id"], result.facebook_post_id)
            logger.info("SUCCESS: %s → %s", post["id"], result.facebook_post_id)
        else:
            logger.error("FAILED: %s — %s", post["id"], result.error)


async def cmd_post(args, config):
    dry_run = args.dry_run or config.get("settings", {}).get("dry_run", True)
    if dry_run:
        logger.info("DRY RUN MODE — nothing will actually be posted")

    platform = getattr(args, "platform", None)
    post_id = getattr(args, "id", None)

    if platform == "forums" or post_id:
        await post_forums(config, dry_run, post_id)
    if platform == "reddit" or post_id:
        post_reddit(config, dry_run, post_id)
    if platform == "facebook" or post_id:
        post_facebook(config, dry_run, post_id)
    if platform == "all":
        await post_forums(config, dry_run)
        post_reddit(config, dry_run)
        post_facebook(config, dry_run)


# ─────────────────────────────────────────
# Cron command (one item per platform per run)
# ─────────────────────────────────────────

async def cmd_cron(args, config):
    """
    Designed to be called by a cron job or Paperclip heartbeat.
    Posts one pending item per enabled platform per invocation.
    Skips posts with unfilled placeholders.
    """
    dry_run = config.get("settings", {}).get("dry_run", True)
    logger.info("Cron run — dry_run=%s", dry_run)

    # Forums: post one pending item
    queue_path = CONTENT_DIR / "forum_posts.json"
    pending = [p for p in pending_posts(queue_path) if not has_unfilled_placeholders(p)]
    if pending:
        await post_forums(config, dry_run, post_id=pending[0]["id"])

    # Reddit: post one pending item
    queue_path = CONTENT_DIR / "reddit_posts.json"
    pending = [p for p in pending_posts(queue_path) if not has_unfilled_placeholders(p)]
    if pending:
        post_reddit(config, dry_run, post_id=pending[0]["id"])

    # Facebook: post one pending item
    queue_path = CONTENT_DIR / "facebook_posts.json"
    pending = [p for p in pending_posts(queue_path) if not has_unfilled_placeholders(p)]
    if pending:
        post_facebook(config, dry_run, post_id=pending[0]["id"])


# ─────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="suplementi.deals Social Posting CLI")
    parser.add_argument("--config", default="config.yml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command")

    # queue
    subparsers.add_parser("queue", help="Show pending posts")

    # verify
    subparsers.add_parser("verify", help="Verify platform credentials")

    # post
    post_parser = subparsers.add_parser("post", help="Post content")
    post_parser.add_argument(
        "--platform",
        choices=["forums", "reddit", "facebook", "all"],
        help="Which platform to post to",
    )
    post_parser.add_argument("--id", help="Post a specific item by ID")
    post_parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")

    # mark-done
    mark_parser = subparsers.add_parser("mark-done", help="Mark a post as done manually")
    mark_parser.add_argument("--id", required=True, help="Post ID to mark done")

    # cron
    subparsers.add_parser("cron", help="Cron/heartbeat mode: post one item per platform")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path
    config = load_config(config_path)

    # Set up file logging if configured
    log_file = config.get("settings", {}).get("log_file")
    if log_file:
        fh = logging.FileHandler(BASE_DIR / log_file)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)

    if args.command == "queue":
        cmd_queue(args, config)
    elif args.command == "verify":
        cmd_verify(args, config)
    elif args.command == "mark-done":
        cmd_mark_done(args, config)
    elif args.command == "post":
        asyncio.run(cmd_post(args, config))
    elif args.command == "cron":
        asyncio.run(cmd_cron(args, config))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
