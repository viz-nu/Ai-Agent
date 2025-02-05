from flask import Flask, jsonify
import asyncio
import sys
import subprocess
from script import process_url  # Import the function you want to run from script.py

app = Flask(__name__)

# Route to check if the server is up and running
@app.route('/')
def home():
    return jsonify({"message": "Server is up and running!"})

# Route to process script.py when /process is hit
@app.route('/process')
def process():
    try:
        # Define the arguments to pass to the script (Replace with actual values as needed)
        url = "http://example.com"
        source = "source_example"
        databaseConnectionStr = "mongodb://localhost:27017"
        dbName = "example_db"
        collectionName = "example_collection"
        institutionName = "example_institution"
        
        # Running the script's main function asynchronously
        result = asyncio.run(run_process(url, source, databaseConnectionStr, dbName, collectionName, institutionName))
        
        return jsonify({"message": "Process completed!", "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def run_process(url, source, databaseConnectionStr, dbName, collectionName, institutionName):
    # You can call your script's main function here
    result = await process_url(url, source, databaseConnectionStr, dbName, collectionName, institutionName)
    return result

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3001)
