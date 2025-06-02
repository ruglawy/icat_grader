import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from datetime import datetime
from sentence_transformers import CrossEncoder


class DocumentRetriever:
    def __init__(self, collection_name="all_projects", db_path="../chroma_db",
                 embedding_model_path="D:/bge-m3/bge-m3"):
        """
        Initialize the DocumentRetriever with the specified collection name and embedding model.

        Args:
            collection_name (str): Name of the ChromaDB collection to use
            db_path (str): Path to the ChromaDB database
            embedding_model_path (str): Path to the embedding model
        """
        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection_name = collection_name

        # Initialize the embedding model
        self.embed_model = HuggingFaceEmbedding(embedding_model_path)

    def set_collection(self, collection_name):
        """
        Set the collection name to use for document retrieval.

        Args:
            collection_name (str): Name of the ChromaDB collection to use

        Returns:
            bool: True if the collection exists, False otherwise
        """
        self.collection_name = collection_name
        return self.collection_exists()

    def collection_exists(self):
        """
        Check if the specified collection exists in ChromaDB.

        Returns:
            bool: True if the collection exists, False otherwise
        """
        try:
            # list_collections() returns Collection objects, extract names
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            return self.collection_name in collection_names
        except Exception as e:
            print(f"Error checking collection existence: {e}")
            return False

    def get_all_collections(self):
        """
        Retrieve all collections available in the ChromaDB.

        Returns:
            list: A list of collection names in the database
        """
        try:
            # Extract names from Collection objects
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            print(f"Error retrieving collections: {e}")
            return []


    def retrieve_documents(self, query, top_k=5):
        """
        Retrieve the top_k most relevant documents from ChromaDB based on the query.

        Args:
            query (str): The query string.
            top_k (int): The number of documents to retrieve.

        Returns:
            list or str: A list of dictionaries containing the retrieved documents and their metadata,
                        or a string message if the collection doesn't exist.
        """
        # Check if collection exists
        if not self.collection_exists():
            return f"Collection '{self.collection_name}' does not exist in the database."

        try:
            # Get the collection
            chroma_collection = self.chroma_client.get_collection(name=self.collection_name)

            print(f"Querying ChromaDB collection '{self.collection_name}' for: '{query}'...")

            # Start the timer
            start_time = datetime.now()

            # Generate embedding for the query
            query_embedding = self.embed_model.get_query_embedding(query)

            # Perform similarity search in ChromaDB
            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "distances"]
            )

            # Calculate and print the time taken for retrieval
            end_time = datetime.now()
            retrieval_time = end_time - start_time
            retrieval_minutes, retrieval_seconds = divmod(retrieval_time.total_seconds(), 60)
            print(f"Retrieval time: {int(retrieval_minutes)} minutes and {retrieval_seconds:.2f} seconds.")

            # Process the results
            retrieved_docs = []
            for i in range(len(results["ids"][0])):
                retrieved_docs.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "distance": results["distances"][0][i]
                })

            print(f"Retrieved {len(retrieved_docs)} documents.")
            return retrieved_docs

        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return f"Error retrieving documents: {str(e)}"

