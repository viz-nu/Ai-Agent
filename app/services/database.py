from pymongo import MongoClient
import os

def get_mongo_client():
    return MongoClient(os.getenv("MONGO_URI"))

def save_to_mongodb(data):
    client = get_mongo_client()
    db = client["crawler_db"]
    collection = db["pages"]
    collection.insert_one(data)
    client.close()
