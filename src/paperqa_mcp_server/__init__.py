"""MCP server exposing PaperQA2 for deep synthesis across scientific papers."""

from __future__ import annotations

import os
import pathlib
import pickle
import zlib

from mcp.server.fastmcp import FastMCP
from paperqa import Settings, agent_query

mcp = FastMCP("paperqa")


def _settings() -> Settings:
    return Settings(
        llm=os.environ.get("PQA_LLM", "gpt-4o-mini"),
        summary_llm=os.environ.get("PQA_SUMMARY_LLM", "gpt-4o-mini"),
        embedding=os.environ.get("PQA_EMBEDDING", "text-embedding-3-small"),
        temperature=0.1,
        parsing={"multimodal": "OFF", "use_doc_details": False},
        answer={"evidence_k": 15, "answer_max_sources": 10},
        agent={
            "index": {
                "paper_directory": os.environ.get(
                    "PAPER_DIRECTORY",
                    os.path.expanduser("~/Zotero/storage"),
                ),
                "concurrency": 1,
            }
        },
    )


_UNINDEXED_THRESHOLD = 10


def _index_status(settings: Settings | None = None) -> dict:
    """Read the index manifest and compare against files in the paper directory.

    Returns a dict with keys: indexed, errored, unindexed, total, ready, message.
    """
    if settings is None:
        settings = _settings()
    index_name = settings.get_index_name()
    index_dir = pathlib.Path(settings.agent.index.index_directory) / index_name
    paper_dir = pathlib.Path(settings.agent.index.paper_directory)
    files_filter = settings.agent.index.files_filter

    # Discover files PaperQA would try to index (same filter as paperqa)
    total = 0
    if paper_dir.is_dir():
        total = sum(1 for f in paper_dir.rglob("*") if files_filter(f))

    # Read the manifest
    manifest_path = index_dir / "files.zip"
    manifest: dict[str, str] = {}
    manifest_error = False
    if manifest_path.exists():
        try:
            manifest = pickle.loads(zlib.decompress(manifest_path.read_bytes()))
        except Exception:
            manifest_error = True

    errored = sum(1 for v in manifest.values() if v == "ERROR")
    indexed = len(manifest) - errored
    unindexed = max(0, total - len(manifest))

    ready = unindexed <= _UNINDEXED_THRESHOLD and not manifest_error
    if manifest_error:
        message = (
            f"Index manifest is corrupt ({total} files on disk)."
            " Rebuild the index from the terminal"
            " — see the paperqa-mcp-server README, step 5."
        )
    else:
        message = f"{indexed}/{total} papers indexed"
        if errored:
            message += f", {errored} errors"
        if unindexed:
            message += f", {unindexed} unindexed"
        if ready:
            message += ". Ready to query."
        else:
            message += (
                ". Queries will fail or time out."
                " Please finish building the index from the terminal"
                " — see the paperqa-mcp-server README, step 5."
            )

    return {
        "indexed": indexed,
        "errored": errored,
        "unindexed": unindexed,
        "total": total,
        "ready": ready,
        "message": message,
    }


@mcp.tool()
async def index_status() -> str:
    """Check the health of the paper index.

    Returns a summary of how many papers are indexed, how many have
    errors, and how many are unindexed. Use this to diagnose why
    paper_qa queries might be failing or timing out.
    """
    status = _index_status()
    lines = [
        f"Index status: {status['message']}",
        f"  Indexed: {status['indexed']}",
        f"  Errors:  {status['errored']}",
        f"  Unindexed: {status['unindexed']}",
        f"  Total files: {status['total']}",
    ]
    return "\n".join(lines)


@mcp.tool()
async def paper_qa(query: str) -> str:
    """Search and synthesize across all papers in the library.

    Use this for questions that require deep reading and synthesis
    across multiple scientific papers — e.g. "What methods have been
    used to recycle lithium from spent batteries?" or "Compare the
    thermal stability of PEEK vs PTFE in the literature."

    Returns a detailed answer with inline citations. Each citation
    includes a file path containing an 8-character Zotero storage key
    (e.g. ABC123DE from storage/ABC123DE/paper.pdf). You can use these
    keys with zotero-mcp tools to look up the full bibliographic record,
    read annotations, or find related items.

    Not for quick metadata lookups or library browsing — use Zotero
    tools for that.

    If this tool returns "Index incomplete", the paper index has not
    been fully built yet. Tell the user to run the index build command
    from the terminal (see the paperqa-mcp-server README, step 5).
    Do not retry the query — it will give the same result until the
    index is built.

    This tool can take 30–90 seconds to respond when working normally.
    """
    settings = _settings()
    status = _index_status(settings)
    if not status["ready"]:
        return f"Index incomplete: {status['message']}"

    try:
        response = await agent_query(query=query, settings=settings)
    except Exception as e:
        return f"PaperQA error: {e}"
    if not response.session.formatted_answer:
        return f"PaperQA could not answer (status: {response.status})."
    return response.session.formatted_answer


def _build_index() -> None:
    """Build the search index using the same settings as the MCP server."""
    import asyncio

    from paperqa.agents.search import get_directory_index

    settings = _settings()
    print(f"Building index: {settings.get_index_name()}")
    print(f"Paper directory: {settings.agent.index.paper_directory}")
    asyncio.run(get_directory_index(settings=settings))
    print("Done.")


def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "index":
        _build_index()
    else:
        mcp.run(transport="stdio")
