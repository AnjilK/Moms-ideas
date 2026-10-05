import time

from .config import Config, load_env
from .deploy import deploy_public_site
from .store import CATEGORIES, Store


def guess_category(text):
    lower = text.lower()
    food_words = ("juice", "lemon", "ginger", "beetroot", "carrot", "food", "recipe")
    mood_words = ("mind", "mood", "anxiety", "depression", "low day", "sad")
    book_words = ("book", "quote", "reading")
    spiritual_words = ("prayer", "god", "faith", "spiritual", "blessing")
    if any(word in lower for word in food_words):
        return "Food & Juices"
    if any(word in lower for word in mood_words):
        return "Mind & Mood"
    if any(word in lower for word in book_words):
        return "Books & Quotes"
    if any(word in lower for word in spiritual_words):
        return "Spiritual / Inspirational Notes"
    return "Stories & Reflections"


def needs_caution(text):
    lower = text.lower()
    caution_words = (
        "medicine",
        "medication",
        "supplement",
        "depression",
        "anxiety",
        "treatment",
        "blood pressure",
        "diabetes",
    )
    return any(word in lower for word in caution_words)


def prepare_item(store, item):
    text = item["body"]
    category = item.get("category") or guess_category(text)
    if category not in CATEGORIES:
        category = "Stories & Reflections"
    caution = "Personal wellness note; show the site disclaimer." if needs_caution(text) else ""
    caption = item["title"]
    store.complete_preparation(item["id"], {
        "category": category,
        "note": "Prepared by the local worker.",
        "caution": caution,
        "website": "",
        "facebook": caption,
        "x": caption[:260],
    })
    print(f"Prepared {item['id']} for {category}.")


def publish_target(store, target, config):
    item_id = target["item_id"]
    destination = target["destination"]
    if destination == "website":
        store.result(item_id, "website", "published", external_id=item_id, url="/post/" + item_id)
        print(f"Published {item_id} to website.")
        if config.auto_deploy_public_site:
            try:
                print(deploy_public_site(store, reason=f"note {item_id}"))
            except Exception as error:
                print(f"Automatic Vercel deploy failed for {item_id}: {error}")
        return
    store.result(
        item_id,
        destination,
        "failed",
        error=f"{destination} publishing is not connected yet.",
    )
    print(f"Skipped {item_id} for {destination}; destination is not connected.")


def run_once(store, config):
    did_work = False
    item = store.claim_preparation()
    if item:
        prepare_item(store, item)
        did_work = True

    target = store.claim_publication()
    if target:
        publish_target(store, target, config)
        did_work = True

    return did_work


def main():
    load_env()
    config = Config()
    config.validate()
    store = Store(config.data_dir)
    store.recover()
    print("Mom's Ideas worker is running. Press Ctrl+C to stop.")
    while True:
        if not run_once(store, config):
            time.sleep(2)


if __name__ == "__main__":
    main()
