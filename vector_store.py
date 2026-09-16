import os

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


# Load the embedding model once when the application starts
embedding_model = SentenceTransformer(
    os.getenv("EMBEDDING_MODEL_NAME")
)


# PersistentClient keeps the vector database on disk
chroma_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_PATH")
)


collection = chroma_client.get_or_create_collection(
    name="emails"
)


def email_exists(email_id):
    # Gmail message ID is used as the unique ChromaDB ID
    result = collection.get(
        ids=[email_id]
    )

    return len(result["ids"]) > 0


def store_email(email, analysis):
    # Avoid embedding and storing the same Gmail message again
    if email_exists(email["id"]):
        return False

    email_text = f"""
Subject: {email["subject"]}

Body:
{email["body"]}
"""

    embedding = embedding_model.encode(
        email_text
    ).tolist()

    # Store the email text, its embedding, and useful AI analysis as metadata
    collection.add(
        ids=[email["id"]],
        embeddings=[embedding],
        documents=[email_text],
        metadatas=[
            {
                "sender": email["sender"],
                "subject": email["subject"],
                "thread_id": email["thread_id"],
                "urgency": analysis["urgency"],
                "intent": analysis["intent"],
                "topic": analysis["topic"],
                "sentiment": analysis["sentiment"],
                "profanity": analysis["profanity"],
                "unsafe_content": analysis["unsafe_content"],
            }
        ],
    )

    return True


def search_emails(query, top_k=5):
    # Convert the user's natural-language search into the same vector space
    query_embedding = embedding_model.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    return results