import contextlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone

DESTINATIONS = ('website', 'facebook', 'x')
CATEGORIES = ('Food & Juices', 'Nutrition Notes', 'Supplements', 'Mind & Mood',
              'Depression Journey', 'Books & Quotes', 'Stories & Reflections',
              'Daily Wisdom', 'Spiritual / Inspirational Notes')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Store:
    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        for folder in ('images', 'originals', 'logs'):
            (root / folder).mkdir(exist_ok=True)
        self.path = root / 'mom_ideas.sqlite'
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY, source_key TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
                    raw_text TEXT NOT NULL, body TEXT NOT NULL, image TEXT,
                    title TEXT NOT NULL, category TEXT NOT NULL,
                    mode TEXT, phase TEXT NOT NULL DEFAULT 'choosing',
                    selected TEXT NOT NULL DEFAULT '[]',
                    preview_token TEXT UNIQUE NOT NULL, csrf TEXT NOT NULL,
                    processing_note TEXT NOT NULL DEFAULT '',
                    caution TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS targets (
                    item_id TEXT NOT NULL REFERENCES items(id), destination TEXT NOT NULL,
                    caption TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, external_id TEXT,
                    url TEXT, error TEXT, updated_at TEXT NOT NULL,
                    PRIMARY KEY(item_id, destination)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, item_id TEXT, destination TEXT,
                    message TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY, item_id TEXT NOT NULL,
                    kind TEXT NOT NULL, destination TEXT, delivered INTEGER NOT NULL DEFAULT 0
                );
            ''')
        os.chmod(self.path, 0o600)

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, source_key, user_id, chat_id, text, image=None):
        ident = secrets.token_hex(8)
        title = text.strip().splitlines()[0][:100] if text.strip() else 'A picture from Mom'
        stamp = now()
        with self.db() as db:
            existing = db.execute('SELECT id FROM items WHERE source_key=?', (source_key,)).fetchone()
            if existing:
                return self.get(existing['id'])
            db.execute('''INSERT INTO items
                (id,source_key,user_id,chat_id,raw_text,body,image,title,category,preview_token,csrf,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ident, source_key, user_id, chat_id, text, text, image, title,
                 'Stories & Reflections', secrets.token_urlsafe(32), secrets.token_urlsafe(32), stamp, stamp))
        (self.root / 'originals' / (ident + '.json')).write_text(json.dumps(
            {'id': ident, 'source_key': source_key, 'text': text, 'image': image, 'created_at': stamp},
            ensure_ascii=False, indent=2))
        return self.get(ident)

    def get(self, ident):
        with self.db() as db:
            row = db.execute('SELECT * FROM items WHERE id=?', (ident,)).fetchone()
            return dict(row) if row else None

    def by_token(self, token):
        with self.db() as db:
            row = db.execute('SELECT * FROM items WHERE preview_token=?', (token,)).fetchone()
            return dict(row) if row else None

    def targets(self, ident):
        with self.db() as db:
            return [dict(x) for x in db.execute('SELECT * FROM targets WHERE item_id=? ORDER BY destination', (ident,))]

    def target(self, ident, dest):
        return next((t for t in self.targets(ident) if t['destination'] == dest), None)

    def set_mode(self, ident, mode):
        if mode not in ('publish', 'review'):
            raise ValueError('Choose Publish or Review.')
        with self.db() as db:
            db.execute("UPDATE items SET mode=?,updated_at=? WHERE id=? AND phase='choosing'", (mode, now(), ident))

    def set_category(self, ident, category):
        if category not in CATEGORIES:
            raise ValueError('Unknown category.')
        with self.db() as db:
            db.execute("UPDATE items SET category=?,updated_at=? WHERE id=? AND phase='choosing'",
                       (category, now(), ident))

    def toggle(self, ident, dest):
        if dest not in DESTINATIONS:
            raise ValueError('Unknown destination.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT selected FROM items WHERE id=? AND phase='choosing' AND mode IS NOT NULL", (ident,)).fetchone()
            if row:
                selected = json.loads(row['selected'])
                selected.remove(dest) if dest in selected else selected.append(dest)
                db.execute('UPDATE items SET selected=?,updated_at=? WHERE id=?', (json.dumps(selected), now(), ident))

    def finish_selection(self, ident):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM items WHERE id=? AND phase='choosing'", (ident,)).fetchone()
            if not row:
                return False
            destinations = json.loads(row['selected'])
            if not row['mode'] or not destinations:
                raise ValueError('Choose at least one destination.')
            for dest in destinations:
                db.execute('INSERT INTO targets (item_id,destination,status,updated_at) VALUES (?,?,?,?)',
                           (ident, dest, 'preparing', now()))
            db.execute("UPDATE items SET phase='preparing',updated_at=? WHERE id=?", (now(), ident))
            return True

    def complete_preparation(self, ident, result):
        with self.db() as db:
            row = db.execute("SELECT mode FROM items WHERE id=? AND phase='processing'", (ident,)).fetchone()
            if not row:
                return
            status = 'queued' if row['mode'] == 'publish' else 'draft'
            for dest in DESTINATIONS:
                caption = result.get(dest, '')
                db.execute('UPDATE targets SET caption=?,status=?,updated_at=? WHERE item_id=? AND destination=?',
                           (caption, status, now(), ident, dest))
            db.execute("UPDATE items SET phase='ready',category=?,processing_note=?,caution=?,updated_at=? WHERE id=?",
                       (result['category'], result['note'], result['caution'], now(), ident))
            if row['mode'] == 'review':
                db.execute("INSERT INTO notices (item_id,kind) VALUES (?, 'review')", (ident,))

    def claim_preparation(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM items WHERE phase='preparing' ORDER BY created_at LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE items SET phase='processing' WHERE id=?", (row['id'],))
                return dict(row)

    def approve(self, ident, dest):
        if dest not in DESTINATIONS:
            raise ValueError('Unknown destination.')
        with self.db() as db:
            return db.execute("UPDATE targets SET status='queued',error=NULL,updated_at=? WHERE item_id=? AND destination=? AND status IN ('draft','failed')",
                              (now(), ident, dest)).rowcount > 0

    def edit(self, ident, dest, text, title=None, category=None):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM targets WHERE item_id=? AND destination=?', (ident, dest)).fetchone()
            if not row or row['status'] not in ('draft', 'failed'):
                raise ValueError('Only drafts or failed destinations can be edited.')
            if dest == 'website':
                if category not in CATEGORIES or not title or not title.strip():
                    raise ValueError('Choose a category and a title.')
                db.execute('UPDATE items SET body=?,title=?,category=?,updated_at=? WHERE id=?',
                           (text, title.strip()[:100], category, now(), ident))
            else:
                db.execute('UPDATE targets SET caption=?,updated_at=? WHERE item_id=? AND destination=?', (text, now(), ident, dest))

    def edit_as_published_website(self, ident, title, category, body, caution=''):
        if category not in CATEGORIES:
            raise ValueError('Unknown category.')
        stamp = now()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''UPDATE items
                SET title=?, category=?, body=?, phase='ready', mode='publish',
                    caution=?, updated_at=?
                WHERE id=?''', (title.strip()[:100], category, body, caution, stamp, ident))
            db.execute('''INSERT INTO targets
                (item_id,destination,caption,status,attempts,external_id,url,error,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(item_id,destination) DO UPDATE SET
                    caption=excluded.caption,
                    status=excluded.status,
                    external_id=excluded.external_id,
                    url=excluded.url,
                    error=excluded.error,
                    updated_at=excluded.updated_at''',
                (ident, 'website', '', 'published', 1, ident, '/post/' + ident, None, stamp))

    def claim_publication(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM targets WHERE status='queued' ORDER BY updated_at LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE targets SET status='publishing',attempts=attempts+1,updated_at=? WHERE item_id=? AND destination=?",
                           (now(), row['item_id'], row['destination']))
                return dict(row)

    def result(self, ident, dest, status, external_id=None, url=None, error=None):
        with self.db() as db:
            db.execute('UPDATE targets SET status=?,external_id=?,url=?,error=?,updated_at=? WHERE item_id=? AND destination=?',
                       (status, external_id, url, error, now(), ident, dest))
            db.execute('INSERT INTO events (item_id,destination,message,created_at) VALUES (?,?,?,?)',
                       (ident, dest, status + (': ' + error if error else ''), now()))
            db.execute("INSERT INTO notices (item_id,kind,destination) VALUES (?,'result',?)", (ident, dest))

    def reconcile(self, ident, dest, external_id, url):
        """Admin records an ambiguous remote result without creating another post."""
        with self.db() as db:
            row = db.execute('SELECT status FROM targets WHERE item_id=? AND destination=?', (ident, dest)).fetchone()
            if not row or row['status'] != 'unknown':
                raise ValueError('Only unknown outcomes need reconciliation.')
            db.execute("UPDATE targets SET status='published',external_id=?,url=?,error=NULL,updated_at=? WHERE item_id=? AND destination=?",
                       (external_id, url, now(), ident, dest))

    def confirmed_not_published(self, ident, dest):
        with self.db() as db:
            db.execute("UPDATE targets SET status='failed',error='Administrator confirmed no remote post exists.',updated_at=? WHERE item_id=? AND destination=? AND status='unknown'",
                       (now(), ident, dest))

    def recover(self):
        with self.db() as db:
            db.execute("UPDATE items SET phase='preparing' WHERE phase='processing'")
            db.execute("UPDATE targets SET status='unknown',error='Service stopped during publication; inspect remote account before retrying.' WHERE status='publishing'")

    def listing(self, public=False, category=None):
        query = 'SELECT i.* FROM items i'
        args = []
        where = []
        if public:
            query += " JOIN targets t ON t.item_id=i.id AND t.destination='website' AND t.status='published'"
        if category:
            where.append('i.category=?')
            args.append(category)
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        query += ' ORDER BY i.created_at DESC LIMIT 100'
        with self.db() as db:
            return [dict(x) for x in db.execute(query, args)]

    def setting(self, key, default=None):
        with self.db() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default

    def set_setting(self, key, value):
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, str(value)))

    def notices(self):
        with self.db() as db:
            return [dict(x) for x in db.execute('SELECT * FROM notices WHERE delivered=0 ORDER BY id LIMIT 20')]

    def notice_done(self, ident):
        with self.db() as db:
            db.execute('UPDATE notices SET delivered=1 WHERE id=?', (ident,))
