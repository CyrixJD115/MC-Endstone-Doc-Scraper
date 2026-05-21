# MCEndstoneDocScraper

A Python web scraper that downloads [Endstone.dev](https://endstone.dev/latest/) documentation into local markdown files — primarily designed to feed coding agents the context they need to write Endstone plugins effectively.

## Why This Exists

When using AI coding agents (like Copilot, Cursor, opencode, etc.) to develop Endstone plugins, they often lack up-to-date knowledge of the Endstone API. This scraper solves that by pulling the latest docs into clean markdown that can be:

- Dropped into a project's context for an agent to reference
- Embedded via `.opencode/` or similar agent config
- Used as a knowledge base for RAG pipelines
- Browsed offline for quick reference

Of course, it works just as well for anyone who wants offline Endstone docs.

## About Endstone

Endstone is a plugin framework for **Minecraft Bedrock Dedicated Servers**. It provides a powerful Python (and C++) API for writing server-side plugins, built on top of the Bedrock Dedicated Server.

## Installation

Requires [uv](https://docs.astral.sh/uv/) (recommended) or pip.

```bash
git clone https://github.com/yourusername/MCEndstoneDocScraper.git
cd MCEndstoneDocScraper
uv sync
```

Or with pip:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Scrape everything
```bash
uv run scraper.py
```

### Scrape specific categories using aliases
```bash
uv run scraper.py -c py -c tut        # Python API + tutorials
uv run scraper.py -c gs               # Getting started only
uv run scraper.py -c cpp --force      # C++ API, overwrite existing
```

### All options

| Option | Description |
|--------|-------------|
| `-c, --category` | Category to scrape (repeatable). See aliases below |
| `-o, --output` | Output directory (default: `./doc`) |
| `-v, --verbose` | Enable verbose output |
| `--dry-run` | Preview what would be scraped without downloading |
| `--force` | Overwrite existing files |
| `--version` | Show version |

### Category aliases

| Category | Aliases | Description |
|----------|---------|-------------|
| `getting-started` | `gs`, `getting_started` | Setup and installation guides |
| `tutorials` | `tut`, `tutorial` | Step-by-step plugin tutorials |
| `reference/python` | `py`, `python` | Complete Python API reference |
| `reference/cpp` | `cpp`, `c++` | Complete C++ API reference |

No `-c` flag = scrape all categories.

## Output Structure

```
doc/
├── getting-started/
│   ├── installation.md
│   ├── start-your-server.md
│   ├── project-structure.md
│   └── contributing.md
├── tutorials/
│   ├── create-your-first-plugin.md
│   ├── install-your-plugin.md
│   ├── use-color-codes.md
│   ├── register-commands.md
│   ├── register-event-listeners.md
│   ├── schedule-tasks.md
│   └── publish-your-plugin.md
└── reference/
    ├── python/
    │   ├── server.md
    │   ├── player.md
    │   ├── actor.md
    │   └── ...
    └── cpp/
        ├── classendstone_1_1Server.md
        ├── classendstone_1_1Player.md
        └── ...
```

## Requirements

- Python 3.10+
- See `pyproject.toml` for dependencies

## License

MIT

## Links

- [Endstone Documentation](https://endstone.dev/latest/)
- [Endstone GitHub](https://github.com/EndstoneMC/endstone)
- [Endstone Discord](https://discord.gg/endstone)
