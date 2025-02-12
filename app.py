from flask import Flask, jsonify, request
import asyncio
import requests
from xml.etree import ElementTree
from script import crawl_parallel,process_url

app = Flask(__name__)


@app.route('/')
def home():
    return jsonify({"message": "Server is up and running!"})
@app.route('/get_sublinks', methods=["POST"])
def get_sublinks():
    """ API endpoint to fetch all sublinks from a given sitemap URL. """
    try:
        data = request.get_json()
        url = data.get('url')
        urls = asyncio.run(process_url(url))
        return jsonify({"message": "Process completed!", "data": urls})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=["POST"])
def process():
    try:
        data = request.get_json()
        urls = data.get('urls')
        source = data.get('source')
        databaseConnectionStr = data.get('databaseConnectionStr')
        institutionName = data.get('institutionName')
        max_concurrent = data.get('maxConcurrent') 
        dbName = data.get('dbName') or "Demonstrations"
        collectionName = data.get('collectionName') or "Data"
        result = asyncio.run(crawl_parallel(urls, source, max_concurrent,
                             databaseConnectionStr, dbName, collectionName, institutionName))
        return jsonify({"success": True, "message": "Process completed!", "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3001)
