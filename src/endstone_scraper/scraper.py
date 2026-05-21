"""
Main scraper module for Endstone.dev documentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

console = Console()

VALID_CATEGORIES = {"getting-started", "tutorials", "reference/python", "reference/cpp"}


class EndstoneScraper:
    """Scraper for Endstone.dev documentation."""

    BASE_URL = "https://endstone.dev/latest/"

    # Pages to scrape
    GETTING_STARTED_PAGES = [
        "getting-started/installation/",
        "getting-started/start-your-server/",
        "getting-started/project-structure/",
        "getting-started/contributing/",
    ]

    TUTORIAL_PAGES = [
        "tutorials/create-your-first-plugin/",
        "tutorials/install-your-plugin/",
        "tutorials/use-color-codes/",
        "tutorials/register-commands/",
        "tutorials/register-event-listeners/",
        "tutorials/schedule-tasks/",
        "tutorials/publish-your-plugin/",
    ]

    def __init__(self, output_dir: str | Path = "doc", verbose: bool = False):
        """Initialize the scraper.

        Args:
            output_dir: Directory to save scraped documentation
            verbose: Enable verbose output
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MCEndstoneDocScraper/0.1.0"})
        self.cpp_version: str | None = None  # Will be discovered when needed

    def fetch_page(self, path: str) -> str:
        """Fetch a page from the documentation.

        Args:
            path: URL path relative to BASE_URL, or full path with version prefix (e.g., "v0.9.0/reference/cpp/...")

        Returns:
            HTML content of the page

        Raises:
            requests.RequestException: If the request fails
        """
        # Check if path starts with a version prefix (e.g., "v0.9.0/") or "latest/"
        if re.match(r"^(v\d+\.\d+\.\d+|latest)/", path):
            # Use the version-specific base URL directly
            url = f"https://endstone.dev/{path}"
        else:
            url = urljoin(self.BASE_URL, path)

        if self.verbose:
            console.print(f"[dim]Fetching: {url}[/dim]")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def discover_python_api_pages(self) -> list[str]:
        """Discover all Python API reference pages from the reference index.

        Returns:
            List of URL paths for Python API pages
        """
        console.print("[info]Discovering Python API pages...[/info]")

        try:
            html = self.fetch_page("reference/")
            soup = BeautifulSoup(html, "lxml")

            # Find the Python API section in the navigation
            python_api_pages = []

            # Look for links in the sidebar/navigation
            # The site uses MkDocs Material theme
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                # Match Python API pages - look for paths that end with python/XXX/
                if href.endswith("/") and "python" in href:
                    # Normalize the path
                    if href.startswith("../"):
                        # ../python/actor/ -> reference/python/actor/
                        path = "reference/" + href.replace("../", "")
                    elif href.startswith("./"):
                        path = "reference/" + href.replace("./", "")
                    elif href.startswith("/"):
                        path = href.lstrip("/")
                    else:
                        path = "reference/" + href

                    # Remove any duplicate 'reference/' in path
                    path = re.sub(r"reference/.*reference/", "reference/", path)

                    # Only include actual Python API pages (not the index)
                    if (path.startswith("reference/python/") and
                        path != "reference/python/" and
                        path not in python_api_pages):
                        python_api_pages.append(path)

            # If discovery didn't find pages, use known list
            if not python_api_pages:
                console.print("[warning]Could not discover pages from HTML, using known list[/warning]")
                python_api_pages = self._get_known_python_api_pages()

            console.print(f"[info]Found {len(python_api_pages)} Python API pages[/info]")
            return sorted(python_api_pages)

        except Exception as e:
            console.print(f"[warning]Error discovering pages: {e}[/warning]")
            console.print("[info]Using known Python API pages[/info]")
            return self._get_known_python_api_pages()

    def _get_known_python_api_pages(self) -> list[str]:
        """Return known Python API pages as fallback.

        Returns:
            List of known Python API page paths
        """
        return [
            "reference/python/server/",
            "reference/python/player/",
            "reference/python/actor/",
            "reference/python/attribute/",
            "reference/python/ban/",
            "reference/python/block/",
            "reference/python/boss/",
            "reference/python/command/",
            "reference/python/damage/",
            "reference/python/enchantments/",
            "reference/python/event/",
            "reference/python/form/",
            "reference/python/language/",
            "reference/python/level/",
            "reference/python/inventory/",
            "reference/python/map/",
            "reference/python/nbt/",
            "reference/python/permissions/",
            "reference/python/plugin/",
            "reference/python/potion/",
            "reference/python/scoreboard/",
            "reference/python/scheduler/",
        ]

    def discover_cpp_api_pages(self) -> list[str]:
        """Discover all C++ API reference pages from the Doxygen documentation.

        Returns:
            List of URL paths for C++ API pages (including version prefix)
        """
        console.print("[info]Discovering C++ API pages...[/info]")

        version = "latest"

        # First, try to determine the current version
        # The C++ docs are typically not available at 'latest', so we need to find a specific version
        try:
            # Try to access the classes page at latest
            response = self.session.get(
                "https://endstone.dev/latest/reference/cpp/classes/",
                timeout=30
            )
            if response.status_code != 200:
                # latest doesn't have cpp, try to find the version from a page
                response = self.session.get(
                    "https://endstone.dev/latest/reference/python/server/",
                    timeout=30
                )
                if response.ok:
                    try:
                        soup = BeautifulSoup(response.text, "lxml")
                        # Look for version links in the navigation
                        version_links = soup.find_all("a", href=re.compile(r"^/v\d+\.\d+\.\d+"))
                        if version_links:
                            href = version_links[0].get("href", "")
                            match = re.search(r"/v(\d+\.\d+\.\d+)", href)
                            if match:
                                version = f"v{match.group(1)}"
                    except Exception:
                        pass  # BeautifulSoup parsing failed, will try fallback versions below

                # If still using "latest", try some known versions
                if version == "latest":
                    for test_version in ["v0.9.0", "v0.8.0", "v0.7.0", "v0.6.0", "v0.5.7.1"]:
                        test_url = f"https://endstone.dev/{test_version}/reference/cpp/classes/"
                        test_response = self.session.get(test_url, timeout=10)
                        if test_response.status_code == 200:
                            version = test_version
                            break
        except requests.RequestException:
            # On network error, try fallback versions
            for test_version in ["v0.9.0", "v0.8.0", "v0.7.0"]:
                try:
                    test_url = f"https://endstone.dev/{test_version}/reference/cpp/classes/"
                    test_response = self.session.get(test_url, timeout=10)
                    if test_response.status_code == 200:
                        version = test_version
                        break
                except requests.RequestException:
                    continue

        # Store the version for use in scraping
        self.cpp_version = version
        console.print(f"[dim]Using C++ API version: {version}[/dim]")

        try:
            # Fetch the classes index page directly
            base_url = f"https://endstone.dev/{version}/reference/cpp/"
            classes_url = urljoin(base_url, "classes/")

            response = self.session.get(classes_url, timeout=30)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, "lxml")

            cpp_api_pages = []

            # Extract class links from the class index page
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                # Match class pages (classXXX_1_1YYY/)
                if "class" in href and href.endswith("/"):
                    # Extract just the class name (e.g., classendstone_1_1Server)
                    class_name = href.rstrip("/").split("/")[-1]
                    # Return path with version prefix
                    path = f"{version}/reference/cpp/{class_name}/"
                    if path not in cpp_api_pages:
                        cpp_api_pages.append(path)

            # Also try to discover namespace and file pages
            for page_type in ["namespace", "file", "struct", "union"]:
                try:
                    page_url = urljoin(base_url, f"{page_type}s/")
                    response = self.session.get(page_url, timeout=30)
                    if response.ok:
                        page_html = response.text
                        page_soup = BeautifulSoup(page_html, "lxml")
                        for link in page_soup.find_all("a", href=True):
                            href = link.get("href", "")
                            if page_type in href and href.endswith("/"):
                                # Extract just the page name
                                page_name = href.rstrip("/").split("/")[-1]
                                path = f"{version}/reference/cpp/{page_name}/"
                                if path not in cpp_api_pages:
                                    cpp_api_pages.append(path)
                except requests.RequestException:
                    continue

            # If discovery didn't find pages, use known list
            if not cpp_api_pages:
                console.print("[warning]Could not discover C++ pages from HTML, using known list[/warning]")
                cpp_api_pages = self._get_known_cpp_api_pages(version)

            console.print(f"[info]Found {len(cpp_api_pages)} C++ API pages[/info]")
            return sorted(cpp_api_pages)

        except Exception as e:
            console.print(f"[warning]Error discovering C++ pages: {e}[/warning]")
            console.print("[info]Using known C++ API pages[/info]")
            return self._get_known_cpp_api_pages(version)

    def _get_known_cpp_api_pages(self, version: str = "latest") -> list[str]:
        """Return known C++ API pages as fallback.

        Args:
            version: Version string (e.g., "latest", "v0.9.0")

        Returns:
            List of known C++ API page paths
        """
        # Common C++ classes and their Doxygen-style names
        known_classes = [
            "classendstone_1_1Server",
            "classendstone_1_1Player",
            "classendstone_1_1Actor",
            "classendstone_1_1Level",
            "classendstone_1_1Command",
            "classendstone_1_1CommandSender",
            "classendstone_1_1ConsoleCommandSender",
            "classendstone_1_1Plugin",
            "classendstone_1_1PluginManager",
            "classendstone_1_1PluginDescription",
            "classendstone_1_1Scheduler",
            "classendstone_1_1Task",
            "classendstone_1_1Event",
            "classendstone_1_1EventHandler",
            "classendstone_1_1HandlerList",
            "classendstone_1_1Cancellable",
            "classendstone_1_1ICancellable",
            "classendstone_1_1Logger",
            "classendstone_1_1Scoreboard",
            "classendstone_1_1Objective",
            "classendstone_1_1Score",
            "classendstone_1_1Team",
            "classendstone_1_1Inventory",
            "classendstone_1_1PlayerInventory",
            "classendstone_1_1ItemStack",
            "classendstone_1_1ItemType",
            "classendstone_1_1ItemFactory",
            "classendstone_1_1ItemMeta",
            "classendstone_1_1Block",
            "classendstone_1_1BlockData",
            "classendstone_1_1BlockState",
            "classendstone_1_1BlockStates",
            "classendstone_1_1BossBar",
            "classendstone_1_1Permission",
            "classendstone_1_1Permissible",
            "classendstone_1_1PermissionAttachment",
            "classendstone_1_1PermissionAttachmentInfo",
            "classendstone_1_1BanList",
            "classendstone_1_1PlayerBanList",
            "classendstone_1_1IpBanList",
            "classendstone_1_1BanEntry",
            "classendstone_1_1PlayerBanEntry",
            "classendstone_1_1IpBanEntry",
            "classendstone_1_1Form",
            "classendstone_1_1ModalForm",
            "classendstone_1_1MessageForm",
            "classendstone_1_1ActionForm",
            "classendstone_1_1Label",
            "classendstone_1_1Button",
            "classendstone_1_1Toggle",
            "classendstone_1_1Slider",
            "classendstone_1_1StepSlider",
            "classendstone_1_1Dropdown",
            "classendstone_1_1TextInput",
            "classendstone_1_1Image",
            "classendstone_1_1Vector",
            "classendstone_1_1Location",
            "classendstone_1_1Position",
            "classendstone_1_1Dimension",
            "classendstone_1_1Chunk",
            "classendstone_1_1UUID",
            "classendstone_1_1NamespacedKey",
            "classendstone_1_1Skin",
            "classendstone_1_1Language",
            "classendstone_1_1Registry",
            "classendstone_1_1Service",
            "classendstone_1_1ServiceManager",
            "classendstone_1_1Color",
            "classendstone_1_1ColorFormat",
            "classendstone_1_1Colors",
            "classendstone_1_1Translatable",
            "classendstone_1_1DamageSource",
            "classendstone_1_1Enchantment",
            "classendstone_1_1MapCanvas",
            "classendstone_1_1MapRenderer",
            "classendstone_1_1MapView",
            "classendstone_1_1MapMeta",
            "classendstone_1_1SocketAddress",
            "classendstone_1_1Recipe",
            # Events
            "classendstone_1_1ActorEvent",
            "classendstone_1_1ActorDamageEvent",
            "classendstone_1_1ActorDeathEvent",
            "classendstone_1_1ActorExplodeEvent",
            "classendstone_1_1ActorKnockbackEvent",
            "classendstone_1_1ActorRemoveEvent",
            "classendstone_1_1ActorSpawnEvent",
            "classendstone_1_1ActorTeleportEvent",
            "classendstone_1_1BlockEvent",
            "classendstone_1_1BlockBreakEvent",
            "classendstone_1_1BlockPlaceEvent",
            "classendstone_1_1BlockPistonEvent",
            "classendstone_1_1PlayerEvent",
            "classendstone_1_1PlayerJoinEvent",
            "classendstone_1_1PlayerQuitEvent",
            "classendstone_1_1PlayerKickEvent",
            "classendstone_1_1PlayerLoginEvent",
            "classendstone_1_1PlayerDeathEvent",
            "classendstone_1_1PlayerRespawnEvent",
            "classendstone_1_1PlayerTeleportEvent",
            "classendstone_1_1PlayerMoveEvent",
            "classendstone_1_1PlayerChatEvent",
            "classendstone_1_1PlayerCommandEvent",
            "classendstone_1_1PlayerInteractEvent",
            "classendstone_1_1PlayerInteractActorEvent",
            "classendstone_1_1PlayerDropItemEvent",
            "classendstone_1_1PlayerItemConsumeEvent",
            "classendstone_1_1PlayerEmoteEvent",
            "classendstone_1_1PlayerJumpEvent",
            "classendstone_1_1PlayerGameModeChangeEvent",
            "classendstone_1_1ServerEvent",
            "classendstone_1_1ServerLoadEvent",
            "classendstone_1_1ServerCommandEvent",
            "classendstone_1_1ServerListPingEvent",
            "classendstone_1_1PluginEnableEvent",
            "classendstone_1_1PluginDisableEvent",
            "classendstone_1_1BroadcastMessageEvent",
            "classendstone_1_1ScriptMessageEvent",
            "classendstone_1_1PacketSendEvent",
            "classendstone_1_1PacketReceiveEvent",
            "classendstone_1_1WeatherEvent",
            "classendstone_1_1WeatherChangeEvent",
            "classendstone_1_1ThunderChangeEvent",
            # Namespaces
            "namespaceendstone",
            "namespacefmt",
            "namespacestd",
        ]

        return [f"{version}/reference/cpp/{cls}/" for cls in known_classes]

    def get_all_pages(self, categories: list[str] | None = None) -> dict[str, list[str]]:
        """Get pages to scrape, organized by category.

        Only discovers pages for the requested categories to avoid
        unnecessary network requests.

        Args:
            categories: List of categories to fetch. If None, fetch all.

        Returns:
            Dictionary with categories as keys and lists of paths as values
        """
        requested = set(categories) if categories else VALID_CATEGORIES
        pages: dict[str, list[str]] = {}

        if "getting-started" in requested:
            pages["getting-started"] = self.GETTING_STARTED_PAGES
        if "tutorials" in requested:
            pages["tutorials"] = self.TUTORIAL_PAGES
        if "reference/python" in requested:
            pages["reference/python"] = self.discover_python_api_pages()
        if "reference/cpp" in requested:
            pages["reference/cpp"] = self.discover_cpp_api_pages()

        return pages

    def scrape_page(self, path: str, output_path: Path) -> tuple[bool, str]:
        """Scrape a single page and save as markdown.

        Args:
            path: URL path to scrape
            output_path: File path to save the markdown output

        Returns:
            Tuple of (success, message)
        """
        try:
            html = self.fetch_page(path)

            # Import here to avoid circular import
            from endstone_scraper.parser import EndstoneParser

            # Construct the base URL for the parser
            if re.match(r"^(v\d+\.\d+\.\d+|latest)/", path):
                base_url = f"https://endstone.dev/{path}"
            else:
                base_url = urljoin(self.BASE_URL, path)

            parser = EndstoneParser()
            markdown = parser.parse_to_markdown(html, base_url=base_url)

            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write markdown file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            return True, f"Saved to {output_path}"

        except Exception as e:
            return False, str(e)

    def scrape_all(
        self,
        categories: list[str] | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Scrape documentation pages.

        Args:
            categories: List of categories to scrape ('getting-started', 'tutorials', 'reference/python', 'reference/cpp')
                        If None, scrape all categories
            dry_run: If True, show what would be scraped without downloading
            force: If True, overwrite existing files

        Returns:
            Dictionary with scraping statistics
        """
        all_pages = self.get_all_pages(categories=categories)

        # Count total pages
        total_pages = sum(len(pages) for pages in all_pages.values())

        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        if dry_run:
            console.print("[yellow]Dry run mode - no files will be downloaded[/yellow]")
            for category, pages in all_pages.items():
                console.print(f"\n[bold]{category}:[/bold]")
                for page in pages:
                    output_path = self._get_output_path(category, page)
                    console.print(f"  {page} -> {output_path}")
            return results

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scraping documentation...", total=total_pages)

            for category, pages in all_pages.items():
                progress.update(task, description=f"[cyan]Scraping {category}...")

                for page in pages:
                    output_path = self._get_output_path(category, page)

                    # Check if file exists
                    if output_path.exists() and not force:
                        results["skipped"] += 1
                        progress.advance(task)
                        continue

                    success, message = self.scrape_page(page, output_path)

                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({"page": page, "error": message})

                    progress.advance(task)

        return results

    def _get_output_path(self, category: str, page: str) -> Path:
        """Get the output file path for a page.

        Args:
            category: Category of the page
            page: URL path of the page

        Returns:
            Path where the markdown file should be saved
        """
        # Extract filename from path
        # Remove trailing slash and get last component
        clean_path = page.rstrip("/")
        filename = clean_path.split("/")[-1]

        # Add .md extension
        if not filename.endswith(".md"):
            filename += ".md"

        # For index pages, use README.md
        if filename in ["installation.md", "server.md"]:
            # These could be the main pages for their sections
            pass

        return self.output_dir / category / filename


def print_results(results: dict[str, Any]) -> None:
    """Print scraping results.

    Args:
        results: Results dictionary from scrape_all()
    """
    console.print("\n[bold]Scraping Results:[/bold]")
    console.print(f"  [green]Success:[/green] {results['success']}")
    console.print(f"  [yellow]Skipped:[/yellow] {results['skipped']}")
    console.print(f"  [red]Failed:[/red] {results['failed']}")

    if results["errors"]:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in results["errors"]:
            console.print(f"  [red]✗[/red] {error['page']}: {error['error']}")
