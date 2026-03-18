import os
import time
from google.cloud import aiplatform
from vertexai.preview import rag
import vertexai
from google.cloud import storage

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.popen("gcloud config get-value project").read().strip()
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-west1"
CORPUS_DISPLAY_NAME = "ca-building-codes"
BUILDING_CODES_DIR = "../building-codes"
DATA_BUCKET = f"{PROJECT_ID}-building-permit-data"

def setup_rag():
    print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Create Corpus if it doesn't exist
    print(f"Checking for existing corpus: {CORPUS_DISPLAY_NAME}...")
    existing_corpora = getattr(rag, 'list_corpora', getattr(rag, 'list_rag_corpora', lambda: []))()
    corpus = None
    for c in existing_corpora:
        if c.display_name == CORPUS_DISPLAY_NAME:
            corpus = c
            print(f"Found existing corpus: {corpus.name}")
            break

    if not corpus:
        print(f"Creating RAG Corpus: {CORPUS_DISPLAY_NAME}...")
        create_func = getattr(rag, 'create_corpus', getattr(rag, 'create_rag_corpus', None))
        corpus = create_func(display_name=CORPUS_DISPLAY_NAME)
        print(f"Created corpus: {corpus.name}")

    # 2. Upload files to GCS and Import
    print(f"Uploading files from {BUILDING_CODES_DIR} to GCS bucket: {DATA_BUCKET}...")
    storage_client = storage.Client(project=PROJECT_ID)
    try:
        bucket = storage_client.bucket(DATA_BUCKET)
        if not bucket.exists():
             bucket = storage_client.create_bucket(DATA_BUCKET, location="us-central1")
    except Exception as e:
        print(f"Error accessing or creating bucket {DATA_BUCKET}: {e}")
        return

    files = [f for f in os.listdir(BUILDING_CODES_DIR) if f.endswith(".pdf")]
    
    for filename in files:
        file_path = os.path.join(BUILDING_CODES_DIR, filename)
        gcs_uri = f"gs://{DATA_BUCKET}/{filename}"
        
        print(f"Uploading {filename} to {gcs_uri}...")
        try:
            blob = bucket.blob(filename)
            blob.upload_from_filename(file_path)
            
            print(f"Importing {gcs_uri} into RAG corpus...")
            rag.import_files(
                corpus_name=corpus.name,
                paths=[gcs_uri],
                chunk_size=1024,
                chunk_overlap=200,
            )
            print(f"Successfully started import for {filename}")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")

    print("RAG setup script completed.")

if __name__ == "__main__":
    setup_rag()
