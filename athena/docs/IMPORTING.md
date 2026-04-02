# Import Existing Data

Athena's memory is just Markdown files. Any text you can export becomes part of your memory.

## Supported Sources

| Source | How to Import |
|:-------|:-------------|
| **ChatGPT** | Settings → Data Controls → Export → Copy `.md` files into `.context/memories/imports/` |
| **Gemini** | [Google Takeout](https://takeout.google.com/) → Select "Gemini Apps" → Extract into `.context/memories/imports/` |
| **Claude** | Settings → Export Data → Copy transcripts into `.context/memories/imports/` |
| **Any Markdown** | Drop `.md` files into `.context/memories/` — indexed on next `/start` |

After importing, run `athena check` to verify files are detected.

## How It Works

When you run `/start`, Athena scans the `.context/` directory for new or changed Markdown files. Any files placed in `.context/memories/imports/` will be automatically indexed and available for semantic search.

The import process is non-destructive — your original files are preserved as-is. Athena creates embeddings for search but never modifies the source files.

> [!TIP]
> For best results, clean up exported data before importing. Remove system messages, timestamps, and formatting artifacts that don't add meaningful context.
