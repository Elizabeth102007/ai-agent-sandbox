import asyncio
from dataclasses import dataclass
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

load_dotenv()

@dataclass
class UserDeps:
    name: str


class FinalAnswer(BaseModel):
    message: str
    mood: str


side_effects = []


agent = Agent(
    "openai:gpt-5-nano",
    deps_type=UserDeps,
    output_type=FinalAnswer,
)


@agent.tool
async def record_greeting(ctx: RunContext[UserDeps]) -> str:
    """Record a greeting for the current user."""

    name = ctx.deps.name

    side_effects.append(f"GREETING RECORDED FOR {name}")

    print(f"SIDE EFFECT: greeting recorded for {name}")

    return f"Done. The greeting for {name} has been recorded. Do not call this tool again."

async def main():

    deps = UserDeps(name="Jenny")

    result = await agent.run(
        """
        Call record_greeting exactly once.
        After the tool returns, provide the final structured answer.
        """,
        deps=deps,
    )

    print("\nFINAL RESULT:")
    print(result.output)

    print("\nALL MESSAGES:")
    for message in result.all_messages():
        print(message)


    print("\nSIDE EFFECTS:")
    print(side_effects)

    
if __name__ == "__main__":
    asyncio.run(main())