

import asyncio
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.runtime import Runtime


llm = ChatOpenAI(model="gpt-5-nano")

checkpointer = InMemorySaver()
store = InMemoryStore()


@dataclass
class Context:
    user_id: str


async def assistant_node(
    state: MessagesState,
    runtime: Runtime[Context],
):
    user_id = runtime.context.user_id
    namespace = ("users", user_id, "facts")

    latest_message = state["messages"][-1]
    user_text = latest_message.content

    # Save a fact when the user explicitly asks us to remember it.
    if "remember that I prefer python" in user_text.lower():
        await runtime.store.aput(
            namespace,
            "favorite-language",
            {"text": "The user prefers Python for backend development."},
        )

    # Retrieve the user's saved fact.
    item = await runtime.store.aget(
        namespace,
        "favorite-language",
    )

    if item is None:
        fact = "No saved fact is available."
    else:
        fact = item.value["text"]

    response = await llm.ainvoke([
        SystemMessage(content=(
            "Answer using the conversation history and the saved fact below. "
            "Do not claim that you remember information that is not available. "
            f"Saved long-term fact: {fact}"
        )),
        *state["messages"],
    ])

    return {"messages": [response]}


builder = StateGraph(
    MessagesState,
    context_schema=Context,
)

builder.add_node("assistant", assistant_node)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

# The SAME graph has both persistence mechanisms.
graph = builder.compile(
    checkpointer=checkpointer,
    store=store,
)


async def main():
    config_a = {"configurable": {"thread_id": "thread-A"}}
    config_b = {"configurable": {"thread_id": "thread-B"}}

    context = Context(user_id="user-1")

    # Run 1: Thread A saves the fact.
    result_a = await graph.ainvoke(
        {"messages": [
            HumanMessage(
                content="Remember that I prefer Python for backend development."
            )
        ]},
        config=config_a,
        context=context,
    )

    print("\nA's reply:")
    print(result_a["messages"][-1].content)

    # Inspect A's checkpointed conversation.
    state_a = await graph.aget_state(config_a)
    print("\nA's saved conversation:")
    for message in state_a.values["messages"]:
        print(type(message).__name__, ":", message.content)

    # Run 2: A asks a follow-up in the SAME thread.
    result_a2 = await graph.ainvoke(
        {"messages": [
            HumanMessage(content="What language do I prefer?")
        ]},
        config=config_a,
        context=context,
    )
    print("\nA's follow-up:")
    print(result_a2["messages"][-1].content)

    # Run 3: B asks the same question in a NEW thread.
    result_b = await graph.ainvoke(
        {"messages": [
            HumanMessage(content="What language do I prefer?")
        ]},
        config=config_b,
        context=context,
    )
    print("\nB's reply:")
    print(result_b["messages"][-1].content)

    # Inspect B's state to verify thread isolation.
    state_b = await graph.aget_state(config_b)
    print("\nB's saved conversation:")
    for message in state_b.values["messages"]:
        print(type(message).__name__, ":", message.content)

    a_history = state_a.values["messages"]
    b_history = state_b.values["messages"]

    assert any(
        "remember that I prefer python" in str(message.content).lower()
        for message in a_history
    )
    assert not any(
        "remember that I prefer python" in str(message.content).lower()
        for message in b_history
    )

    # Verify B can access the fact through the shared store.
    item = await store.aget(
        ("users", "user-1", "facts"),
        "favorite-language",
    )
    assert item is not None
    assert "Python" in item.value["text"]

    print("\nPASS: A's history is isolated from B.")
    print("PASS: B can access the fact shared through the store.")

    print("\nStored facts:")
    for item in await store.asearch(
        ("users", "user-1", "facts")
    ):
        print(item.key, "->", item.value)


if __name__ == "__main__":
    asyncio.run(main())
