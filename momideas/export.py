import shutil
from pathlib import Path

from .config import Config, load_env
from .store import CATEGORIES, Store
from .web import DISCLAIMER, SITE_NAME, TAGLINE, esc, excerpt, page, slug_category


PUBLIC_DIR = Path("public")


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def image_export_path(item):
    image = item.get("image")
    if not image:
        return ""
    source = Path(image)
    suffix = source.suffix.lower() or ".jpg"
    return f"/images/{item['id']}{suffix}"


def render_static_cards(items):
    if not items:
        return '<div class="empty">No published notes yet.</div>'
    cards = []
    for item in items:
        image_url = image_export_path(item)
        image = f'<img class="card-image" src="{esc(image_url)}" alt="">' if image_url else '<div class="card-top"></div>'
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


def render_home(items):
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
      {render_static_cards(items)}
      <p class="footer">{esc(DISCLAIMER)}</p>
    </main>"""
    return page("Home", body, show_admin=False)


def render_category(category, items):
    body = f"""
    <main class="shell" style="padding-top:38px">
      <h1>{esc(category)}</h1>
      <p class="lede">A gathered shelf of Mom's notes in this category.</p>
      <nav class="nav-chips"><a class="nav-chip" href="/">Latest</a>{''.join(f'<a class="nav-chip {"active" if c == category else ""}" href="/category/{slug_category(c)}">{esc(c)}</a>' for c in CATEGORIES)}</nav>
      {render_static_cards(items)}
    </main>"""
    return page(category, body, category, show_admin=False)


def render_post(item):
    paragraphs = "".join(f"<p>{esc(p)}</p>" for p in item["body"].splitlines() if p.strip())
    notice = '<div class="notice">' + esc(DISCLAIMER) + "</div>" if item.get("caution") else ""
    image_url = image_export_path(item)
    image = f'<img class="post-image" src="{esc(image_url)}" alt="">' if image_url else ""
    body = f"""
    <main class="shell">
      <article class="post">
        <div class="meta">{esc(item["category"])}</div>
        <h1>{esc(item["title"])}</h1>
        {image}
        <div class="post-body">{paragraphs}</div>
        {notice}
      </article>
    </main>"""
    return page(item["title"], body, item["category"], show_admin=False)


def export_site(store, output_dir=PUBLIC_DIR):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    static_root = Path("static")
    if static_root.exists():
        shutil.copytree(static_root, output_dir / "static")

    items = store.listing(public=True)
    write_text(output_dir / "index.html", render_home(items))

    for category in CATEGORIES:
        category_items = store.listing(public=True, category=category)
        write_text(output_dir / "category" / slug_category(category) / "index.html", render_category(category, category_items))

    for item in items:
        write_text(output_dir / "post" / item["id"] / "index.html", render_post(item))
        image = item.get("image")
        if image:
            source = Path(image)
            try:
                source.relative_to(store.root / "images")
            except ValueError:
                continue
            if source.exists() and source.is_file():
                suffix = source.suffix.lower() or ".jpg"
                copy_file(source, output_dir / "images" / f"{item['id']}{suffix}")

    return len(items)


def main():
    load_env()
    config = Config()
    store = Store(config.data_dir)
    count = export_site(store)
    print(f"Exported {count} published notes to {PUBLIC_DIR}/")


if __name__ == "__main__":
    main()
