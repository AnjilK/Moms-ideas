# Mom's Ideas - Option 2 Roadmap

## Concept

Mom uses ChatGPT, Claude, or another AI chat tool to refine her rough ideas first. When she is happy with the final version, she sends that final text to a Telegram bot and says `publish`.

The Telegram bot then saves the content to the Mac Studio, lightly structures it with a local LLM, stores it in SQLite, and publishes it to the website.

This keeps Mom's creative workflow simple while giving the publishing system clean, structured data.

## High-Level Flow

```text
Notebook scribble / typed note / photo
        |
        v
Mom curates in ChatGPT / Claude / local LLM
        |
        v
Mom copies final version to Telegram bot
        |
        v
Mom types "publish"
        |
        v
Bot saves raw text to Mac Studio folder
        |
        v
Local LLM lightly structures the content
        |
        v
SQLite database
        |
        v
Website publish
        |
        v
Later: social posts, Substack, animations, videos
```

## Current Build Status

As of 5 October 2026, the project has a working local website plus a first Telegram-to-website publishing loop.

Built:

- Local website named **Notes From Mom**.
- Public homepage.
- Category pages.
- Individual post pages.
- Local `/admin` publishing form.
- SQLite database created automatically at `data/mom_ideas.sqlite`.
- Published website records are stored in SQLite with a `website` destination status.
- Telegram bot with authorized-user checking.
- Telegram intake for text, photos, and photos with captions.
- Telegram category selection buttons.
- Telegram **Publish** and **Review** buttons.
- Telegram website destination button.
- Background worker for preparation and website publishing.
- Review mode with a private preview link and **Approve Website** button.
- Local image storage in `data/images/`.
- Website image display on post pages and homepage cards.
- Demo content seeding with `python3 -m momideas.demo`.
- Local server with `python3 -m momideas.web`.
- Bot listener with `python3 -m momideas.telegram_bot`.
- Worker with `python3 -m momideas.worker`.
- Hero image asset at `static/hero-notes-from-mom.png`.

The current local admin flow is:

```text
/admin form
        |
        v
SQLite item + website target
        |
        v
Public local website pages
```

The current Telegram flow is:

```text
Telegram text/photo/caption
        |
        v
Choose category
        |
        v
Choose Publish or Review
        |
        v
Choose Website
        |
        v
Worker prepares note
        |
        v
Publish immediately or send review preview
        |
        v
Public local website page
```

Facebook and X are not connected yet. Their buttons are placeholders for later API work.

For Vercel, the recommended first production approach is:

```text
Telegram
        |
        v
Mac Studio bot
        |
        v
SQLite private draft/publish state
        |
        v
Static website export
        |
        v
GitHub push
        |
        v
Vercel deploy
```

In this model, SQLite stays on the Mac Studio. Vercel receives static public site files rather than using the local SQLite database directly.

## Why This Option Works

- Mom can use a familiar chat experience for curation.
- She does not need to log into a complicated CMS.
- The Telegram bot becomes the submission and publishing gate.
- The Mac Studio can store the original text, processed JSON, and database.
- SQLite is enough for the first version.
- The website can read from approved/published database records.
- Social media automation can be added later.

## Roles

| Role | Responsibility |
| --- | --- |
| Mom | Creates rough ideas, refines them with AI, sends final version to Telegram |
| Anjil | Builds and owns the workflow, website, database, and publishing process |
| Brother | Helps Mom locally if needed, especially with phone/Telegram setup |
| AI assistant | Helps refine, structure, categorise, summarise, and prepare posts |
| Telegram bot | Receives final content and publishing commands |
| Mac Studio | Runs bot listener, local LLM processing, database, and publishing scripts |

## Core User Flow

### 1. Mom Creates A Rough Idea

Example:

```text
Beetroot juice + carrot + lemon.
Good in morning.
Helps energy.
Do not drink too much.
```

This could come from:

- Notebook photo
- Typed note
- Voice note
- Existing WhatsApp message
- Old handwritten scribble
- Memory or story

### 2. Mom Refines It With AI

Mom uploads or types the rough idea into ChatGPT, Claude, or another AI tool.

She asks things like:

- Make this clearer.
- Make this warmer.
- Add ingredients.
- Make it suitable for a website post.
- Make it shorter for Facebook.
- Add a gentle health disclaimer.
- Keep my tone.

### 3. Mom Sends Final Version To Telegram Bot

Mom copies the final text and sends it to the bot.

Example:

```text
Beetroot Carrot Lemon Juice

This is a simple morning juice I like making with beetroot, carrot, lemon, and a small piece of ginger...
```

### 4. Mom Chooses Category And Publish/Review

The bot replies with category buttons:

```text
Food & Juices
Nutrition Notes
Supplements
Mind & Mood
Depression Journey
Books & Quotes
Stories & Reflections
Daily Wisdom
Spiritual / Inspirational Notes
```

After category selection, the bot asks:

```text
[Publish] [Review]
```

Then it asks for destination:

```text
[Website]
[Facebook later] [X later]
```

### 5. Bot Saves Raw And Processed Versions

The system saves:

- Original submitted text
- Structured JSON
- Database record
- Processing logs
- Any generated captions or summaries

### 6. Website Publishes The Approved Post

When Mom confirms, the content becomes visible on the website.

If Mom chose **Review**, the bot sends a private local preview link and an **Approve Website** button before publishing.

## Folder Structure On Mac Studio

```text
MomIdeas/
  inbox/
    text/
    images/
    voice/

  processed/
    json/
    markdown/

  database/
    mom_ideas.sqlite

  website_exports/
    posts/
    images/

  logs/
    bot.log
    processing.log
```

## SQLite Database Tables

### content_items

| Field | Type | Purpose |
| --- | --- | --- |
| id | integer | Primary key |
| title | text | Clean title |
| slug | text | URL-safe title |
| category | text | Main content category |
| raw_text | text | Original text Mom sent |
| body | text | Clean final body |
| summary | text | Short summary |
| status | text | draft / approved / published / archived |
| source | text | telegram_submission |
| language | text | English / Hindi / Malayalam / other |
| health_disclaimer_needed | boolean | Safety flag |
| created_at | datetime | Created timestamp |
| updated_at | datetime | Updated timestamp |
| published_at | datetime | Published timestamp |

### content_tags

| Field | Type | Purpose |
| --- | --- | --- |
| id | integer | Primary key |
| content_id | integer | Links to content item |
| tag | text | Searchable tag |

### publish_targets

| Field | Type | Purpose |
| --- | --- | --- |
| id | integer | Primary key |
| content_id | integer | Links to content item |
| target | text | website / facebook / x / substack |
| status | text | queued / published / failed |
| published_url | text | URL after publishing |
| published_at | datetime | Timestamp |

### content_versions

| Field | Type | Purpose |
| --- | --- | --- |
| id | integer | Primary key |
| content_id | integer | Links to content item |
| version_number | integer | Draft version |
| body | text | Version text |
| created_at | datetime | Timestamp |

## Content Categories

Initial categories:

- Food & Juices
- Nutrition Notes
- Supplements
- Mind & Mood
- Depression Journey
- Books & Quotes
- Stories & Reflections
- Daily Wisdom
- Spiritual / Inspirational Notes

## Local LLM Responsibilities

The local LLM should only lightly process the final text after Mom has approved it.

It should:

- Extract a clean title.
- Detect category.
- Generate tags.
- Generate a URL slug.
- Create a short summary.
- Format the post for the website.
- Detect if a health disclaimer is needed.
- Detect risky medical claims.
- Generate optional social captions.

It should not:

- Heavily rewrite Mom's approved text.
- Add unsupported health claims.
- Turn lived experience into medical advice.
- Publish mental health or supplement claims without caution.

## Safety Rules For Health And Mental Health Content

The system should add a gentle disclaimer for:

- Supplements
- Nutrition advice
- Depression or mental health posts
- Medication-adjacent claims
- Claims about treating, curing, or preventing illness

Suggested disclaimer:

```text
This is a personal wellness note based on lived experience. It is not medical advice. Please speak to a qualified health professional before making changes to treatment, medication, supplements, or diet, especially if you have a health condition.
```

For depression-related posts, add crisis-sensitive wording where appropriate:

```text
If you feel at risk of harming yourself or feel unsafe, please seek urgent help from local emergency services or a mental health crisis line.
```

## MVP Features

### Must Have

- Telegram bot receives text from Mom.
- Bot recognises `publish`.
- Bot stores raw text in local folder.
- Local LLM extracts title, category, tags, summary, and disclaimer flag.
- SQLite database stores the content item.
- Bot sends preview back to Mom.
- Mom confirms before publishing.
- Website displays published posts.

### Should Have

- Save as draft option.
- Edit title option.
- Category correction option.
- View latest submitted item.
- Simple admin page for Anjil/brother.
- Markdown export for each post.
- Basic search and category filters on website.

### Could Have Later

- Photo upload from Telegram.
- OCR for handwritten notes.
- Voice note transcription.
- Multiple languages.
- Social media caption generation.
- Auto-post to Facebook Page.
- Auto-post to X/Twitter.
- Substack draft generation.
- Image generation for recipe cards.
- Short animation or video generation.
- Scheduled publishing calendar.

## Publishing Roadmap

### Phase 1 - Manual AI Curation And Telegram Submission

Goal: prove the workflow with minimal build.

Features:

- Mom curates in ChatGPT or Claude.
- Mom sends final text to Telegram bot.
- Bot saves raw text to Mac Studio.
- Bot saves a basic SQLite record.
- Anjil manually publishes to website.

Success measure:

- 10 good posts captured and organised.

### Phase 2 - Structured Processing

Goal: make the data clean and reusable.

Features:

- Local LLM creates title, category, summary, tags, slug.
- Disclaimer detection.
- JSON export.
- Markdown export.
- Bot preview before saving.

Success measure:

- Each submitted item becomes a clean database record automatically.

### Phase 3 - Website Publishing

Goal: publish approved posts to a simple website.

Features:

- Website reads from SQLite or exported Markdown/JSON.
- Category pages.
- Individual post pages.
- Homepage with latest posts.
- Search/filter by category and tag.
- Basic disclaimer footer.

Success measure:

- Mom can submit and publish a website post through Telegram.

### Phase 4 - Review Dashboard

Goal: make management easy for Anjil and brother.

Features:

- Admin page showing drafts, approved posts, published posts.
- Edit title/body/category/tags.
- Change status.
- See publication URLs.
- Review health disclaimer flags.

Success measure:

- No need to inspect raw database files.

### Phase 5 - Social And Newsletter Distribution

Goal: repurpose content beyond the website.

Features:

- Generate Facebook caption.
- Generate X/Twitter thread.
- Generate Substack draft.
- Generate Instagram-style short caption.
- Queue posts for approval.
- Later add auto-posting APIs where practical.

Success measure:

- One website post can generate 3-5 social/newsletter variants.

### Phase 6 - Media Generation

Goal: turn selected posts into visual content.

Features:

- Recipe card images.
- Quote cards.
- Short narrated video scripts.
- Simple animations.
- Voiceover option.
- Social video export format.

Success measure:

- One approved post can become a simple video or shareable graphic.

## Recommended First Technical Build

Build these first:

1. Telegram bot.
2. Local folder save.
3. SQLite table.
4. Local LLM structuring prompt.
5. Bot preview and confirmation.
6. Website list of published posts.

Avoid these at the start:

- Full social media auto-posting.
- Complex CMS.
- Multi-user permissions.
- Video generation.
- WhatsApp automation.
- Heavy editing after Mom has approved content.

## Example Bot Conversation

```text
Mom:
Beetroot Carrot Lemon Juice

This is a simple morning juice I like making with beetroot, carrot, lemon and ginger...

Mom:
publish

Bot:
I have prepared this for publishing:

Title: Beetroot Carrot Lemon Juice
Category: Food & Juices
Tags: beetroot, carrot, lemon, ginger, morning
Disclaimer needed: Yes

Summary:
A simple morning juice with beetroot, carrot, lemon and ginger.

Publish now?

[Yes, publish] [Save as draft] [Edit title]

Mom:
Yes, publish

Bot:
Published.

Website URL:
https://example.com/food-juices/beetroot-carrot-lemon-juice
```

## Example Local LLM Prompt

```text
You are preparing one of Mom's approved notes for a website.

Do not heavily rewrite the note. Preserve her warm, personal tone.

Return JSON only with:
- title
- slug
- category
- summary
- tags
- body
- health_disclaimer_needed
- caution_notes
- suggested_social_caption

Rules:
- Do not add medical claims.
- Treat supplements, nutrition, depression, and health advice carefully.
- Add a disclaimer flag if needed.
- If the note makes a strong medical claim, mark it in caution_notes.

Approved note:
{{content}}
```

## Website Design Direction

Suggested site name:

```text
Notes From Mom
```

Suggested tagline:

```text
Food, books, hope, and small ideas for better days.
```

Suggested homepage sections:

- Latest Notes
- Food & Juices
- Mind & Mood
- Books & Quotes
- Stories & Reflections
- Mom's Favourites

Tone:

- Warm
- Calm
- Personal
- Trustworthy
- Not overly clinical
- Not influencer-style

## Key Decisions To Make

| Decision | Recommended Starting Choice |
| --- | --- |
| Input channel | Telegram bot |
| Curation tool | ChatGPT or Claude first |
| Submission command | `publish` |
| Storage | Mac Studio local folder + SQLite |
| AI processing | Local LLM via Ollama |
| First publishing target | Website only |
| Social media | Generate drafts first, auto-post later |
| Website style | Warm personal knowledge journal |

## Final Recommendation

Start with Option 2 as a practical bridge:

```text
ChatGPT/Claude for creative curation
Telegram bot for submission
Mac Studio for storage and processing
SQLite for structured content
Website for publishing
Social/video later
```

This gives Mom a simple workflow and gives the project a proper technical foundation without overbuilding too early.
