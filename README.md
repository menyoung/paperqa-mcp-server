# paperqa-mcp-server

MCP server that exposes [PaperQA2](https://github.com/Future-House/paper-qa)
as a tool for Claude. Point it at your Zotero storage (or any folder of PDFs)
and Claude can do deep synthesis across your entire library.

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

### 3. Clone this repo

```bash
git clone https://github.com/menyoung/paperqa-mcp-server.git
cd paperqa-mcp-server
```

### 4. Test that it runs

This downloads ~90 Python packages the first time — that's normal:

```bash
uv run server.py &
```

Wait a few seconds. If you see `Installed XX packages` and no errors, it
worked. Kill the background process:

```bash
kill %1 2>/dev/null
```

### 5. Find your full paths

You'll need two absolute paths for the config. Run these and copy the output:

```bash
which uv           # e.g. /Users/yourname/.local/bin/uv
pwd                 # e.g. /Users/yourname/paperqa-mcp-server
```

### 6. Add to Claude Desktop

1. Open Claude Desktop
2. Go to **Settings → Developer → Edit Config**
3. This opens `claude_desktop_config.json`. Add a `paperqa` entry inside
   `mcpServers` (create `mcpServers` if it doesn't exist):

```json
{
  "mcpServers": {
    "paperqa": {
      "command": "/FULL/PATH/TO/uv",
      "args": ["run", "/FULL/PATH/TO/paperqa-mcp-server/server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

Replace the three ALL-CAPS placeholders:
- `/FULL/PATH/TO/uv` — paste the output of `which uv` from step 5
- `/FULL/PATH/TO/paperqa-mcp-server/server.py` — paste the output of `pwd`
  from step 5, then add `/server.py` at the end
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

### 7. Pre-build the index

You **must** pre-build the index before using `paper_qa`. Without it,
your first query will try to index every PDF on the fly, which takes
too long and will time out.

PaperQA2 chunks each PDF and embeds the text via the OpenAI embeddings
API. With hundreds of papers this takes a while and costs a few dollars
in API calls.

```bash
cd /path/to/paperqa-mcp-server
OPENAI_API_KEY=sk-your-key-here uv run --with paper-qa --with pillow \
  pqa --parsing.multimodal OFF --parsing.use_doc_details false \
  --agent.index.concurrency 1 index ~/Zotero/storage
```

Replace `~/Zotero/storage` with your PDF folder if different.

What the flags do:
- `--parsing.multimodal OFF` — skip image extraction from PDFs (avoids
  a crash on PDFs with CMYK images)
- `--parsing.use_doc_details false` — skip Crossref/Semantic Scholar
  metadata lookups (avoids rate limits; Claude can get metadata from
  Zotero directly via zotero-mcp)
- `--agent.index.concurrency 1` — index one file at a time to stay
  under OpenAI's embedding rate limit

**If this crashes** with a rate limit error, just re-run the same command.
It picks up where it left off — each run indexes more files. With a large
library (500+ papers) you may need to run it a few times.

After that, the index is cached at `~/.pqa/indexes/`. Only new or changed
files get re-processed on subsequent runs.

## Troubleshooting

**"Server disconnected" in Claude Desktop**

Claude Desktop has a short startup timeout. If `uv` needs to download
packages on first launch, it will time out. Fix: run `uv run server.py`
once from the terminal first (step 4 above) so packages are cached.

**"No such file or directory"**

You must use the **full absolute path** to `uv` in the config (e.g.
`/Users/yourname/.local/bin/uv`, not just `uv`). Claude Desktop runs
with a minimal system PATH.

**"unhandled errors in a TaskGroup" when querying**

This means the index isn't fully built yet. PaperQA2 tries to index
remaining files during your query, hits the OpenAI rate limit, and
crashes. Fix: finish building the index from the terminal first (step 7).

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

This pairs well with [zotero-mcp](https://github.com/kucinghyper/zotero-mcp):

- **paperqa-mcp-server** → deep reading and synthesis across full paper text
- **zotero-mcp** → browse library, search metadata, read annotations, manage collections

File paths in PaperQA2's citations contain Zotero's 8-character storage keys
(e.g. `ABC123DE` from `storage/ABC123DE/paper.pdf`). Claude can use these
keys with zotero-mcp to look up the full item in your library.
