
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver

from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano")
checkpointer = InMemorySaver()


async def chat_node(state: MessagesState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(MessagesState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

graph = builder.compile(checkpointer=checkpointer)


async def main():
    thread_a = {"configurable": {"thread_id": "A"}}
    thread_b = {"configurable": {"thread_id": "B"}}

    # First run in thread A
    result = await graph.ainvoke(
        {"messages": [
            SystemMessage(content=(
                "Answer questions about previous messages accurately. "
                "If the answer is not in the conversation, say you don't know."
            )),
            HumanMessage(content="My secret code word is ORCHID-731.")
        ]},
        config=thread_a,
    )
    print("A1:", result["messages"][-1].content)

    # Second run in thread A
    result = await graph.ainvoke(
        {"messages": [
            HumanMessage(content="What is my secret code word?")
        ]},
        config=thread_a,
    )
    print("A2:", result["messages"][-1].content)

    # First run in thread B
    result = await graph.ainvoke(
        {"messages": [
            SystemMessage(content=(
                "Answer questions about previous messages accurately. "
                "If the answer is not in the conversation, say you don't know."
            )),
            HumanMessage(content="What is my secret code word?")
        ]},
        config=thread_b,
    )
    print("B1:", result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
