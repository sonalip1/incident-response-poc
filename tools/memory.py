import os
import json
import chromadb

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
COLLECTION_NAME = "incident_memory"

def init_memory():
    """Initializes and returns the persistent ChromaDB collection."""
    client = chromadb.PersistentClient(path=DB_PATH)
    # Get or create the collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def seed_memory():
    """Loads seed_incidents.json into the collection."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_file = os.path.join(base_dir, "data", "seed_incidents.json")
    
    if not os.path.exists(seed_file):
        raise FileNotFoundError(f"Seed file not found at: {seed_file}")
        
    with open(seed_file, "r") as f:
        incidents = json.load(f)
        
    collection = init_memory()
    
    # Check if already seeded to prevent duplication
    existing = collection.get()
    if existing and existing.get("ids"):
        print("ChromaDB already seeded.")
        return
        
    ids = []
    documents = []
    metadatas = []
    
    for inc in incidents:
        ids.append(inc["id"])
        documents.append(inc["text"])
        metadatas.append({"category": inc["category"]})
        
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print(f"Seeded {len(incidents)} incidents into ChromaDB.")

def get_similar_incidents(log_text: str, category: str = None, n: int = 2) -> list[str]:
    """Queries ChromaDB for semantically similar incidents, optionally filtering by category."""
    collection = init_memory()
    
    # Check if there are any documents in the DB
    existing = collection.get()
    if not existing or not existing.get("ids"):
        return []
        
    where = None
    if category:
        where = {"category": category}
        
    results = collection.query(
        query_texts=[log_text],
        n_results=n,
        where=where
    )
    
    # Return list of matching documents
    if results and results.get("documents"):
        return results["documents"][0]
    return []

def save_resolution(log_text: str, resolution: dict):
    """Saves a resolved incident text and metadata back to ChromaDB."""
    collection = init_memory()
    
    # Generate unique ID
    existing = collection.get()
    count = len(existing.get("ids", [])) if existing else 0
    new_id = f"inc_resolved_{count + 1}"
    
    # Construct memory text
    category = resolution.get("category", "unknown")
    steps = ", ".join(resolution.get("suggested_fix", []))
    resolved_text = f"Incident: {log_text}. Cause: {resolution.get('root_cause', 'Unknown')}. Fix: {steps}."
    
    collection.add(
        ids=[new_id],
        documents=[resolved_text],
        metadatas=[{"category": category}]
    )
    print(f"Saved new resolution {new_id} to ChromaDB memory.")
