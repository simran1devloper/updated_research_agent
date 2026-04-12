"""Outbound adapter: web page fetcher (httpx first, Playwright fallback)."""
import logging
import httpx

from ...domain.ports import IWebFetcher

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ResearchBot/1.0; +https://github.com/research-agent)"
    )
}


class WebFetcherAdapter(IWebFetcher):
    async def is_alive(self, url: str) -> bool:
        if not url or not url.startswith("http"):
            return False
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                resp = await client.head(url, headers=_HEADERS)
                return resp.status_code < 400
        except Exception:
            return False

    async def fetch(self, url: str) -> str | None:
        # Try httpx first (fast)
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers=_HEADERS)
                if resp.status_code == 200:
                    return self._extract_text(resp.text)
        except Exception:
            pass

        # Playwright fallback for JS-heavy pages
        return await self._playwright_fetch(url)

    def _extract_text(self, html: str) -> str:
        """Naive tag stripper — good enough for most pages."""
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:5000].strip()

    async def _playwright_fetch(self, url: str) -> str | None:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=20_000)
                content = await page.content()
                await browser.close()
                return self._extract_text(content)
        except Exception as exc:
            logger.debug("Playwright fetch failed for %s: %s", url, exc)
            return None
