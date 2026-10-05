from .config import Config, load_env
from .store import Store


SAMPLES = [
    (
        "Beetroot Carrot Lemon Juice",
        "Food & Juices",
        """Beetroot Carrot Lemon Juice

This is a simple morning juice I like making with beetroot, carrot, lemon, and a small piece of ginger.

It tastes earthy and bright, and it feels like a gentle way to start the day. I like to drink a small glass slowly rather than making too much.""",
        "nutrition",
    ),
    (
        "A Small Thought For Low Days",
        "Depression Journey",
        """A Small Thought For Low Days

Some days ask for very small steps. Open the curtains. Drink water. Sit near a window. Message one person.

Healing is not always a big brave speech. Sometimes it is one quiet thing done with care.""",
        "mental health",
    ),
    (
        "The Line I Underlined Twice",
        "Books & Quotes",
        """The Line I Underlined Twice

I love when a book gives one sentence that stays with me all day. The best lines do not shout. They sit beside you and keep you company.""",
        "",
    ),
]


def main():
    load_env()
    config = Config()
    store = Store(config.data_dir)
    for title, category, body, caution in SAMPLES:
        item = store.create("sample:" + title, 0, 0, body)
        store.edit_as_published_website(item["id"], title, category, body, caution=caution)
    print(f"Seeded {len(SAMPLES)} sample notes in {config.data_dir / 'mom_ideas.sqlite'}")


if __name__ == "__main__":
    main()
