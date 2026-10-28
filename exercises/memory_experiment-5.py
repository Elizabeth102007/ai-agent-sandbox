
from langgraph.store.memory import InMemoryStore


def main():
    namespace = ("restart-test",)

    # This store starts empty.
    store = InMemoryStore()

    print("At startup:")
    print(store.search(namespace))

    store.put(
        namespace,
        "example",
        {"text": "This memory exists only in this process."},
        index=False,
    )

    print("\nAfter writing:")
    print(store.search(namespace))


if __name__ == "__main__":
    main()
