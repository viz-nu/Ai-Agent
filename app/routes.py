from flask import Blueprint, request, jsonify
from app.services.crawler import fetch_urls_from_sitemap, crawl_and_process_urls

main = Blueprint('main', __name__)

@main.route("/fetch-urls", methods=["POST"])
def fetch_urls():
    data = request.json
    sitemap_urls = data.get("sitemap_urls")
    if not sitemap_urls:
        return jsonify({"error": "Missing sitemap_urls"}), 400
    
    urls = fetch_urls_from_sitemap(sitemap_urls)
    return jsonify({"urls": urls})

@main.route("/crawl-urls", methods=["POST"])
def crawl_urls():
    data = request.json
    urls = data.get("urls")
    if not urls or not isinstance(urls, list):
        return jsonify({"error": "Invalid URLs list"}), 400
    
    results = crawl_and_process_urls(urls)
    return jsonify({"results": results})
