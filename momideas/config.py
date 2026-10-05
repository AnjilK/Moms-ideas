import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


def load_env(path=Path('.env')):
    """Read literal KEY=value pairs; never evaluate shell expressions."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"').strip("'"))


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv('DATA_DIR', 'data')))
    base_url: str = field(default_factory=lambda: os.getenv('BASE_URL', 'http://127.0.0.1:8000').rstrip('/'))
    host: str = field(default_factory=lambda: os.getenv('HOST', '127.0.0.1'))
    port: int = field(default_factory=lambda: int(os.getenv('PORT', '8000')))
    telegram_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    allowed_users: Tuple[int, ...] = field(default_factory=lambda: tuple(int(x.strip()) for x in os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',') if x.strip()))
    admin_password: str = field(default_factory=lambda: os.getenv('ADMIN_PASSWORD', ''))
    ollama_url: str = field(default_factory=lambda: os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'))
    ollama_model: str = field(default_factory=lambda: os.getenv('OLLAMA_MODEL', 'llama3.2:3b'))
    x_client_id: str = field(default_factory=lambda: os.getenv('X_CLIENT_ID', ''))
    x_client_secret: str = field(default_factory=lambda: os.getenv('X_CLIENT_SECRET', ''))
    x_access_token: str = field(default_factory=lambda: os.getenv('X_ACCESS_TOKEN', ''))
    x_refresh_token: str = field(default_factory=lambda: os.getenv('X_REFRESH_TOKEN', ''))
    fb_page_id: str = field(default_factory=lambda: os.getenv('FACEBOOK_PAGE_ID', ''))
    fb_token: str = field(default_factory=lambda: os.getenv('FACEBOOK_PAGE_TOKEN', ''))
    fb_version: str = field(default_factory=lambda: os.getenv('FACEBOOK_GRAPH_VERSION', ''))
    demo: bool = False
    max_image_bytes: int = 5 * 1024 * 1024

    def validate(self):
        from urllib.parse import urlsplit
        url = urlsplit(self.base_url)
        if url.scheme not in ('http', 'https') or not url.netloc or url.query or url.fragment or url.path:
            raise ValueError('BASE_URL must be a bare http(s) origin, with no path or query.')
        if self.telegram_token and not self.allowed_users:
            raise ValueError('Set TELEGRAM_ALLOWED_USERS before enabling the bot.')
        if self.admin_password and len(self.admin_password) < 16:
            raise ValueError('ADMIN_PASSWORD must contain at least 16 characters.')
