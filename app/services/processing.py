from app.services.embedding import get_embedding
from app.services.database import save_to_mongodb

def process_url(url):
    # Here, you should fetch and process the content from the URL.
    content = f"Fetched content from {url}"  # Placeholder
    embedding = get_embedding(content)
    result = {"url": url, "content": content, "embedding": embedding}
    save_to_mongodb(result)
    return result
