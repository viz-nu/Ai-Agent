import asyncio
import re
import json
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def crawl_and_store(urls: List[str]):
    browser_config = BrowserConfig(headless=True, user_agent_mode="random", text_mode=True, light_mode=True)
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=10000)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        results = await crawler.arun_many(urls, config=crawl_config)
        final_data = []
        for url, result in zip(urls, results):
            if result.success:
                content = re.sub(r"!\[.*?\]\(.*?\)", "",result.markdown)  # Remove images
                # Remove markdown links
                content = re.sub(r"(\* \[.*?\]\(.*?\)\n)+", "", content)
                content = re.sub(r"\n{2,}", "\n", content).strip()
                final_data.append(
                    {"success": True, "url": url, "error": None, "content": content})
            else:
                final_data.append(
                    {"success": False, "url": url, "error": result.error_message, "content": None})
        return final_data

    finally:
        await crawler.close()
