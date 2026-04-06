"""Playwright MCP Server - browser automation via Playwright."""

from mcp.server.fastmcp import FastMCP
from typing import Optional
import asyncio

mcp = FastMCP("playwright")

_browser = None
_context = None
_page = None


async def _get_browser():
    global _browser, _context, _page
    if _browser is None:
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(headless=True)
        _context = await _browser.new_context()
        _page = await _context.new_page()
    return _browser, _context, _page


@mcp.tool()
async def navigate(url: str) -> dict:
    """Navigate to a URL and return page info."""
    try:
        _, _, page = await _get_browser()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
            "ok": response.ok if response else False,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def screenshot(path: Optional[str] = None, full_page: bool = False) -> dict:
    """Take a screenshot of the current page."""
    try:
        _, _, page = await _get_browser()
        import tempfile
        import os

        if path is None:
            path = os.path.join(tempfile.gettempdir(), "playwright_screenshot.png")
        await page.screenshot(path=path, full_page=full_page)
        return {"path": path, "url": page.url}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def click(selector: str) -> dict:
    """Click an element on the page."""
    try:
        _, _, page = await _get_browser()
        await page.click(selector, timeout=10000)
        return {"clicked": selector, "url": page.url}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def fill(selector: str, value: str) -> dict:
    """Fill a form field."""
    try:
        _, _, page = await _get_browser()
        await page.fill(selector, value, timeout=10000)
        return {"filled": selector, "value": value}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_text(selector: str) -> dict:
    """Get text content of an element."""
    try:
        _, _, page = await _get_browser()
        text = await page.text_content(selector, timeout=10000)
        return {"selector": selector, "text": text}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def evaluate(js: str) -> dict:
    """Execute JavaScript in the page context."""
    try:
        _, _, page = await _get_browser()
        result = await page.evaluate(js)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_content() -> dict:
    """Get the full page HTML content."""
    try:
        _, _, page = await _get_browser()
        content = await page.content()
        return {"url": page.url, "content_length": len(content)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def close() -> dict:
    """Close the browser."""
    global _browser, _context, _page
    try:
        if _browser:
            await _browser.close()
            _browser = None
            _context = None
            _page = None
        return {"status": "closed"}
    except Exception as e:
        return {"error": str(e)}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
