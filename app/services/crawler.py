import requests
from xml.etree import ElementTree

import time

def fetch_urls_from_sitemap(sitemap_urls):
    userAgents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
    ]
    def get_urls(url, retries=3):
        for attempt in range(retries):
            try:
                response = requests.get(url, headers={"User-Agent":userAgents[attempt]}, timeout=100)
                if response.status_code == 403:
                    print(f"Access forbidden (403) for {url} using agent {userAgents[attempt]}. Trying with different User-Agent.")
                    continue
                
                response.raise_for_status()
                root = ElementTree.fromstring(response.content)
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                urls = []
                for url_element in root.findall('.//ns:loc', namespace):
                    url_text = url_element.text.strip() if url_element.text else None
                    lastmod_element = url_element.find('../ns:lastmod', namespace)
                    lastmod = lastmod_element.text.strip() if lastmod_element is not None and lastmod_element.text else None
                    
                    if url_text:
                        urls.append((url_text, lastmod))
                
                return urls
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        print(f"Request failed after {retries} attempts: {url}")
        return []

    seen_urls = set()
    urls_to_process = sitemap_urls
    all_urls = []

    while urls_to_process:
        current_url = urls_to_process.pop()
        if current_url in seen_urls:
            continue
        seen_urls.add(current_url)

        fetched_urls = get_urls(current_url)
        for url, lastmod in fetched_urls:
            if url.endswith('.xml'):
                urls_to_process.append(url)
            elif url.startswith("http"):
                all_urls.append({"url": url, "lastmod": lastmod})
    
    return all_urls
