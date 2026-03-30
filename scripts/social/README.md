# suplementi.deals Social Posting Automation

Automated content distribution for suplementi.deals across Serbian forums, Facebook, and Reddit.

## Architecture

```
scripts/social/
├── poster.py              ← Main CLI entry point
├── config.example.yml     ← Copy to config.yml and fill credentials
├── requirements.txt       ← Python dependencies
├── platforms/
│   ├── forum_sr.py        ← Playwright: realx3mforum, benchmark.rs, krstarica
│   ├── facebook.py        ← Facebook Graph API v21
│   └── reddit_poster.py   ← Reddit PRAW
└── content/
    ├── forum_posts.json   ← 8 Serbian forum drafts (from RSS-29)
    ├── reddit_posts.json  ← 9 Reddit drafts (from RSS-29)
    └── facebook_posts.json← 4 weekly FB templates (from RSS-30)
```

## Setup

```bash
cd scripts/social
pip install -r requirements.txt
playwright install chromium

cp config.example.yml config.yml
# Edit config.yml — add credentials, set dry_run: false when ready
```

## Usage

```bash
# See pending posts (what's in the queue)
python poster.py queue

# Dry-run (safe preview — prints what would be posted)
python poster.py post --platform forums --dry-run
python poster.py post --platform reddit --dry-run
python poster.py post --platform facebook --dry-run

# Post a specific item by ID
python poster.py post --id forum-b1 --dry-run

# Live posting (set dry_run: false in config.yml first)
python poster.py post --platform forums
python poster.py post --platform reddit

# Verify credentials
python poster.py verify

# Cron mode (post one item per platform, for automated scheduling)
python poster.py cron
```

## Platform Setup

### Serbian Forums (Playwright)

1. Create accounts manually on each forum (realx3mforum.com, forum.benchmark.rs, forum.krstarica.com)
2. Do at least 5-10 genuine non-promotional posts first to build account credibility
3. Find the supplement thread URLs and section URLs for new posts
4. Add credentials and URLs to `config.yml`
5. First run will save session cookies — subsequent runs reuse them

**Anti-detection features built in:**
- Randomised typing delays (human-like)
- Randomised pauses between actions
- Session cookie persistence
- User-agent rotation

### Facebook Graph API

One-time setup (do this manually):

1. Go to [developers.facebook.com](https://developers.facebook.com) → Create App
2. Add "Facebook Login" + "Pages API" products
3. Generate User Access Token with `pages_manage_posts` scope
4. Exchange for long-lived token:
   ```
   GET https://graph.facebook.com/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=YOUR_APP_ID
     &client_secret=YOUR_APP_SECRET
     &fb_exchange_token=SHORT_LIVED_TOKEN
   ```
5. Get Page Access Token:
   ```
   GET https://graph.facebook.com/YOUR_PAGE_ID?fields=access_token&access_token=LONG_LIVED_USER_TOKEN
   ```
6. Add `page_id` and `page_access_token` to `config.yml`

### Reddit (PRAW)

1. Complete the 30-day warmup schedule from RSS-29 first
2. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → Create App (type: script)
3. Add `client_id`, `client_secret`, `username`, `password` to `config.yml`
4. Account needs ≥50 karma before posting links will be allowed

## Content Queue

All post content lives in `content/*.json`. Each post has:
- `posted: false` → pending
- `posted: true` → done (won't be re-posted)
- `requires_price_fill: true` → fill `[FILL_PRICE]` placeholders with real prices before posting

**To add a new post**, append an entry to the relevant JSON file following the existing schema.

**To mark a post as manually done** (if you posted it outside this tool):
```bash
python poster.py mark-done --id forum-a1
```

## Cron / Heartbeat Scheduling

For automated execution, run in cron mode:
```bash
# Post once per day (crontab example)
0 18 * * 1-5 cd /path/to/scripts/social && python poster.py cron
```

Or trigger from Paperclip heartbeat. Cron mode posts one item per enabled platform per run, skipping posts with unfilled price placeholders.

## Priority Order (as per RSS-41)

| Priority | Platform | Status |
|----------|----------|--------|
| 1 | Serbian Forums (realx3m, benchmark.rs, krstarica) | Playwright automation ready |
| 2 | Facebook | Graph API ready (needs Page setup) |
| 3 | Reddit | PRAW ready (needs account warmup first) |
