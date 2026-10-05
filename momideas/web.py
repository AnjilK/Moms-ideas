import hashlib
import html
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .config import Config, load_env
from .store import CATEGORIES, Store


SITE_NAME = "Notes From Mom"
TAGLINE = "Food, books, hope, and small ideas for better days."
DISCLAIMER = (
    "Personal wellness notes are shared from lived experience and are not medical advice. "
    "Please speak with a qualified professional before changing treatment, medication, "
    "supplements, or diet."
)


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def excerpt(text, length=170):
    clean = " ".join((text or "").split())
    if len(clean) <= length:
        return clean
    return clean[: length - 1].rsplit(" ", 1)[0] + "..."


def slug_category(category):
    return quote(category.lower().replace("&", "and").replace("/", "").replace(" ", "-"))


def unslug_category(slug):
    normalized = unquote(slug)
    for category in CATEGORIES:
        if slug_category(category) == normalized:
            return category
    return None


def item_image_url(item):
    return f'/image/{quote(item["id"])}' if item.get("image") else ""


def page(title, body, active=None, show_admin=True):
    nav_categories = "".join(
        f'<a class="nav-chip {"active" if active == c else ""}" href="/category/{slug_category(c)}">{esc(c)}</a>'
        for c in CATEGORIES
    )
    admin_link = '<a class="admin-link" href="/admin">Publish locally</a>' if show_admin else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - {SITE_NAME}</title>
  <style>
    :root {{
      --ink: #20211d;
      --muted: #686b5f;
      --paper: #fbfaf4;
      --panel: #ffffff;
      --sage: #7d9a74;
      --berry: #9d405b;
      --gold: #d9a441;
      --line: #e3dfd2;
      --shadow: 0 18px 45px rgba(53, 48, 35, .10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(125,154,116,.18), transparent 310px),
        var(--paper);
    }}
    a {{ color: inherit; }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 14px clamp(18px, 5vw, 56px);
      border-bottom: 1px solid rgba(75,72,58,.12);
      background: rgba(251,250,244,.88);
      backdrop-filter: blur(14px);
    }}
    .brand {{ text-decoration: none; font-weight: 800; letter-spacing: 0; }}
    .admin-link {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 13px;
      text-decoration: none;
      color: var(--muted);
      background: rgba(255,255,255,.68);
      white-space: nowrap;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(280px, .9fr);
      gap: clamp(24px, 5vw, 64px);
      align-items: center;
      padding: clamp(34px, 7vw, 86px) clamp(18px, 5vw, 56px) 34px;
      max-width: 1180px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0;
      max-width: 760px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(42px, 7vw, 86px);
      line-height: .96;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .lede {{ margin: 20px 0 0; max-width: 650px; color: var(--muted); font-size: 20px; }}
    .hero-photo {{
      min-height: 360px;
      border-radius: 8px;
      box-shadow: var(--shadow);
      background:
        linear-gradient(145deg, rgba(32,33,29,.12), rgba(32,33,29,0)),
        url("/static/hero-notes-from-mom.png") center / cover;
      position: relative;
      overflow: hidden;
    }}
    .hero-photo:after {{
      content: "Notes, recipes, reflections";
      position: absolute;
      left: 24px;
      right: 24px;
      bottom: 22px;
      padding-top: 18px;
      border-top: 1px solid rgba(32,33,29,.18);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 28px;
    }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 0 clamp(18px, 5vw, 56px) 70px; }}
    .nav-chips {{ display: flex; gap: 9px; flex-wrap: wrap; margin: 18px 0 32px; }}
    .nav-chip {{
      text-decoration: none;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.72);
      border-radius: 999px;
      color: var(--muted);
      padding: 8px 12px;
      font-size: 14px;
    }}
    .nav-chip.active, .nav-chip:hover {{ border-color: var(--sage); color: var(--ink); background: #fff; }}
    .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 20px; margin: 26px 0 16px; }}
    h2 {{ margin: 0; font-size: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .card {{
      min-height: 238px;
      display: flex;
      flex-direction: column;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.82);
      box-shadow: 0 10px 26px rgba(53,48,35,.06);
      overflow: hidden;
    }}
    .card-top {{ height: 8px; background: linear-gradient(90deg, var(--sage), var(--gold), var(--berry)); }}
    .card-image {{
      display: block;
      width: 100%;
      aspect-ratio: 16 / 10;
      object-fit: cover;
      border-bottom: 1px solid var(--line);
      background: #eee7d8;
    }}
    .card-body {{ padding: 18px; display: flex; flex: 1; flex-direction: column; }}
    .meta {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    .card h3 {{ margin: 8px 0 8px; font-size: 22px; line-height: 1.15; }}
    .card p {{ margin: 0; color: var(--muted); }}
    .read {{ margin-top: auto; padding-top: 18px; font-weight: 700; text-decoration: none; color: var(--berry); }}
    .post {{
      max-width: 780px;
      margin: 22px auto 0;
      padding: clamp(20px, 4vw, 42px);
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.88);
      box-shadow: var(--shadow);
    }}
    .post h1 {{ font-size: clamp(38px, 6vw, 64px); }}
    .post-image {{
      display: block;
      width: 100%;
      max-height: 620px;
      object-fit: contain;
      margin: 24px 0 0;
      border-radius: 8px;
      background: #f0ecdf;
    }}
    .post-body {{ margin-top: 24px; font-size: 19px; }}
    .post-body p {{ margin: 0 0 18px; }}
    .notice {{ border-left: 4px solid var(--gold); padding: 12px 14px; background: #fff8df; color: #5d4a19; }}
    .empty {{ padding: 28px; border: 1px dashed var(--line); border-radius: 8px; color: var(--muted); background: rgba(255,255,255,.58); }}
    form {{ display: grid; gap: 12px; }}
    label {{ font-weight: 700; }}
    input, textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      background: #fff;
    }}
    textarea {{ min-height: 220px; resize: vertical; }}
    button {{
      width: fit-content;
      border: 0;
      border-radius: 8px;
      background: var(--berry);
      color: #fff;
      padding: 11px 16px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }}
    .footer {{ color: var(--muted); font-size: 14px; margin-top: 36px; }}
    @media (max-width: 820px) {{
      .hero {{ grid-template-columns: 1fr; padding-top: 30px; }}
      .hero-photo {{ min-height: 230px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .topbar {{ align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/">{SITE_NAME}</a>
    {admin_link}
  </header>
  {body}
</body>
</html>"""


def render_cards(items):
    if not items:
        return '<div class="empty">No published notes yet. Add the first one from the local publishing page.</div>'
    cards = []
    for item in items:
        image = f'<img class="card-image" src="{esc(item_image_url(item))}" alt="">' if item.get("image") else '<div class="card-top"></div>'
        cards.append(f"""
        <article class="card">
          {image}
          <div class="card-body">
            <div class="meta">{esc(item["category"])}</div>
            <h3>{esc(item["title"])}</h3>
            <p>{esc(excerpt(item["body"]))}</p>
            <a class="read" href="/post/{esc(item["id"])}">Read note</a>
          </div>
        </article>""")
    return '<div class="grid">' + "".join(cards) + '</div>'


class WebsiteHandler(BaseHTTPRequestHandler):
    store = None
    static_root = Path("static")

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_html(self, body, status=HTTPStatus.OK):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def redirect(self, location):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            return self.home()
        if path.startswith("/category/"):
            return self.category(path.rsplit("/", 1)[-1])
        if path.startswith("/post/"):
            return self.post(path.rsplit("/", 1)[-1])
        if path.startswith("/preview/"):
            return self.preview(path.rsplit("/", 1)[-1])
        if path.startswith("/image/"):
            return self.image_file(path.rsplit("/", 1)[-1])
        if path == "/admin":
            return self.admin()
        if path.startswith("/static/"):
            return self.static_file(path.removeprefix("/static/"))
        return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Page not found.</div></main>'), HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if urlsplit(self.path).path != "/admin/publish":
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Page not found.</div></main>'), HTTPStatus.NOT_FOUND)
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        title = form.get("title", [""])[0].strip()
        category = form.get("category", [CATEGORIES[0]])[0]
        body = form.get("body", [""])[0].strip()
        if not title or not body or category not in CATEGORIES:
            return self.admin("Please add a title, category, and note body.")
        digest = hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()[:16]
        source_key = "local-admin:" + digest
        item = self.store.create(source_key, 0, 0, body)
        self.store.edit_as_published_website(item["id"], title, category, body)
        self.redirect("/post/" + item["id"])

    def static_file(self, name):
        if "/" in name or "\\" in name:
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">File not found.</div></main>'), HTTPStatus.NOT_FOUND)
        path = self.static_root / name
        if not path.exists() or not path.is_file():
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">File not found.</div></main>'), HTTPStatus.NOT_FOUND)
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def image_file(self, ident):
        item = self.store.get(unquote(ident))
        if not item or not item.get("image"):
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Image not found.</div></main>'), HTTPStatus.NOT_FOUND)
        path = Path(item["image"])
        try:
            path.relative_to(self.store.root / "images")
        except ValueError:
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Image not found.</div></main>'), HTTPStatus.NOT_FOUND)
        if not path.exists() or not path.is_file():
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Image not found.</div></main>'), HTTPStatus.NOT_FOUND)
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def home(self):
        items = self.store.listing(public=True)
        body = f"""
        <section class="hero">
          <div>
            <h1>{SITE_NAME}</h1>
            <p class="lede">{TAGLINE}</p>
          </div>
          <div class="hero-photo" aria-hidden="true"></div>
        </section>
        <main class="shell">
          <nav class="nav-chips"><a class="nav-chip active" href="/">Latest</a>{''.join(f'<a class="nav-chip" href="/category/{slug_category(c)}">{esc(c)}</a>' for c in CATEGORIES)}</nav>
          <div class="section-head"><h2>Latest Notes</h2><span class="meta">{len(items)} published</span></div>
          {render_cards(items)}
          <p class="footer">{esc(DISCLAIMER)}</p>
        </main>"""
        self.send_html(page("Home", body))

    def category(self, slug):
        category = unslug_category(slug)
        if not category:
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Category not found.</div></main>'), HTTPStatus.NOT_FOUND)
        items = self.store.listing(public=True, category=category)
        body = f"""
        <main class="shell" style="padding-top:38px">
          <h1>{esc(category)}</h1>
          <p class="lede">A gathered shelf of Mom's notes in this category.</p>
          <nav class="nav-chips"><a class="nav-chip" href="/">Latest</a>{''.join(f'<a class="nav-chip {"active" if c == category else ""}" href="/category/{slug_category(c)}">{esc(c)}</a>' for c in CATEGORIES)}</nav>
          {render_cards(items)}
        </main>"""
        self.send_html(page(category, body, category))

    def post(self, ident):
        item = self.store.get(ident)
        target = self.store.target(ident, "website") if item else None
        if not item or not target or target["status"] != "published":
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Published note not found.</div></main>'), HTTPStatus.NOT_FOUND)
        self.render_post(item)

    def preview(self, token):
        item = self.store.by_token(token)
        if not item:
            return self.send_html(page("Not Found", '<main class="shell"><div class="empty">Preview not found.</div></main>'), HTTPStatus.NOT_FOUND)
        self.render_post(item, preview=True)

    def render_post(self, item, preview=False):
        paragraphs = "".join(f"<p>{esc(p)}</p>" for p in item["body"].splitlines() if p.strip())
        notice = '<div class="notice">' + esc(DISCLAIMER) + "</div>" if item.get("caution") else ""
        preview_notice = '<div class="notice">Private review preview. This note is not public yet.</div>' if preview else ""
        image = f'<img class="post-image" src="{esc(item_image_url(item))}" alt="">' if item.get("image") else ""
        body = f"""
        <main class="shell">
          <article class="post">
            {preview_notice}
            <div class="meta">{esc(item["category"])}</div>
            <h1>{esc(item["title"])}</h1>
            {image}
            <div class="post-body">{paragraphs}</div>
            {notice}
          </article>
        </main>"""
        self.send_html(page(item["title"], body, item["category"]))

    def admin(self, error=""):
        options = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in CATEGORIES)
        message = f'<div class="notice">{esc(error)}</div>' if error else ""
        body = f"""
        <main class="shell" style="padding-top:38px">
          <section class="post">
            <div class="meta">Local publishing</div>
            <h1>Publish a note</h1>
            <p class="lede">Paste a finished note here to publish it to this local website.</p>
            {message}
            <form method="post" action="/admin/publish">
              <label>Title<input name="title" required maxlength="100" placeholder="Beetroot Carrot Lemon Juice"></label>
              <label>Category<select name="category">{options}</select></label>
              <label>Note<textarea name="body" required placeholder="Paste Mom's finished note here..."></textarea></label>
              <button type="submit">Publish to website</button>
            </form>
          </section>
        </main>"""
        self.send_html(page("Publish", body))


def make_server(config):
    store = Store(config.data_dir)
    WebsiteHandler.store = store
    WebsiteHandler.static_root = Path("static")
    return ThreadingHTTPServer((config.host, config.port), WebsiteHandler)


def main():
    load_env()
    config = Config()
    config.validate()
    server = make_server(config)
    print(f"Serving {SITE_NAME} at http://{config.host}:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
