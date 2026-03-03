# paperqa-mcp-server

MCP server that exposes [PaperQA2](https://github.com/Future-House/paper-qa)
as a tool for Claude. Point it at your Zotero storage (or any folder of PDFs)
and Claude can do deep synthesis across your entire library.

## Prerequisites

1. **uv** — install it if you don't have it:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **OpenAI API key** — needed for embeddings. Get one at
   https://platform.openai.com/api-keys

3. **Papers** — a folder of PDFs. If you use Zotero, your PDFs are at
   `~/Zotero/storage` by default.

## Test it from the terminal

Before connecting to Claude, verify it works:

```bash
OPENAI_API_KEY=sk-your-key-here uv run server.py
```

You should see the server start with no errors. Press Ctrl+C to stop it.

If your PDFs are somewhere other than `~/Zotero/storage`:

```bash
OPENAI_API_KEY=sk-your-key-here PAPER_DIRECTORY=/path/to/your/pdfs uv run server.py
```

## Connect to Claude Desktop

1. Open Claude Desktop
2. Go to Settings → Developer → Edit Config
3. This opens `claude_desktop_config.json`. Add the `paperqa` entry:

```json
{
  "mcpServers": {
    "paperqa": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/paperqa-mcp-server/server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "PAPER_DIRECTORY": "/Users/yourname/Zotero/storage"
      }
    }
  }
}
```

**Important:**
- Replace `/absolute/path/to/` with the actual path where you cloned this repo
- Replace `sk-your-key-here` with your real OpenAI API key
- Replace `/Users/yourname/` with your actual home directory
- `PAPER_DIRECTORY` can be omitted if your PDFs are at `~/Zotero/storage`

4. Quit Claude Desktop completely and reopen it
5. You should see a hammer icon with `paper_qa` listed as a tool

## First run is slow

The first time you ask a question, PaperQA2 indexes every PDF in your
paper directory — chunking, embedding, and fetching metadata. With
hundreds of papers this takes minutes and costs a few dollars in
OpenAI embedding API calls.

After that, the index is cached. Only new or changed files get
re-processed on subsequent runs.

To pre-build the index without waiting for your first query:

```bash
OPENAI_API_KEY=sk-your-key-here uv run --with paper-qa pqa index --paper_directory ~/Zotero/storage
```

## Use a different LLM

By default, PaperQA2 uses `gpt-4o-mini` for its internal reasoning.
This is separate from Claude — Claude calls the tool, PaperQA2 does
its own LLM calls internally to gather and synthesize evidence.

To use a different model, add env vars to your Claude Desktop config:

```json
{
  "env": {
    "OPENAI_API_KEY": "sk-your-key-here",
    "PQA_LLM": "gpt-4o",
    "PQA_SUMMARY_LLM": "gpt-4o-mini"
  }
}
```

To use Claude as PaperQA2's internal LLM (you'll pay for both
Claude Desktop and Claude API calls):

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-your-key-here",
    "PQA_LLM": "claude-sonnet-4-20250514",
    "PQA_SUMMARY_LLM": "claude-haiku-4-5-20251001"
  }
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
