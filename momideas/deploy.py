import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .export import PUBLIC_DIR, export_site


def run_git(args):
    return subprocess.run(
        ["git"] + args,
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )


def public_site_changed():
    result = run_git(["status", "--porcelain", "--", str(PUBLIC_DIR)])
    return bool(result.stdout.strip())


def deploy_public_site(store, reason="website update"):
    count = export_site(store)
    if not public_site_changed():
        return f"Exported {count} published notes; no public site changes to deploy."

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_git(["add", str(PUBLIC_DIR)])
    run_git(["commit", "-m", f"Update public site ({reason}, {stamp})"])
    run_git(["push"])
    return f"Exported and pushed {count} published notes to GitHub."
