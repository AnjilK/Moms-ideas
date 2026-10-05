import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Config, load_env
from .store import CATEGORIES, Store


class Telegram:
    def __init__(self, token):
        self.token = token
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method, payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base}/{method}", data=data, headers=headers)
        try:
            with urlopen(request, timeout=35) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram {method} failed: {error.code} {detail}") from error
        if not result.get("ok"):
            raise RuntimeError(result)
        return result["result"]

    def get_updates(self, offset=None, timeout=25):
        query = {"timeout": timeout}
        if offset is not None:
            query["offset"] = offset
        url = f"{self.base}/getUpdates?{urlencode(query)}"
        try:
            with urlopen(url, timeout=timeout + 10) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram getUpdates failed: {error.code} {detail}") from error
        if not result.get("ok"):
            raise RuntimeError(result)
        return result["result"]

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def answer_callback_query(self, callback_query_id, text=None):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return self.call("answerCallbackQuery", payload)

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        payload = {"chat_id": chat_id, "message_id": message_id}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("editMessageReplyMarkup", payload)

    def edit_message_text(self, chat_id, message_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("editMessageText", payload)

    def get_file(self, file_id):
        return self.call("getFile", {"file_id": file_id})

    def download_file(self, file_path, destination):
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        with urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())


def inline_keyboard(rows):
    return {"inline_keyboard": rows}


def button(text, data):
    return {"text": text, "callback_data": data}


def safe_answer_callback(api, callback_id, text=None):
    try:
        api.answer_callback_query(callback_id, text)
    except RuntimeError as error:
        print(f"Telegram callback acknowledgement skipped: {error}")


def safe_edit_message_text(api, chat_id, message_id, text, reply_markup=None):
    try:
        api.edit_message_text(chat_id, message_id, text, reply_markup)
    except RuntimeError as error:
        print(f"Telegram message edit skipped: {error}")


def category_keyboard(item_id):
    rows = []
    for index, category in enumerate(CATEGORIES):
        rows.append([button(category, f"cat:{item_id}:{index}")])
    return inline_keyboard(rows)


def destination_keyboard(item):
    item_id = item["id"]
    return inline_keyboard([
        [button("Website", f"dest:{item_id}:website")],
        [button("Facebook later", f"later:{item_id}:facebook"), button("X later", f"later:{item_id}:x")],
    ])


def approval_keyboard(item_id):
    return inline_keyboard([
        [button("Approve Website", f"approve:{item_id}:website")],
    ])


def source_key(message):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    digest = hashlib.sha256(f"{chat_id}:{message_id}".encode("utf-8")).hexdigest()[:16]
    return f"telegram:{digest}"


def message_text(message):
    text = message.get("text") or message.get("caption") or ""
    return text.strip()


def image_extension(file_path):
    suffix = Path(file_path).suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".webp"):
        return suffix
    return ".jpg"


def save_photo(api, store, message):
    photos = message.get("photo") or []
    if not photos:
        return None
    photo = max(photos, key=lambda candidate: candidate.get("file_size", 0))
    file_info = api.get_file(photo["file_id"])
    digest = hashlib.sha256(file_info["file_unique_id"].encode("utf-8")).hexdigest()[:16]
    destination = store.root / "images" / f"{digest}{image_extension(file_info['file_path'])}"
    if not destination.exists():
        api.download_file(file_info["file_path"], destination)
    return str(destination)


def handle_message(api, store, allowed_users, message):
    user = message.get("from") or {}
    user_id = user.get("id")
    chat_id = message["chat"]["id"]

    if user_id not in allowed_users:
        return

    text = message_text(message)
    if text == "/start":
        api.send_message(
            chat_id,
            "Hello. Send me a finished note, and I will save it for Mom's Ideas.",
        )
        return

    image = save_photo(api, store, message)
    if not text and not image:
        api.send_message(chat_id, "Please send text or a photo.")
        return
    if not text:
        text = "A picture from Mom"

    item = store.create(source_key(message), user_id, chat_id, text, image=image)
    image_line = "\nImage: saved" if image else ""
    api.send_message(
        chat_id,
        "Saved this note.\n\n"
        f"Title: {item['title']}\n"
        f"Category: {item['category']}"
        f"{image_line}\n\n"
        "Choose a category.",
        category_keyboard(item["id"]),
    )


def handle_callback(api, store, allowed_users, callback):
    user = callback.get("from") or {}
    user_id = user.get("id")
    if user_id not in allowed_users:
        safe_answer_callback(api, callback["id"])
        return

    message = callback["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    parts = callback.get("data", "").split(":")

    if len(parts) != 3:
        safe_answer_callback(api, callback["id"], "I could not understand that button.")
        return

    action, item_id, value = parts
    item = store.get(item_id)
    if not item:
        safe_answer_callback(api, callback["id"], "That note was not found.")
        return

    if action == "cat":
        try:
            category = CATEGORIES[int(value)]
        except (ValueError, IndexError):
            safe_answer_callback(api, callback["id"], "Unknown category")
            return
        store.set_category(item_id, category)
        store.set_mode(item_id, "publish")
        item = store.get(item_id)
        safe_answer_callback(api, callback["id"], "Category selected")
        safe_edit_message_text(
            api,
            chat_id,
            message_id,
            f"Saved this note.\n\nTitle: {item['title']}\nCategory: {category}\n\nSelected category: {category}",
        )
        api.send_message(
            chat_id,
            "Where should we publish it?",
            destination_keyboard(item),
        )
        return

    if action == "mode":
        safe_answer_callback(api, callback["id"], "This step is no longer needed.")
        safe_edit_message_text(api, chat_id, message_id, "This step is no longer needed. Please send the note again if you want to publish it.")
        return

    if action == "dest":
        safe_answer_callback(api, callback["id"], "Website selected")
        store.toggle(item_id, value)
        store.finish_selection(item_id)
        safe_edit_message_text(api, chat_id, message_id, "Selected destination: Website")
        api.send_message(
            chat_id,
            "Website selected. The note is queued for preparation.\n\n"
            "The worker will publish it to the local website.",
        )
        return

    if action == "approve":
        safe_answer_callback(api, callback["id"], "Review is no longer used.")
        safe_edit_message_text(api, chat_id, message_id, "Review is no longer used. New notes publish after category and destination are selected.")
        return

    if action == "later":
        safe_answer_callback(api, callback["id"], f"{value} is not connected yet.")
        return

    safe_answer_callback(api, callback["id"], "I could not understand that button.")


def deliver_notices(api, store, base_url):
    for notice in store.notices():
        item = store.get(notice["item_id"])
        if not item:
            store.notice_done(notice["id"])
            continue

        chat_id = item["chat_id"]
        if notice["kind"] == "review":
            preview_url = base_url + "/preview/" + item["preview_token"]
            text = (
                "This note is ready for review.\n\n"
                f"Title: {item['title']}\n"
                f"Category: {item['category']}\n\n"
                f"{preview_url}"
            )
            api.send_message(chat_id, text, approval_keyboard(item["id"]))
            store.notice_done(notice["id"])
            continue
        else:
            target = store.target(item["id"], notice["destination"])
            if target and target["status"] == "published":
                url = target["url"] or ""
                if url.startswith("/"):
                    url = base_url + url
                text = f"Published to {notice['destination']}.\n\n{url}"
            elif target:
                text = f"{notice['destination']} failed: {target['error'] or 'Unknown error'}"
            else:
                text = f"{notice['destination']} finished, but I could not find the result."

        api.send_message(chat_id, text)
        store.notice_done(notice["id"])


def main():
    load_env()
    config = Config()
    config.validate()
    if not config.telegram_token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env first.")

    api = Telegram(config.telegram_token)
    store = Store(config.data_dir)
    updates = api.get_updates(timeout=1)
    offset = updates[-1]["update_id"] + 1 if updates else None
    last_notice_check = 0

    print("Telegram bot is listening. Press Ctrl+C to stop.")
    while True:
        try:
            if time.monotonic() - last_notice_check >= 2:
                deliver_notices(api, store, config.base_url)
                last_notice_check = time.monotonic()
            for update in api.get_updates(offset=offset):
                offset = update["update_id"] + 1
                message = update.get("message")
                callback = update.get("callback_query")
                if message:
                    handle_message(api, store, set(config.allowed_users), message)
                if callback:
                    handle_callback(api, store, set(config.allowed_users), callback)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
            print(f"Telegram polling error: {error}")
            time.sleep(5)


if __name__ == "__main__":
    main()
