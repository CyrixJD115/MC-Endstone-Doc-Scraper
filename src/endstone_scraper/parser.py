"""
Parser module for converting Endstone.dev HTML to Markdown.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md


class EndstoneParser:
    """Parser for converting Endstone.dev HTML to clean Markdown."""

    # Tags to remove from the content
    REMOVE_TAGS = [
        "nav",
        "header",
        "footer",
        ".md-header",
        ".md-tabs",
        ".md-sidebar",
        ".md-footer",
        ".md-top",
        ".md-search",
        ".skip-to-content",
    ]

    # Tags that should be converted differently
    CUSTOM_CONVERTERS = {
        # Custom handling for code blocks, tables, etc.
    }

    def __init__(self):
        """Initialize the parser."""
        self.base_url = ""

    def parse_to_markdown(self, html_content: str, base_url: str = "") -> str:
        """Convert HTML content to clean Markdown.

        Args:
            html_content: Raw HTML content
            base_url: Base URL for converting relative links

        Returns:
            Cleaned Markdown content
        """
        if not html_content:
            return "# Error: Empty HTML content\n"

        self.base_url = base_url

        try:
            soup = BeautifulSoup(html_content, "lxml")
        except Exception as e:
            return f"# Error: Could not parse HTML - {e}\n"

        # Remove navigation, header, footer elements
        self._cleanup_html(soup)

        # Extract the main content
        main_content = self._extract_main_content(soup)

        if not main_content:
            # Fallback: try to extract text from body or entire document
            if soup.body:
                main_content = soup.body
            else:
                main_content = soup

        # Convert relative links to absolute
        try:
            self._fix_links(main_content)
        except Exception:
            pass  # Continue even if link fixing fails

        # Clean up special elements
        try:
            self._clean_special_elements(main_content)
        except Exception:
            pass  # Continue even if special element cleaning fails

        # Convert to markdown
        try:
            markdown_text = md(
                str(main_content),
                heading_style="ATX",
                bullets="*",
                strip=["script", "style"],
            )
        except Exception as e:
            return f"# Error: Could not convert to markdown - {e}\n"

        # Post-process markdown
        try:
            markdown_text = self._post_process_markdown(markdown_text)
        except Exception:
            pass  # Return raw markdown if post-processing fails

        return markdown_text

    def _cleanup_html(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from the HTML.

        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove elements by CSS selector
        for selector in self.REMOVE_TAGS:
            for elem in soup.select(selector):
                elem.decompose()

        # Remove common navigation/search elements
        for elem in soup.find_all(class_=["md-search", "md-nav", "md-footer-meta"]):
            elem.decompose()

    def _extract_main_content(self, soup: BeautifulSoup) -> Tag | None:
        """Extract the main article content from the HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            Tag containing the main content, or None if not found
        """
        # MkDocs Material theme uses various main content containers
        # Try different selectors
        selectors = [
            "article",
            "main article",
            ".md-content",
            ".markdown",
            "[role='main']",
            "main .md-content__inner",
        ]

        for selector in selectors:
            main = soup.select_one(selector)
            if main:
                return main

        # Fallback: find the largest content div
        candidates = []
        for div in soup.find_all("div"):
            text = div.get_text()
            if len(text) > 500:  # Arbitrary threshold
                candidates.append((div, len(text)))

        if candidates:
            return max(candidates, key=lambda x: x[1])[0]

        return soup.body

    def _fix_links(self, content: Tag) -> None:
        """Convert relative links to absolute links.

        Args:
            content: Tag containing the content
        """
        if content is None:
            return

        for link in content.find_all("a", href=True):
            if link is None:
                continue

            href = link.get("href", "")
            if not href:
                continue

            # Skip anchor links and external links
            if href.startswith("#") or href.startswith(("http://", "https://", "mailto:")):
                continue

            # Convert relative links to absolute
            if href.startswith("/"):
                link["href"] = "https://endstone.dev/latest" + href
            elif href.startswith("./") or href.startswith("../"):
                # Handle relative paths - this is simplified
                if "latest" in self.base_url:
                    base = self.base_url.split("latest/")[0] + "latest/"
                else:
                    base = "https://endstone.dev/latest/"

                # Normalize the path
                parts = href.split("../")
                clean_href = parts[-1] if parts else href
                link["href"] = base + clean_href

    def _clean_special_elements(self, content: Tag) -> None:
        """Clean up special elements like admonitions, code blocks, etc.

        Args:
            content: Tag containing the content
        """
        if content is None:
            return

        # Clean up admonitions (note, warning, tip, etc.)
        try:
            for admonition in content.find_all(class_=re.compile(r"admonition|hint|note|warning|tip|caution|danger")):
                if admonition is None:
                    continue

                # Add type indicator
                classes = admonition.get("class", []) or []
                admonition_type = "Note"

                for cls in classes:
                    if "note" in cls:
                        admonition_type = "Note"
                    elif "warning" in cls:
                        admonition_type = "Warning"
                    elif "tip" in cls:
                        admonition_type = "Tip"
                    elif "danger" in cls:
                        admonition_type = "Danger"
                    elif "caution" in cls:
                        admonition_type = "Caution"
                    elif "important" in cls:
                        admonition_type = "Important"

                # Add type as a header - with None check
                title_elem = None
                for tag in ["p", "div", "span"]:
                    title_elem = admonition.find(tag, class_=re.compile(r"title|admonition-title"))
                    if title_elem:
                        break

                if title_elem:
                    title_text = title_elem.get_text().strip() if hasattr(title_elem, 'get_text') else admonition_type
                    title_elem.decompose()
                else:
                    title_text = admonition_type

                # Insert markdown-style blockquote indicator
                prefix = f"> **{admonition_type}:** {title_text}\n> "

                # Convert children to blockquote format
                for p in admonition.find_all("p"):
                    try:
                        p.insert_before(prefix)
                        prefix = "> "
                    except Exception:
                        pass
        except Exception:
            pass  # Skip if admonition processing fails

        # Clean up code blocks with language info
        try:
            for code_block in content.find_all("code", class_=re.compile(r"language-|highlight-")):
                if code_block is None:
                    continue

                classes = code_block.get("class", []) or []
                language = "text"

                for cls in classes:
                    if isinstance(cls, str):
                        if cls.startswith("language-"):
                            language = cls.replace("language-", "")
                        elif cls.startswith("highlight-"):
                            language = cls.replace("highlight-", "")

                # Add language info as a comment or indicator
                if language != "text":
                    # Store language for markdown conversion
                    code_block["data-language"] = language
        except Exception:
            pass  # Skip if code block processing fails

        # Fix image references
        try:
            for img in content.find_all("img", src=True):
                if img is None:
                    continue

                src = img.get("src", "")
                if not src:
                    continue

                if src.startswith("/"):
                    img["src"] = "https://endstone.dev/latest" + src
                elif src.startswith("./") or src.startswith("../"):
                    # Handle relative paths
                    if "latest" in self.base_url:
                        base_path = self.base_url.rsplit("/", 1)[0] + "/"
                    else:
                        base_path = "https://endstone.dev/latest/"
                    img["src"] = base_path + src.lstrip("./")
        except Exception:
            pass  # Skip if image processing fails

    def _post_process_markdown(self, markdown: str) -> str:
        """Clean up and improve the markdown output.

        Args:
            markdown: Raw markdown output

        Returns:
            Cleaned markdown
        """
        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Clean up code blocks
        markdown = re.sub(r"```\s*\n\s*```", "```\n```", markdown)

        # Fix table formatting issues
        markdown = re.sub(r"\|\s+\|", "| |", markdown)

        # Remove duplicate headers (MkDocs sometimes adds page title in content)
        lines = markdown.split("\n")
        if len(lines) > 2:
            first_line = lines[0].strip()
            second_line = lines[1].strip() if len(lines) > 1 else ""

            # Check if first two lines form a heading (underlined with = or -)
            if first_line.startswith("#") and second_line.startswith("#"):
                # Check if they're similar
                first_text = re.sub(r"[#\\-\\=\\s]+", "", first_line).lower()
                second_text = re.sub(r"[#\\-\\=\\s]+", "", second_line).lower()

                if first_text == second_text or len(first_text) == 0:
                    lines = lines[1:]

            markdown = "\n".join(lines)

        # Fix empty links
        markdown = re.sub(r"\\[\\]\\(.*?\\)", "", markdown)

        # Clean up HTML entities
        markdown = unescape(markdown)

        # Remove trailing whitespace from each line
        lines = markdown.split("\n")
        lines = [line.rstrip() for line in lines]
        markdown = "\n".join(lines)

        # Ensure single trailing newline
        markdown = markdown.rstrip() + "\n"

        return markdown


def extract_title(html_content: str) -> str:
    """Extract the title from HTML content.

    Args:
        html_content: Raw HTML content

    Returns:
        Page title
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Try to find title from various sources
    title_selectors = [
        "h1",
        "title",
        "meta[property='og:title']",
        ".md-typeset h1",
    ]

    for selector in title_selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == "meta":
                return elem.get("content", "Untitled")
            return elem.get_text().strip()

    return "Untitled"


def extract_description(html_content: str) -> str:
    """Extract the description from HTML content.

    Args:
        html_content: Raw HTML content

    Returns:
        Page description
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Try meta description
    meta_desc = soup.select_one("meta[name='description']")
    if meta_desc:
        return meta_desc.get("content", "")

    # Try og:description
    og_desc = soup.select_one("meta[property='og:description']")
    if og_desc:
        return og_desc.get("content", "")

    # Fallback to first paragraph
    first_p = soup.select_one("p")
    if first_p:
        text = first_p.get_text().strip()
        return text[:200] + "..." if len(text) > 200 else text

    return ""
