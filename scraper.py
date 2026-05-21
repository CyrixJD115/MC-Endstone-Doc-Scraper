#!/usr/bin/env python3
"""
MCEndstoneDocScraper - Entrypoint script

Run this script to scrape Endstone.dev documentation.
"""

if __name__ == "__main__":
    from endstone_scraper.cli import main

    import sys

    sys.exit(main())
