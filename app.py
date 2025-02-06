from flask import Flask, jsonify, request
import asyncio
from script import run_process  # Importing the async function

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Server is up and running!"})

@app.route('/process', methods=["POST"])
def process():
    try:
        data = request.get_json()
        url = data.get('url')
        source = data.get('source')
        databaseConnectionStr = data.get('databaseConnectionStr')
        institutionName = data.get('institutionName')

        dbName = "Demonstrations"
        collectionName = "Data"

        # Running the async function in the background using create_task()
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.run_until_complete(run_process(url, source, databaseConnectionStr, dbName, collectionName, institutionName))

        return jsonify({"message": "Process completed!", "result": "done"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3001)
