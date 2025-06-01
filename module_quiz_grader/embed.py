import pandas as pd
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.schema import Document
from datetime import datetime
import numpy as np
import os
import glob


def calc_and_print_time(start_time, name):
    """Calculate and print the time taken for a process."""
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time.total_seconds(), 60)
    print(f"{name} time: {int(minutes)} minutes and {seconds:.2f} seconds.")


# Initialize Chroma client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Initialize the embedding model
print("Initializing embedding model...")
embed_model = HuggingFaceEmbedding(r"D:\bge-m3\bge-m3")

# Path to the all chunks processed file
all_chunks_file = 'chunks_processed/all_chunks_processed.csv'

# Load the all chunks processed CSV file
print(f"Loading data from {all_chunks_file}...")
all_data = pd.read_csv(all_chunks_file)
print(f"Loaded {len(all_data)} documents from {all_chunks_file}")

# Generate embeddings for all chunks at once
print("Generating embeddings for all documents...")
start_embedding = datetime.now()

# Extract text from the data
texts = all_data['text'].tolist()
ids = all_data['id'].astype(str).tolist()

# Generate embeddings for all texts at once
embeddings = embed_model._get_text_embeddings(texts)

calc_and_print_time(start_embedding, "Embedding generation")
print(f"Generated embeddings for {len(embeddings)} documents")

# Create a dictionary mapping IDs to their embeddings and texts for quick lookup
print("Creating lookup tables for efficient collection creation...")
id_to_embedding = {id_val: embedding for id_val, embedding in zip(ids, embeddings)}
id_to_text = {id_val: text for id_val, text in zip(ids, texts)}

# --- drop & recreate 'all_projects' every run ------------
try:
    chroma_client.delete_collection("all_projects")
except Exception as e:
    print(f"Warning: Could not delete 'all_projects' collection. Reason: {e}")

# First, create and populate the "all_projects" collection
print("\nCreating 'all_projects' collection...")
all_projects_collection = chroma_client.get_or_create_collection("all_projects")

# Add documents in batches to avoid memory issues
batch_size = 1000
for i in range(0, len(ids), batch_size):
    batch_ids = ids[i:i + batch_size]
    batch_texts = [id_to_text[id_val] for id_val in batch_ids]
    batch_embeddings = [id_to_embedding[id_val] for id_val in batch_ids]

    all_projects_collection.add(
        documents=batch_texts,
        ids=batch_ids,
        embeddings=batch_embeddings,
        metadatas=[{"module": id_val.split("_")[0]} for id_val in batch_ids]
    )
    print(f"Added batch {i // batch_size + 1}/{(len(ids) - 1) // batch_size + 1} to all_projects collection")

# Now create collections for each project
project_files = glob.glob('chunks_processed/*_chunks.csv')
print(f"\nFound {len(project_files)} project files to create collections for")

for project_file in project_files:
    # Extract the project name from the filename
    project_name = os.path.basename(project_file).replace('_chunks.csv', '')
    print(f"\nProcessing project: {project_name}")

    # # --- (re)create collection fresh ---
    # coll_name = f"project_{project_name}"
    # chroma_client.delete_collection(coll_name)  # ignore if not present
    # project_collection = chroma_client.create_collection(coll_name)

    # Load the project's CSV file
    project_data = pd.read_csv(project_file)
    project_ids = project_data['id'].astype(str).tolist()
    print(f"Loaded {len(project_data)} documents for project {project_name}")

    # Create a collection for the project
    # Delete the collection if it exists
    collection_name = f"project_{project_name}"
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass  # Collection doesn't exist, that's fine

    # Create a fresh collection
    project_collection = chroma_client.create_collection(collection_name)

    # Use the embeddings we already generated to populate the project collection
    project_texts = []
    project_embeddings = []
    valid_ids = []

    for proj_id in project_ids:
        if proj_id in id_to_embedding:
            valid_ids.append(proj_id)
            project_texts.append(id_to_text[proj_id])
            project_embeddings.append(id_to_embedding[proj_id])
        else:
            print(f"Warning: ID {proj_id} not found in all_chunks_processed data")

    # Add documents in batches
    for i in range(0, len(valid_ids), batch_size):
        batch_ids = valid_ids[i:i + batch_size]
        batch_texts = project_texts[i:i + batch_size]  # Slice from prepared list
        batch_embeddings = project_embeddings[i:i + batch_size]  # Slice from prepared list

        project_collection.add(
            documents=batch_texts,
            ids=batch_ids,
            embeddings=batch_embeddings
        )
        print(
            f"Added batch {i // batch_size + 1}/{(len(valid_ids) - 1) // batch_size + 1} to {project_name} collection")

    print(f"Created collection 'project_{project_name}' with {len(valid_ids)} documents")

print("\nAll collections created successfully!")