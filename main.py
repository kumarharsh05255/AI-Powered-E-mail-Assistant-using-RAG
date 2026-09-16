from fastapi import FastAPI, HTTPException

from gmail_client import (
    fetch_emails,
    get_email,
    send_reply,
)
from email_analyzer import (
    analyze_email,
    summarize_email,
    classify_email,
    analyze_sentiment,
)
from vector_store import (
    store_email,
    search_emails,
)
from rag import generate_reply


app = FastAPI(
    title="AI Powered Email Assistant"
)


# Basic endpoint to quickly check whether the backend is running
@app.get("/")
def home():
    return {
        "message": "AI Powered Email Assistant API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/emails")
def get_recent_emails(limit: int = 10):
    # Fetch recent emails directly from Gmail for the frontend inbox
    try:
        return fetch_emails(limit)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/sync-emails")
def sync_emails(limit: int = 10):
    # Analyze and store new emails in ChromaDB for semantic search and RAG
    try:
        emails = fetch_emails(limit)

        stored = 0
        skipped = 0

        for email in emails:
            analysis = analyze_email(email)

            if store_email(email, analysis):
                stored += 1
            else:
                skipped += 1

        return {
            "fetched": len(emails),
            "stored": stored,
            "skipped": skipped,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/analyze/{email_id}")
def analyze_email_endpoint(email_id: str):
    email = get_email(email_id)

    return analyze_email(email)


@app.get("/summary/{email_id}")
def summarize_email_endpoint(email_id: str):
    email = get_email(email_id)

    return {
        "summary": summarize_email(email)
    }


@app.get("/classification/{email_id}")
def classify_email_endpoint(email_id: str):
    email = get_email(email_id)

    return classify_email(email)


@app.get("/sentiment/{email_id}")
def sentiment_endpoint(email_id: str):
    email = get_email(email_id)

    return analyze_sentiment(email)


@app.get("/search-emails")
def search_email_endpoint(
    query: str,
    top_k: int = 5,
):
    # Semantic search only searches emails already synced into ChromaDB
    return search_emails(
        query=query,
        top_k=top_k,
    )


@app.get("/generate-reply/{email_id}")
def generate_reply_endpoint(email_id: str):
    try:
        email = get_email(email_id)

        reply = generate_reply(email)

        # Reply is only a draft; nothing is sent automatically
        return {
            "reply": reply,
            "status": "draft",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/send-reply/{email_id}")
def send_reply_endpoint(
    email_id: str,
    reply_text: str,
):
    # Email is sent only after the user explicitly approves the draft
    try:
        return send_reply(
            email_id,
            reply_text,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )