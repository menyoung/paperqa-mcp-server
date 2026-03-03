# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "paper-qa",
#     "mcp[cli]>=1.2.0",
# ]
# ///
"""MCP server exposing PaperQA2 for deep synthesis across scientific papers."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from paperqa import Settings, agent_query

mcp = FastMCP("paperqa")


def _settings() -> Settings:
    return Settings(
        llm=os.environ.get("PQA_LLM", "gpt-4o-mini"),
        summary_llm=os.environ.get("PQA_SUMMARY_LLM", "gpt-4o-mini"),
        embedding=os.environ.get("PQA_EMBEDDING", "text-embedding-3-small"),
        temperature=0.1,
        answer={"evidence_k": 15, "answer_max_sources": 10},
        agent={
            "index": {
                "paper_directory": os.environ.get(
                    "PAPER_DIRECTORY",
                    os.path.expanduser("~/Zotero/storage"),
                )
            }
        },
    )


@mcp.tool()
async def paper_qa(query: str) -> str:
    """Search and synthesize across all papers in the library.

    Use this for questions that require deep reading and synthesis
    across multiple scientific papers. Returns a detailed answer with
    inline citations. Citation source paths contain 8-character Zotero
    storage keys (e.g. ABC123DE) that can be used to look up items
    in Zotero.

    Not for quick metadata lookups or library browsing — use Zotero
    tools for that.
    """
    response = await agent_query(query=query, settings=_settings())
    return response.session.formatted_answer


if __name__ == "__main__":
    mcp.run(transport="stdio")
