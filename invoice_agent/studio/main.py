

import argparse
import asyncio
import json
from pathlib import Path

from graph import build_graph


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract and validate an invoice."
    )
    parser.add_argument(
        "sample",
        help="Path to the invoice text file.",
    )
    args = parser.parse_args()

    sample_path = Path(args.sample)

    try:
        raw_text = sample_path.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(
            f"Could not read invoice sample '{sample_path}': {exc}"
        )

    graph = build_graph()

    initial_state = {
        "raw_text": raw_text,
        "invoice": None,
        "errors": [],
        "attempts": 0,
        "path": [],
        "result": None,
    }

    final_state = await graph.ainvoke(initial_state)
    result = final_state["result"]

    print("Final result:")
    print(json.dumps(result.model_dump(mode="json"), indent=2))

    print("\nExecution path:")
    print(" -> ".join(final_state["path"]))


if __name__ == "__main__":
    asyncio.run(main())
