import os

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


# Load the embedding model once when the backend starts
embedding_model = SentenceTransformer(
    os.getenv("EMBEDDING_MODEL_NAME")
)


# PersistentClient keeps ChromaDB data on disk
chroma_client = chromadb.PersistentClient(
   path = "chroma_db"
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
    # Do not embed/store an email that is already synced
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

    # Store the email together with its AI-generated analysis
    collection.add(
        ids=[email["id"]],
        embeddings=[embedding],
        documents=[email_text],
        metadatas=[
            {
                "sender": email["sender"],
                "subject": email["subject"],
                "thread_id": email["thread_id"],
                "date": email["date"],
                "urgency": analysis["urgency"],
                "intent": analysis["intent"],
                "topic": analysis["topic"],
                "sentiment": analysis["sentiment"],
                "summary": analysis["summary"],
                "profanity": analysis["profanity"],
                "unsafe_content": analysis["unsafe_content"],
            }
        ],
    )

    return True


def get_stored_emails():
    # Retrieve synced emails and their saved AI analysis
    results = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    emails = []

    for email_id, document, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
    ):
        emails.append(
            {
                "id": email_id,
                "thread_id": metadata.get(
                    "thread_id",
                    "",
                ),
                "sender": metadata.get(
                    "sender",
                    "",
                ),
                "subject": metadata.get(
                    "subject",
                    "",
                ),
                "date": metadata.get(
                    "date",
                    "",
                ),
                "body": document,
                "analysis": {
                    "summary": metadata.get(
                        "summary",
                        "",
                    ),
                    "urgency": metadata.get(
                        "urgency",
                        "",
                    ),
                    "intent": metadata.get(
                        "intent",
                        "",
                    ),
                    "topic": metadata.get(
                        "topic",
                        "",
                    ),
                    "sentiment": metadata.get(
                        "sentiment",
                        "",
                    ),
                    "profanity": metadata.get(
                        "profanity",
                        False,
                    ),
                    "unsafe_content": metadata.get(
                        "unsafe_content",
                        False,
                    ),
                },
            }
        )

    return emails


def search_emails(query, top_k=5):
    # Convert the search query into an embedding for semantic search
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