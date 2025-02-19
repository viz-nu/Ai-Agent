from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import os
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

    results = asyncio.run(crawl_and_store(
        urls, source, databaseConnectionStr, dbName, collectionName, institutionName))

    return jsonify({"results": results})


@main.route('/convert_pdf', methods=['POST'])
def convert_pdf():
    # if 'file' not in request.files:
    #     return jsonify({"error": "No file provided"}), 400

    # file = request.files['file']

    # if file.filename == '':
    #     return jsonify({"error": "No selected file"}), 400

    # file_path = f"temp_{file.filename}"

    # file.save(file_path)

    try:
        loader = PyPDFLoader("https://css4.pub/2017/newsletter/drylab.pdf")
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, chunk_overlap=200, length_function=len, separators=["\n\n", "\n", " ", "."])
        chunks = text_splitter.split_documents(docs)
        print(chunks[0])
        serializable_chunks = [
            {"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks]
        return jsonify({"doc": serializable_chunks})
    except Exception as e:
        # os.remove(file_path)  # Clean up temp file in case of error
        return jsonify({"error": str(e)}), 500

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.docstore.document import Document
os.environ["OPENAI_API_KEY"] = ""

def get_semantic_chunks(transcript):
    """
    Convert transcript text into semantic chunks using embeddings + FAISS.
    """
    # 1. Convert transcript into a list of sentences
    sentences = [entry["text"] for entry in transcript]
    
    # 2. Embed each sentence
    embeddings = OpenAIEmbeddings()
    docs = [Document(page_content=sentence) for sentence in sentences]
    
    # 3. Store embeddings in FAISS (Vector DB)
    vector_db = FAISS.from_documents(docs, embeddings)

    # 4. Retrieve semantically related chunks
    results = []
    for doc in docs:
        similar_docs = vector_db.similarity_search(doc.page_content, k=3)  # Find top 3 similar sentences
        chunk = " ".join([d.page_content for d in similar_docs])
        results.append(chunk)

    return list(set(results))  # Remove duplicates


@main.route('/yt-transcripts', methods=["GET"])
def get_yt_transcripts():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatted_transcript = get_semantic_chunks(transcript)
        return jsonify({"video_id": video_id, "transcript": formatted_transcript})
    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled for this video"}), 403
    except VideoUnavailable:
        return jsonify({"error": "Video is unavailable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
