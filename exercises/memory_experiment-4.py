

import asyncio

from langchain_openai import OpenAIEmbeddings
from langgraph.store.memory import InMemoryStore


# This is a demonstration threshold, not a universal value.
# Calibrate it against real queries and relevant/irrelevant examples.
MIN_SCORE = 0.35


async def main():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    store = InMemoryStore(
        index={
            "embed": embeddings,
            "dims": 1536,
            "fields": ["text"],
        }
    )

    user1_namespace = ("users", "user-1", "memories")
    user2_namespace = ("users", "user-2", "memories")

    user1_memories = {
        "memory-1": {
            "text": "The user enjoys hiking in the mountains on weekends."
        },
        "memory-2": {
            "text": "The user has a severe allergy to peanuts."
        },
        "memory-3": {
            "text": "The user works remotely as a software engineer."
        },
        "memory-4": {
            "text": "The user prefers quiet cafes when studying."
        },
    }

    user2_memories = {
        "memory-1": {
            "text": "The user enjoys playing the piano."
        },
        "memory-2": {
            "text": "The user is learning French."
        },
    }

    # Save and index user 1's memories.
    for key, value in user1_memories.items():
        await store.aput(
            user1_namespace,
            key,
            value,
            index=["text"],
        )

    # Save and index user 2's memories.
    for key, value in user2_memories.items():
        await store.aput(
            user2_namespace,
            key,
            value,
            index=["text"],
        )

    # Inspect what is actually stored for each user.
    print("USER 1: all stored memories")
    for item in await store.asearch(user1_namespace):
        print(item.key, "->", item.value)

    print("\nUSER 2: all stored memories")
    for item in await store.asearch(user2_namespace):
        print(item.key, "->", item.value)

    # Query 1: semantically relevant, different wording.
    relevant_query = (
        "What outdoor leisure activity does this person enjoy?"
    )

    relevant_results = await store.asearch(
        user1_namespace,
        query=relevant_query,
        limit=3,
    )

    print("\nRELEVANT QUERY:", relevant_query)
    for item in relevant_results:
        score = getattr(item, "score", None)
        print(
            f"key={item.key}, score={score}, "
            f"text={item.value['text']}"
        )

    # Query 2: unrelated to all stored memories.
    unrelated_query = (
        "What is the orbital composition of a distant exoplanet?"
    )

    unrelated_results = await store.asearch(
        user1_namespace,
        query=unrelated_query,
        limit=3,
    )

    print("\nUNRELATED QUERY:", unrelated_query)
    for item in unrelated_results:
        score = getattr(item, "score", None)
        print(
            f"key={item.key}, score={score}, "
            f"text={item.value['text']}"
        )

    # A nearest-neighbor search can return results even when none is
    # genuinely relevant. Use the threshold only as an initial filter.
    print("\nUNRELATED QUERY: threshold demonstration")
    accepted = []

    for item in unrelated_results:
        score = getattr(item, "score", None)

        if score is not None and score >= MIN_SCORE:
            accepted.append(item)

    if accepted:
        print(
            f"{len(accepted)} result(s) passed the illustrative "
            f"threshold of {MIN_SCORE}."
        )
    else:
        print(
            "No results passed the threshold, or scores were unavailable."
        )

    # User isolation check: search only under user 1's namespace.
    user1_results = await store.asearch(
        user1_namespace,
        query="music and musical instruments",
        limit=10,
    )

    print("\nUSER ISOLATION CHECK")
    print("Results returned under user 1's namespace:")

    for item in user1_results:
        print(item.key, "->", item.value)

    # Verify that user 2's known records are not in user 1's results.
    user2_texts = {
        value["text"] for value in user2_memories.values()
    }

    assert all(
        item.value["text"] not in user2_texts
        for item in user1_results
    )

    print("PASS: user 1's search returned no user 2 records.")


if __name__ == "__main__":
    asyncio.run(main())
