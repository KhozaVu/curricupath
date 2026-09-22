"""HTML entry point for the lightweight CurricuPath advisor UI."""

from pathlib import Path


_PAGE_PATH = Path(__file__).with_name("advisor_page.html")


def advisor_page_html() -> str:
    """Load the browser UI without introducing a template dependency."""

    return _PAGE_PATH.read_text(encoding="utf-8")
