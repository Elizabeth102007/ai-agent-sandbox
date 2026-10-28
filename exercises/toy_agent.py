from __future__ import annotations

import os
from typing import Literal

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv

load_dotenv()


# configuration

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5-nano")


SUMMARY_TRIGGER_TOKENS = 50



# TOOLS


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a basic arithmetic expression.

    Example:
        calculator("12 * 5 + 3")
    """
    try:
        # Toy example use only.
        # eval() can be used like this in production with untrusted input.
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Could not calculate expression: {e}"


@tool
def get_weather(city: str) -> str:
    """
    Return a fake weather result for a city.
    """
    fake_weather = {
        "cairo": "32°C, sunny",
        "london": "16°C, cloudy",
        "new york": "21°C, partly cloudy",
    }

    return fake_weather.get(
        city.lower(),
        f"No weather data available for {city}.",
    )


tools = [
    calculator,
    get_weather,
]



# models

llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
)

# The agent model gets access to the two tools.
llm_with_tools = llm.bind_tools(tools)


# Separate model call used only for summarization.
summarizer_llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
)



# state schema

class State(MessagesState):
    """
    A single application state schema.

    MessagesState already provides:

        messages: Annotated[list[AnyMessage], add_messages]

    """

    summary: str | None


# agent node
def call_agent(state: State):
    """
    Calls the LLM.

    Because llm_with_tools has the tools bound to it, the AI can
    either answer normally or produce tool_calls.

    ToolNode handles those tool_calls afterward.
    """

    response = llm_with_tools.invoke(state["messages"])

    return {
        "messages": [response]
    }



# decide whether to summarize or call the agent next

def should_summarize(state: State) -> Literal["summarize", "agent"]:

    messages = state["messages"]

    token_count = llm.get_num_tokens_from_messages(messages)

    print(f"Current conversation tokens: {token_count}")

    if token_count >= SUMMARY_TRIGGER_TOKENS:
        return "summarize"

    return "agent"

# summarization node

def summarize_messages(state: State):
    """
    Compress the old conversation into a single summary.

    keeps the most recent conversational exchange and replace
    the older history with a SystemMessage containing the summary.

    Which prevents the message list from growing forever.
    """

    messages = state["messages"]

    conversation_messages = [
        message
        for message in messages
        if isinstance(message, (HumanMessage, AIMessage))
    ]

    if not conversation_messages:
        return {}

    previous_summary = state.get("summary")

    conversation_text = "\n".join(
        f"{message.__class__.__name__}: {message.content}"
        for message in conversation_messages
    )

    previous_summary_text = (
        previous_summary
        if previous_summary
        else "There is no previous summary."
    )

    prompt = f"""
             You are a conversation summarizer.

            Create a concise but information-dense summary of the conversation.

            Preserve:
            - important facts
            - user preferences
            - decisions
            - ongoing tasks
            - important technical details
            - unresolved questions
            - relevant context needed to continue the conversation

            Do not invent information.

            Previous summary:
            {previous_summary_text}

            Current conversation:
            {conversation_text}

            Return ONLY the updated summary.
            """

    response = summarizer_llm.invoke(
        [
            SystemMessage(content=prompt)
        ]
    )

    new_summary = response.content

    # Find a safe cut point in the FULL message list — always start
    # right at a human turn, never mid tool-call sequence.
    human_indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    cut_index = human_indices[-2] if len(human_indices) >= 2 else 0
    recent_messages = messages[cut_index:]


    summary_message = SystemMessage(
        content=(
            "Conversation summary. Use this as background context "
            "for the conversation:\n\n"
            f"{new_summary}"
        )
    )

    # REMOVE_ALL_MESSAGES tells the add_messages reducer to replace
    # the existing message history rather than append to it.
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            summary_message,
            *recent_messages,
        ],
        "summary": new_summary,
    }



# tool node

tool_node = ToolNode(tools)

# build graph

builder = StateGraph(State)

# Nodes
builder.add_node("summarize", summarize_messages)
builder.add_node("agent", call_agent)
builder.add_node("tools", tool_node)

# Start -> decide whether summarization is necessary.
builder.add_conditional_edges(
    START,
    should_summarize,
    {
        "summarize": "summarize",
        "agent": "agent",
    },
)

# After summarization -> agent.
builder.add_edge("summarize", "agent")

# Agent -> either tools OR END.

builder.add_conditional_edges(
    "agent",
    tools_condition,
)

builder.add_edge("tools", "agent")


# checkpointer/short-term memory

#memory = InMemorySaver()

graph = builder.compile()#checkpointer=memory)


# run the graph 
if __name__ == "__main__":

    # thread_id identifies the conversation.
    
    # Calling graph.invoke() repeatedly with the same thread_id
    # gives the agent access to its previous checkpointed state.
    
    #config = {"configurable": {"thread_id": "toy-conversation-1"}}

    questions = [
        "My name is Alex.",
        "What is 12 * 8?",
        "What's the weather in Cairo?",
        "What did I tell you my name was?"
    ]

    for question in questions:

        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(content=question)
                ]
            },
            #config=config,
        )

        print("\n" + "=" * 70)
        print("USER:")
        print(question)

        print("\nASSISTANT:")
        print(result["messages"][-1].content)

        print("\nMESSAGES CURRENTLY IN STATE:")
        for message in result["messages"]:
            print(
                f"- {message.__class__.__name__}: {message.content}"
            )

        print(
            "\nSUMMARY EXISTS:",
            bool(result.get("summary"))
        )
    print(
        "SUMMARY CONTENT:",
        result.get("summary")
        )