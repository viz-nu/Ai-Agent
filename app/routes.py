import os
from flask import Blueprint, request, jsonify
from app.services.processing import crawl_and_store
import asyncio
main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def test():
    try:
        
        return jsonify({"test":"server up and running"})
    except Exception as e:
        # os.remove(file_path)  # Clean up temp file in case of error
        return jsonify({"error": str(e)}), 500

@main.route("/crawl-urls", methods=["POST"])
def crawl_urls():
    data = request.json
    urls = data.get("urls")
    if not urls or not isinstance(urls, list):
        return jsonify({"error": "Invalid URLs list"}), 400

    results = asyncio.run(crawl_and_store(urls))

    return jsonify({"results": results})
