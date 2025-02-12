# script.py
import sys
import requests
from xml.etree import ElementTree
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from typing import List
from langchain.text_splitter import MarkdownTextSplitter
import os
import sys
import psutil
import asyncio
import requests
from xml.etree import ElementTree
from rich import print
import re
from pymongo import MongoClient
import json
from datetime import datetime


async def crawl_parallel(urls: List[str], source: str = "", max_concurrent: int = 3, databaseConnectionStr: str = "", dbName: str = "", collectionName: str = "", institutionName: str = ""):
    # Track peak memory usage across all tasks
    peak_memory = 0
    process = psutil.Process(os.getpid())

    def log_memory(prefix: str = ""):
        nonlocal peak_memory
        current_mem = process.memory_info().rss  # in bytes
        if current_mem > peak_memory:
            peak_memory = current_mem
    browser_config = BrowserConfig(headless=True, verbose=False, extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],user_agent_mode="random",text_mode=True ,light_mode=True)
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS,page_timeout=10000)
    client = MongoClient(databaseConnectionStr)
    db = client[dbName]
    collection = db[collectionName]
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()
    final=[]
    try:
        success_count = 0
        fail_count = 0
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i: i + max_concurrent]
            tasks = []
            for j, url in enumerate(batch):
                session_id = f"parallel_session_{i + j}"
                task = crawler.arun(url=url, config=crawl_config, session_id=session_id)
                tasks.append(task)
            log_memory(f"Before batch {i//max_concurrent + 1}: ")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            log_memory(f"After batch {i//max_concurrent + 1}: ")
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    with open("errors.txt", "a") as f:
                        final.append({"success":False,'url': url, 'Error': result})
                        f.write(f"Failed to crawl: {url}\nError: {result}\n\n\n")
                    fail_count += 1
                elif result.success:
                    # Clean up content and split markdown
                    content = re.sub(r"!\[.*?\]\(.*?\)", "", result.markdown)
                    content = re.sub(r"(\* \[.*?\]\(.*?\)\n)+", "", content)
                    content = re.sub(r"\n{2,}", "\n", content).strip()
                    splitter = MarkdownTextSplitter()
                    split_documents = splitter.create_documents([content])
                    documents_to_insert = [{"metadata": {"source": source, "chunk_size": len(doc.page_content), "crawled_at": datetime.utcnow(), "url_path": url, "institutionName": institutionName}, "content": doc.page_content, "chunk_number": idx + 1} for idx, doc in enumerate(split_documents)]
                    if documents_to_insert:
                        collection.insert_many(documents_to_insert)
                    final.append({"success":True,'url': url, 'Error': None})
                    success_count += 1
                else:
                    with open("errors.txt", "a") as f:
                        final.append({"success":False,'url': url, 'Error': result})
                        f.write(f"Failed to crawl: {url}\nResult: {result}\n\n\n")
                    fail_count += 1
                print(f"failed:{fail_count},success:{success_count},total:{len(urls)}")
    except Exception as e:
        print({"error": f"An unexpected error occurred: {e}"})
    finally:
        await crawler.close()
        client.close()
        return {
            "success": success_count,
            "failed": fail_count,
            "peakMemoryUsage(MB)": peak_memory // (1024 * 1024),
            "finalData":final
        }


def get_all_urls_from_sitemap(sitemap_url, visited_sitemaps=None):
    if visited_sitemaps is None:
        visited_sitemaps = set()
    try:
        if sitemap_url in visited_sitemaps:
            return []
        
        response = requests.get(sitemap_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" })
        response.raise_for_status()
        
        root = ElementTree.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        visited_sitemaps.add(sitemap_url)
        
        urls = []
        for loc in root.findall('.//ns:loc', namespace):
            url = loc.text.strip()
            if url.endswith('.xml'):
                urls.extend(get_all_urls_from_sitemap(url, visited_sitemaps))
            else:
                urls.append(url)
        return urls
    except Exception as e:
        print(f"Error: {e}")
        return []
async def process_url(url):
    # step 1 fetch all links from sitemap
    urls = get_all_urls_from_sitemap(url)
    print(f"total {len(urls)} are to be processed")
    return urls
