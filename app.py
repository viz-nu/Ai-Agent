from flask import Flask, jsonify, request
import asyncio
from script import run_process  # Importing the async function

app = Flask(__name__)
# Global Playwright and Browser Context
playwright = None
browser = None

async def init_playwright():
    global playwright, browser
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch_persistent_context(
        user_data_dir="/tmp/playwright",  # Store session data
        headless=True,  # Run in headless mode for lower memory usage
        args=["--no-sandbox"]  # Required for running Playwright in some environments
    )

@app.before_first_request
def start_playwright():
    """ Initialize Playwright when the Flask app starts """
    asyncio.run(init_playwright())
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
        thread = threading.Thread(target=run_async_task, args=(url, source, databaseConnectionStr, dbName, collectionName, institutionName))
        thread.start()
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.run_until_complete(run_process(url, source, databaseConnectionStr, dbName, collectionName, institutionName))

        return jsonify({"message": "Process completed!", "result": "done"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.teardown_appcontext
def shutdown_playwright(exception=None):
    """ Shut down Playwright when the app exits """
    global playwright, browser
    if browser:
        asyncio.run(browser.close())
    if playwright:
        asyncio.run(playwright.stop())


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3001)
