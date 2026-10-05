# Mom's Ideas

A local-first publishing system for turning Mom's finished notes into a simple website.

## What Exists Now

- A local website called **Notes From Mom**.
- A public homepage with latest published notes.
- Category pages for the initial content categories.
- Individual post pages.
- Telegram bot intake for text, photos, and photos with captions.
- Telegram category buttons before publishing.
- Telegram **Publish** / **Review** flow.
- Telegram website destination selection.
- Review mode with a private preview link and **Approve Website** button.
- A background worker that prepares queued notes and publishes website posts.
- Saved Telegram images display on post pages and as homepage thumbnails.
- A local publishing form at `/admin`.
- SQLite storage for notes and per-destination publish status.
- Demo seed data for trying the website immediately.
- A generated hero image saved in `static/hero-notes-from-mom.png`.

## Run The Local System

```bash
python3 -m momideas.web
python3 -m momideas.telegram_bot
python3 -m momideas.worker
```

Run those in separate terminal windows. Then open:

```text
http://127.0.0.1:8000
```

Optional demo seed data:

```bash
python3 -m momideas.demo
```

## Export The Public Website

The public website is exported as plain static files into `public/`:

```bash
python3 -m momideas.export
```

That command reads the published website notes from the private local SQLite database, copies the public hero image and published note images, and writes:

```text
public/index.html
public/category/.../index.html
public/post/.../index.html
public/images/...
public/static/...
```

Commit the refreshed `public/` folder whenever Mom is ready to test a new public version.

## Current Local Publishing Flow

```text
Open /admin
  -> paste a finished note
  -> choose a category
  -> click Publish to website
  -> note is saved into SQLite
  -> website reads published notes from SQLite
  -> homepage/category/post pages update locally
```

## Current Telegram Publishing Flow

```text
Send text, photo, or photo with caption to Telegram bot
  -> bot saves original text/image into SQLite and data/images
  -> bot asks for category
  -> bot asks Publish or Review
  -> bot asks destination
  -> choose Website
```

Publish mode:

```text
Website selected
  -> worker prepares the note
  -> worker marks website target published
  -> bot sends published local link
```

Review mode:

```text
Website selected
  -> worker prepares draft
  -> bot sends private /preview/<token> link
  -> tap Approve Website
  -> worker publishes
  -> bot sends published local link
```

Telegram button feedback now edits the tapped message to show what was selected. Telegram does not allow bots to change button colours directly.

SQLite lives at:

```text
data/mom_ideas.sqlite
```

The database is intentionally ignored by Git because it is local runtime state. It can contain private drafts, originals, failures, and future Telegram submission history.

## Where SQLite Fits

SQLite is the private local source of truth on the Mac Studio.

It stores:

- the note title, body, category, and original text
- image file paths when images are added later
- whether the website destination is `draft`, `queued`, `published`, `failed`, or `unknown`
- future publish status for Facebook and X
- events and notices for retries or review

Images should be stored as files, not inside SQLite. SQLite should store the local image path, for example:

```text
data/images/2026/10/beetroot-juice-original.jpg
```

When the site is exported for public hosting, the image can be copied into a public static folder and referenced by URL.

Current local image files are stored under:

```text
data/images/
```

They are served locally through note-specific `/image/<item_id>` routes.

## Inspect The Database

From the project folder:

```bash
sqlite3 data/mom_ideas.sqlite
```

Useful commands:

```sql
.tables
.headers on
.mode column
select id, title, category from items;
select item_id, destination, status, url from targets;
select id, title, category, phase, mode, selected from items order by created_at desc limit 10;
```

Exit with:

```sql
.quit
```

One-shot example:

```bash
sqlite3 data/mom_ideas.sqlite "select id, title, category from items;"
```

## Vercel Flow

The live Vercel website serves the committed static export from `public/`. SQLite stays private on the Mac Studio rather than being used as Vercel's live database.

Recommended first public-version flow:

```text
Telegram
  -> Mac Studio bot
  -> SQLite draft/publish state
  -> static website export
  -> Git commit and push to GitHub
  -> Vercel rebuilds and publishes
```

This keeps Mom's workflow private and local, while Vercel only serves clean public files.

First setup in Vercel:

```text
New Project
  -> Import https://github.com/AnjilK/Moms-ideas
  -> Framework Preset: Other
  -> Build Command: leave empty / none
  -> Output Directory: public
  -> Deploy
```

`vercel.json` is already configured for the committed `public/` folder.

Updating the public site:

```bash
python3 -m momideas.export
git add public momideas/export.py momideas/web.py vercel.json README.md
git commit -m "Add static website export"
git push
```

After the first import, each push to GitHub should trigger a Vercel deployment.

Optional automatic Vercel updates:

```env
AUTO_DEPLOY_PUBLIC_SITE=1
```

When this is set in `.env`, the worker will automatically export `public/`, commit the changed public files, and push to GitHub after a website note is published. Vercel then redeploys from GitHub.

## GitHub

The local repository has been initialized and linked to:

```text
https://github.com/AnjilK/Moms-ideas.git
```

Project files have been staged for the first commit. Local runtime data under `data/` is ignored.

## Current Gaps

- Facebook and X buttons are placeholders only; API credentials and adapters are not connected.
- Website publishing is still local SQLite-backed; Vercel export/publish is planned next.
- Review previews are local links, not public internet links.
- No OCR, voice transcription, or scheduling yet.
