

import asyncio
from typing import Optional

from pydantic import BaseModel, ConfigDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.memory import InMemoryStore


class ProfilePatch(BaseModel):
    """Fields that may be updated in a user profile."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    occupation: Optional[str] = None
    preferred_language: Optional[str] = None
    city: Optional[str] = None


llm = ChatOpenAI(model="gpt-5-nano")

structured_llm = llm.with_structured_output(ProfilePatch)

store = InMemoryStore()

namespace = ("users", "user-1")
profile_key = "profile"


async def extract_patch(message: str) -> ProfilePatch:
    result = await structured_llm.ainvoke([
        SystemMessage(content="""
Extract only profile changes explicitly stated in the latest user message.

Allowed fields:
- name
- occupation
- preferred_language
- city

Do not invent facts.
Return null for fields not provided in the message.
"""),
        HumanMessage(content=message),
    ])

    return result


async def update_profile(message: str):
    # Read the existing profile.
    item = await store.aget(namespace, profile_key)
    current = item.value if item is not None else {}

    # Ask the model for a schema-validated patch.
    patch_model = await extract_patch(message)

    # Keep only explicitly set, non-null fields.
    patch = patch_model.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    # merge the patch into the current document.
    updated = {**current, **patch}

    # save back to the SAME namespace and key.
    await store.aput(namespace, profile_key, updated)

    saved = await store.aget(namespace, profile_key)

    print("\nMessage:", message)
    print("Validated model output:", patch_model)
    print("Patch applied:", patch)
    print("Profile after update:", saved.value)


async def main():
    await update_profile(
        "My name is Ada and I work as a backend developer."
    )

    await update_profile(
        "I prefer Python and live in Cairo."
    )

    await update_profile(
        "I moved to Lagos."
    )

    print("\nAll records in the user namespace:")
    for item in await store.asearch(namespace):
        print(item.key, "->", item.value)


if __name__ == "__main__":
    asyncio.run(main())
