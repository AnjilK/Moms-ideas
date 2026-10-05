# Mom’s Ideas — implementation snapshot

Snapshot date: 5 October 2026. Requested destination: Spaces. Spaces could not be accessed through the connected tools; native app control was explicitly blocked. This file is the portable snapshot.

## Current status

- Mom sends text, one image, or an image with a caption to Telegram.
- The bot saves text and Telegram photos locally.
- The bot asks for category first, then asks **Publish** or **Review**, then asks destination.
- Current active destination: website.
- Facebook and X are visible as "later" placeholders only.
- Publish mode queues and publishes to the local website.
- Review mode sends a private preview link and an **Approve Website** Telegram button.
- Retain successful publications; retry failures without reposting successes.
- Preserve originals. No OCR, transcription, scheduling, or additional networks in v1.
- Telegram button taps now edit the selected message to make choices visible. Telegram does not allow custom button colours.

## Environment and setup

- Python 3.9.6 is available. Implementation will use Python’s standard library, SQLite, and Ollama with no required Python packages.
- `.env` exists locally and is ignored by Git.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` have been configured locally.
- Telegram allowed user currently used during testing: `8680596889`.
- The current local site runs from SQLite. For Vercel, SQLite should remain private on the Mac Studio and public pages should be exported to static files or moved to a hosted database later.
- Git has been initialized locally and the `origin` remote points to `https://github.com/AnjilK/Moms-ideas.git`. Project files are staged; runtime data remains ignored.

## Completed implementation

- Local public website at `python3 -m momideas.web`.
- Homepage, category pages, individual post pages, and `/admin` local publishing form.
- Website posts are stored in SQLite and marked as published for the `website` destination.
- Telegram bot at `python3 -m momideas.telegram_bot`.
- Background worker at `python3 -m momideas.worker`.
- Telegram text notes are saved into SQLite.
- Telegram photos are downloaded to `data/images/` and linked from SQLite.
- Telegram category buttons are implemented using the categories from `momideas.store.CATEGORIES`.
- Telegram **Publish** and **Review** buttons are implemented.
- Website destination selection is implemented.
- Review approval via Telegram **Approve Website** button is implemented.
- Private review previews are available at `/preview/<preview_token>`.
- Saved images are served through `/image/<item_id>`.
- Post pages display saved images.
- Homepage cards show image thumbnails when a note has an image.
- Demo seed data is available with `python3 -m momideas.demo`.
- Hero image asset saved at `static/hero-notes-from-mom.png`.
- SQLite database is created automatically at `data/mom_ideas.sqlite`.
- Images should be stored as files; SQLite should store image paths and metadata.
- Verified locally:
  - Python source compiles with `py_compile`.
  - Homepage responds.
  - Hero image serves.
  - `/admin` can publish a note and redirect to the new post page.
  - Temporary database flow verified: create item, set publish mode, choose website, worker prepares, worker publishes.
  - Bot, worker, and website have been run locally during testing.

## Current local admin flow

```text
Open /admin
  -> paste title/category/body
  -> publish
  -> create/update SQLite item
  -> create website target with status published
  -> public pages query SQLite for website published items
```

## Current Telegram flow

```text
Telegram text/photo/caption
  -> bot saves item and optional image
  -> choose category
  -> choose Publish or Review
  -> choose Website
```

Publish:

```text
Website selected
  -> item phase becomes preparing
  -> worker prepares item
  -> website target becomes queued
  -> worker publishes website target
  -> target status becomes published
  -> bot sends local /post/<id> link
```

Review:

```text
Website selected
  -> item phase becomes preparing
  -> worker prepares item
  -> website target remains draft
  -> bot sends /preview/<token> link
  -> user taps Approve Website
  -> target becomes queued
  -> worker publishes website target
  -> bot sends local /post/<id> link
```

## Run commands

Run each in a separate terminal:

```bash
cd /Users/anjilmacstudio/Moms-ideas
python3 -m momideas.web
```

```bash
cd /Users/anjilmacstudio/Moms-ideas
python3 -m momideas.telegram_bot
```

```bash
cd /Users/anjilmacstudio/Moms-ideas
python3 -m momideas.worker
```

Check running processes:

```bash
ps -axo pid,command | grep '[m]omideas.telegram_bot'
ps -axo pid,command | grep '[m]omideas.worker'
ps -axo pid,command | grep '[m]omideas.web'
```

Important: only one `momideas.telegram_bot` process should run. Multiple bot listeners cause Telegram `409 Conflict` errors.

## Recommended production flow for Vercel

```text
Telegram
  -> Mac Studio bot
  -> SQLite draft/review/publish state
  -> static website export
  -> Git commit and push
  -> GitHub
  -> Vercel rebuild
```

SQLite remains useful as the private control center for drafts, originals, duplicate prevention, retries, image paths, and future per-destination publishing.

## Remaining implementation work

- Add static website export and GitHub push for Vercel.
- Add protected local admin/review pages if needed.
- Add Ollama caption generation and X/Facebook adapters.
- Add real Facebook and X credentials and publisher adapters.
- Add failure handling, duplicate prevention, setup instructions, and meaningful offline tests.
- Update this file with the completed files, test results, and remaining setup needs.
