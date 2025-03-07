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

    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(crawl_and_store(urls))  # Use run_until_complete instead of run

    return jsonify({"results": results})
