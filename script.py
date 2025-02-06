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
    # We'll keep track of peak memory usage across all tasks
    peak_memory = 0
    process = psutil.Process(os.getpid())

    def log_memory(prefix: str = ""):
        nonlocal peak_memory
        current_mem = process.memory_info().rss  # in bytes
        if current_mem > peak_memory:
            peak_memory = current_mem
    # Minimal browser config
    browser_config = BrowserConfig(headless=True, verbose=False, extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"])
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    client = MongoClient(databaseConnectionStr)
    db = client[dbName]
    collection = db[collectionName]
    # Create the crawler instance
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()
    try:
        success_count = 0
        fail_count = 0
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i: i + max_concurrent]
            tasks = []
            for j, url in enumerate(batch):
                # Unique session_id per concurrent sub-task
                session_id = f"parallel_session_{i + j}"
                task = crawler.arun(
                    url=url, config=crawl_config, session_id=session_id)
                tasks.append(task)
            # Check memory usage prior to launching tasks
            log_memory(prefix=f"Before batch {i//max_concurrent + 1}: ")
            # Gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check memory usage after tasks complete
            log_memory(prefix=f"After batch {i//max_concurrent + 1}: ")
            # Evaluate results and save content to database
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    with open("errors.txt", "a") as f:
                        f.write(f"Failed to crawl: {url}\nError: {result}\n\n\n")
                    fail_count += 1
                elif result.success:
                    # Remove media references and inline images
                    content = re.sub(r"!\[.*?\]\(.*?\)", "", result.markdown)
                    # Remove duplicate links
                    content = re.sub(r"(\* \[.*?\]\(.*?\)\n)+", "", content)
                    # Remove extra whitespace
                    content = re.sub(r"\n{2,}", "\n", content).strip()
                    # Process the markdown text
                    splitter = MarkdownTextSplitter()
                    split_documents = splitter.create_documents([content])
                    # save the content in database
                    # documents_to_insert = [{"metadata": {"source": source, "chunk_size": len(doc.page_content), "crawled_at": datetime.utcnow(), "url_path": url, "institutionName": institutionName}, "content": doc.page_content, "chunk_number": idx + 1} for idx, doc in enumerate(split_documents)]
                    # if documents_to_insert:
                    #     collection.insert_many(documents_to_insert)
                    success_count += 1
                else:
                    with open("errors.txt", "a") as f:
                        f.write(f"Failed to crawl: {url}\nResult: {result}\n\n\n")
                    fail_count += 1
                print(f"failed:{fail_count},success:{success_count},total:{len(urls)}")
    except Exception as e:
        print({"error": "An unexpected error occurred: {e}"})
    finally:
        await crawler.close()
        client.close()
        return {
            "success": success_count,
            "failed": fail_count,
            "status": "success",
            "peakMemoryUsage(MB)": peak_memory // (1024 * 1024)
        }


def get_all_urls_from_sitemap(sitemap_url, visited_sitemaps=None):
    if visited_sitemaps is None:
        visited_sitemaps = set()
    try:
        if sitemap_url in visited_sitemaps:
            return []
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(sitemap_url, headers=headers)
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

def get_pydantic_ai_docs_urls(mainURL):
    sitemap_url = mainURL
    all_urls = get_all_urls_from_sitemap(sitemap_url)
    return all_urls


async def process_url(url, source, databaseConnectionStr, dbName, collectionName, institutionName):
    # step 1 fetch all links from sitemap
    urls = get_pydantic_ai_docs_urls(url)
    print(f"total {len(urls)} are to be processed")
    if urls:
        result = await crawl_parallel(urls, source, 10, databaseConnectionStr, dbName, collectionName, institutionName)
    else:
        result = {"status": "failed"}
    return result
async def run_process(url, source, databaseConnectionStr, dbName, collectionName, institutionName):
    result = await process_url(url, source, databaseConnectionStr, dbName, collectionName, institutionName)
    return result

    
