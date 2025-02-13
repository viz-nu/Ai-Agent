import asyncio
import re
import json
from datetime import datetime
from typing import List
from pymongo import MongoClient
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from langchain.text_splitter import MarkdownTextSplitter

async def crawl_and_store(urls: List[str], source: str, db_uri: str, db_name: str, collection_name: str, institution_name: str):
    browser_config = BrowserConfig(headless=True, user_agent_mode="random", text_mode=True, light_mode=True)
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=10000)
    
    client = MongoClient(db_uri)
    db = client[db_name]
    collection = db[collection_name]
    
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()
    
    try:
        results = await crawler.arun_many(urls, config=crawl_config)
        final_data = []
        
        for url, result in zip(urls, results):
            if result.success:
                content = re.sub(r"!\[.*?\]\(.*?\)", "", result.markdown)  # Remove images
                content = re.sub(r"(\* \[.*?\]\(.*?\)\n)+", "", content)  # Remove markdown links
                content = re.sub(r"\n{2,}", "\n", content).strip()
                
                splitter = MarkdownTextSplitter()
                split_docs = splitter.create_documents([content])
                
                documents = [{
                    "metadata": {
                        "source": source,
                        "chunk_size": len(doc.page_content),
                        "crawled_at": datetime.utcnow(),
                        "url_path": url,
                        "institutionName": institution_name
                    },
                    "content": doc.page_content,
                    "chunk_number": idx + 1
                } for idx, doc in enumerate(split_docs)]
                
                if documents:
                    collection.insert_many(documents)
                
                final_data.append({"success": True, "url": url, "error": None})
            else:
                final_data.append({"success": False, "url": url, "error": result.error_message})
                
        return final_data
    
    finally:
        await crawler.close()
        client.close()

# Example usage
# asyncio.run(crawl_and_store(["https://example.com"], "example_source", "mongodb://localhost:27017", "test_db", "test_collection", "Example Institution"))
