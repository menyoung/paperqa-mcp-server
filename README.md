# paperqa-mcp-server

Give Claude the ability to read, search, and synthesize across your
entire PDF library. Built on [PaperQA2](https://github.com/Future-House/paper-qa).

Point it at your Zotero storage folder (or any folder of PDFs) and ask
Claude questions that require deep reading across multiple papers.

<a href="https://glama.ai/mcp/servers/@menyoung/paperqa-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@menyoung/paperqa-mcp-server/badge" alt="paperqa-mcp-server MCP server" />
</a>

## Quick start

### 1. Install uv

[uv](https://docs.astral.sh/uv/) is a Python package manager. If you don't
have it yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing, **restart your terminal** so `uv` is on your PATH.

Verify it works:

```bash
uv --version
```

### 2. Get an OpenAI API key

PaperQA2 uses OpenAI for embeddings and internal reasoning. Get a key at
https://platform.openai.com/api-keys

### 3. Warm the package cache

The first run downloads ~90 Python packages — this is normal and only
happens once. Run this so the packages are cached before Claude Desktop
tries to start the server:

```bash
uvx paperqa-mcp-server index 2>&1 | head -1
```

You should see output like `Building index: ...`. Press Ctrl+C to stop
(we'll run the real index build in step 6). If you see a Python error
instead, something went wrong with the install.

### 4. Find your full path to uvx

Claude Desktop can't find `uvx` on its own — you need to give it the
full path. Run:

```bash
which uvx
```

This prints something like `/Users/yourname/.local/bin/uvx`. Copy it —
you'll need it in the next step.

### 5. Add to Claude Desktop

1. Open Claude Desktop
2. Go to **Settings → Developer → Edit Config**
3. This opens `claude_desktop_config.json`. Add a `paperqa` entry inside
   `mcpServers` (create `mcpServers` if it doesn't exist):

```json
{
  "mcpServers": {
    "paperqa": {
      "command": "/Users/yourname/.local/bin/uvx",
      "args": ["paperqa-mcp-server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

Replace the two placeholders:
- `/Users/yourname/.local/bin/uvx` — paste the output of `which uvx` from step 4
- `sk-your-key-here` — your OpenAI API key from step 2

If your PDFs are somewhere other than `~/Zotero/storage`, add a
`PAPER_DIRECTORY` entry to `env`:

```json
"env": {
  "OPENAI_API_KEY": "sk-your-key-here",
  "PAPER_DIRECTORY": "/full/path/to/your/pdfs"
}
```

4. **Quit Claude Desktop completely** (Cmd+Q, not just close the window)
   and reopen it
5. You should see a hammer icon — click it and `paper_qa` should be listed

### 6. Pre-build the index

Before Claude can search your papers, the server needs to build a search
index. This reads each PDF, splits it into chunks, and sends the chunks
to OpenAI's embedding API. With hundreds of papers this takes a while
and costs a few dollars in API calls.

If you have more than 10 unindexed papers, the server will refuse to
answer queries and tell you to run this step first. A few new papers
will be indexed automatically when you query.

```bash
export OPENAI_API_KEY=sk-your-key-here
uvx paperqa-mcp-server index
```

You'll see log lines as each paper is processed. When it finishes, it
prints `Done.`

**If this crashes** with a rate limit error, just re-run the same command.
It picks up where it left off — each run indexes more files. With a large
library (500+ papers) you may need to run it a few times.

After that, the index is cached at `~/.pqa/indexes/`. Only new or changed
files get re-processed on subsequent runs.

## Troubleshooting

**"Server disconnected" in Claude Desktop**

Claude Desktop has a short startup timeout. If `uv` needs to download
packages on first launch, it will time out. Fix: run `uvx paperqa-mcp-server`
once from the terminal first so packages are cached.

**"Index incomplete" when querying**

The server checks the index before each query. If too many papers are
unindexed, it returns a diagnostic message instead of trying (and
failing) to index them all on the fly. Fix: run the index command in
step 6.

**Hammer icon doesn't appear**

Make sure you quit Claude Desktop completely (Cmd+Q) and reopened it.
Check for JSON syntax errors in `claude_desktop_config.json` — a
missing comma is the most common mistake.

## Use a different LLM

By default, PaperQA2 uses `gpt-4o-mini` for its internal reasoning.
This is separate from Claude — Claude calls the tool, PaperQA2 does
its own LLM calls internally to gather and synthesize evidence.

To use a different model, add env vars to your Claude Desktop config:

```json
"env": {
  "OPENAI_API_KEY": "sk-your-key-here",
  "PQA_LLM": "gpt-4o",
  "PQA_SUMMARY_LLM": "gpt-4o-mini"
}
```

## All environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PAPER_DIRECTORY` | `~/Zotero/storage` | Folder containing your PDFs |
| `OPENAI_API_KEY` | — | **Required** for default embeddings |
| `PQA_LLM` | `gpt-4o-mini` | LLM for internal reasoning |
| `PQA_SUMMARY_LLM` | `gpt-4o-mini` | LLM for summarizing chunks |
| `PQA_EMBEDDING` | `text-embedding-3-small` | Embedding model |
| `ANTHROPIC_API_KEY` | — | Only if using Claude as internal LLM |

## Works with zotero-mcp

This pairs well with [zotero-mcp](https://github.com/54yyyu/zotero-mcp):

- **paperqa-mcp-server** — deep reading and synthesis across full paper text
- **zotero-mcp** — browse your library, search metadata, read annotations

Claude can cross-reference between them — for example, finding papers
with PaperQA and then pulling up their Zotero metadata and annotations.
PaperQA2's citations include Zotero storage keys (e.g. `ABC123DE` from
`storage/ABC123DE/paper.pdf`) that Claude can use to look up items via
zotero-mcp.

## Index implementation notes

`paperqa-mcp-server index` uses the same `_settings()` function as the MCP
server, so the index it builds is exactly the one the server will look
for. The PaperQA2 index directory name is a hash of the settings
(embedding model, chunk size, paper directory path, etc.). The settings
include:

- **Multimodal OFF** — skip image extraction from PDFs (avoids a crash on
  PDFs with CMYK images)
- **Doc details OFF** — skip Crossref/Semantic Scholar metadata lookups
  (avoids rate limits; Claude can get metadata from Zotero directly via
  zotero-mcp)
- **Concurrency 1** — index one file at a time to stay under OpenAI's
  embedding rate limit

> **Why not `pqa index`?** The `pqa` CLI constructs settings via pydantic's
> `CliSettingsSource`, which produces different defaults than constructing
> `Settings()` directly in Python (e.g. `chunk_chars` of 7000 vs 5000).
> Different settings = different index hash = server can't find the index.
> Always use `paperqa-mcp-server index` to build the index.

## Install from GitHub (latest)

To use the latest version from the main branch instead of PyPI:

```json
{
  "mcpServers": {
    "paperqa": {
      "command": "/Users/yourname/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/menyoung/paperqa-mcp-server", "paperqa-mcp-server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

To build the index from the latest main branch:

```bash
OPENAI_API_KEY=sk-your-key-here uvx --from git+https://github.com/menyoung/paperqa-mcp-server paperqa-mcp-server index
```

## Development

If you want to contribute or modify the server locally:

```bash
git clone https://github.com/menyoung/paperqa-mcp-server.git
cd paperqa-mcp-server
uv sync
uv run paperqa-mcp-server        # run the server
uv run paperqa-mcp-server index  # build the index
```