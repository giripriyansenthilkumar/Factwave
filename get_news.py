import requests
import pymongo
from datetime import datetime, timedelta
import time
import json

script_start = time.time()

# MongoDB Connection
client = pymongo.MongoClient("mongodb+srv://ml_dept_project:ml_dept_project@ml-project.gkigx.mongodb.net/")
db = client["factwave"]
collection = db["verified_facts"]

# Get all stored headlines for fast lookup
stored_news = set(
    doc.get("headline", "").strip().lower()
    for doc in collection.find({}, {"headline": 1, "_id": 0})
)
print(f"Stored news in database: {len(stored_news)} items")  # Debugging: Log the number of stored headlines

API_KEY = "eff5ecc6ce7243179f9698ddda51f05e"

# List of sources to fetch headlines for
sources = ["bbc-news", "cnn", "the-verge", "bloomberg", "associated-press"]  # Example sources

# Interval in seconds to fetch live news
FETCH_INTERVAL = 300  # Fetch news every 5 minutes

while True:
    print("Fetching live news...")
    for source in sources:
        print(f"Fetching headlines for source: {source}")
        BASE_URL = f"https://newsapi.org/v2/top-headlines?sources={source}&apiKey={API_KEY}"

        api_start = time.time()
        response = requests.get(BASE_URL)
        news_data = response.json()
        print(f"API response for {source}: {json.dumps(news_data, indent=2)}")  # Debugging: Log the full API response
        api_end = time.time()
        print(f"API response time for {source}: {api_end - api_start:.2f} seconds")

        process_start = time.time()
        if news_data["status"] != "ok":
            print(f"Error fetching news for {source}: {news_data.get('message', 'Unknown error')}")
            continue

        news_items = []
        for article in news_data["articles"]:
            headline = article.get("title", "").strip().lower()  # Normalize headline
            source_name = article.get("source", {}).get("name", "unknown").strip().lower()  # Get source name
            if not headline:
                print(f"Invalid article in {source}: {article}")  # Debugging: Log invalid articles
                continue

            # Check if this headline already exists
            if headline in stored_news:
                print(f"Duplicate found: {headline} in source {source}")  # Debugging: Log duplicates
            else:
                news_items.append({
                    "source": source_name,
                    "headline": headline,
                    "timestamp": datetime.utcnow()
                })

        if news_items:
            print(f"News items to insert for {source}: {news_items}")  # Debugging: Log items to be inserted
            insert_start = time.time()
            collection.insert_many(news_items)  # Bulk Insert
            insert_end = time.time()
            print(f"Inserted {len(news_items)} news items for {source} in {insert_end - insert_start:.2f} seconds")
        else:
            print(f"No new headlines to insert for {source}.")

        process_end = time.time()
        print(f"Processing time for {source}: {process_end - process_start:.2f} seconds")

    print(f"Waiting for {FETCH_INTERVAL} seconds before fetching news again...")
    time.sleep(FETCH_INTERVAL)
