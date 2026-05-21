"""
Command-line interface for the Endstone documentation scraper.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from endstone_scraper.scraper import EndstoneScraper, print_results

console = Console()

CATEGORY_ALIASES: dict[str, str] = {
    "getting-started": "getting-started",
    "gs": "getting-started",
    "getting_started": "getting-started",
    "tutorials": "tutorials",
    "tut": "tutorials",
    "tutorial": "tutorials",
    "reference/python": "reference/python",
    "python": "reference/python",
    "py": "reference/python",
    "reference/cpp": "reference/cpp",
    "cpp": "reference/cpp",
    "c++": "reference/cpp",
}

VALID_CATEGORIES = {
    "getting-started",
    "tutorials",
    "reference/python",
    "reference/cpp",
}

CATEGORY_INFO: dict[str, tuple[str, str]] = {
    "getting-started": ("Getting Started", "Setup and installation guides"),
    "tutorials": ("Tutorials", "Step-by-step tutorials"),
    "reference/python": ("Python API", "Complete Python API reference"),
    "reference/cpp": ("C++ API", "Complete C++ API reference"),
}


def resolve_category(name: str) -> str:
    return CATEGORY_ALIASES.get(name.lower(), name.lower())


def validate_categories(names: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for name in names:
        cat = resolve_category(name)
        if cat not in VALID_CATEGORIES:
            invalid.append(name)
        elif cat not in seen:
            resolved.append(cat)
            seen.add(cat)
    return resolved, invalid


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endstone-scrape",
        description="Scrape Endstone.dev documentation into local markdown files.",
        epilog=(
            "Examples:\n"
            "  %(prog)s                              # Scrape all documentation\n"
            "  %(prog)s -c python -o ./docs          # Scrape only Python API\n"
            "  %(prog)s -c gs -c tut                 # Scrape getting-started and tutorials\n"
            "  %(prog)s -c cpp --force               # Scrape C++ API, overwrite existing\n"
            "  %(prog)s --dry-run                    # Show what would be scraped\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--category",
        dest="categories",
        action="append",
        help=(
            "Categories to scrape (can be specified multiple times). "
            "Short aliases: gs, tut, py, cpp. "
            "Full names: getting-started, tutorials, reference/python, reference/cpp. "
            "If not specified, all categories are scraped."
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        default="doc",
        help="Output directory for scraped documentation (default: ./doc)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without downloading files",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def show_banner() -> None:
    banner = Panel(
        "[bold cyan]MCEndstoneDocScraper[/bold cyan]\n"
        "Endstone.dev Documentation Scraper\n\n"
        "[dim]Scrapes Python & C++ API documentation for Endstone Minecraft Bedrock Server[/dim]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(banner)


def show_categories() -> None:
    table = Table(title="[bold]Available Documentation Categories[/bold]", show_header=True)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Aliases", style="dim")
    table.add_column("Description", style="dim")

    aliases_for: dict[str, list[str]] = {}
    for alias, canonical in CATEGORY_ALIASES.items():
        if alias != canonical:
            aliases_for.setdefault(canonical, []).append(alias)

    for key, (_, description) in CATEGORY_INFO.items():
        alias_str = ", ".join(sorted(aliases_for.get(key, [])))
        table.add_row(key, alias_str, description)

    console.print(table)


def main(args: list[str] | None = None) -> int:
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    show_banner()

    if parsed_args.categories:
        resolved, invalid = validate_categories(parsed_args.categories)
        if invalid:
            console.print(f"[red]Unknown categories:[/red] {', '.join(invalid)}")
            console.print(f"[dim]Valid categories: {', '.join(sorted(VALID_CATEGORIES))}")
            alias_hints = [f"{k} -> {v}" for k, v in CATEGORY_ALIASES.items() if k != v]
            console.print(f"[dim]Aliases: {', '.join(alias_hints)}")
            return 1
        categories = resolved
    else:
        categories = None

    show_categories()

    console.print()
    if categories:
        console.print(f"[info]Categories to scrape:[/info] {', '.join(categories)}")
    else:
        console.print("[info]Scraping all categories[/info]")

    console.print(f"[info]Output directory:[/info] {Path(parsed_args.output).absolute()}")

    if parsed_args.force:
        console.print("[warning]Force mode: Existing files will be overwritten[/warning]")

    console.print()

    scraper = EndstoneScraper(
        output_dir=parsed_args.output,
        verbose=parsed_args.verbose,
    )

    try:
        results = scraper.scrape_all(
            categories=categories,
            dry_run=parsed_args.dry_run,
            force=parsed_args.force,
        )

        if not parsed_args.dry_run:
            print_results(results)

        if results.get("failed", 0) > 0:
            return 1

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
