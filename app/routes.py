from flask import Blueprint, request, jsonify
from app.services.crawler import fetch_urls_from_sitemap
from app.services.processing import crawl_and_store
import asyncio
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
    dbName = data.get("dbName")
    collectionName = data.get("collectionName")
    source = data.get("source")
    databaseConnectionStr = data.get("databaseConnectionStr")
    institutionName = data.get("institutionName")
    if not urls or not isinstance(urls, list):
        return jsonify({"error": "Invalid URLs list"}), 400
    
    results = asyncio.run(crawl_and_store(urls, source, databaseConnectionStr, dbName, collectionName, institutionName))

    return jsonify({"results": results})
