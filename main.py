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
    email_exists,
    store_email,
    search_emails,
    get_stored_emails,
)

from rag import generate_reply


app = FastAPI(
    title="AI Powered Email Assistant"
)


# Quick checks to confirm that the FastAPI backend is running
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
    # Fetch raw recent emails directly from Gmail
    try:
        return fetch_emails(limit)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/sync-emails")
def sync_emails(limit: int = 10):
    # Analyze new Gmail emails and store them in ChromaDB
    try:
        emails = fetch_emails(limit)

        stored = 0
        skipped = 0

        for email in emails:
            # Skip the LLM call when the email is already stored
        

            if email_exists(email["id"]):
                skipped += 1
                continue

            analysis = analyze_email(email)

            if store_email(email, analysis):
                stored += 1

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


@app.get("/inbox")
def get_analyzed_inbox():
    # Use saved analysis instead of calling the LLM again
    emails = get_stored_emails()

    urgency_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
    }

    emails.sort(
        key=lambda email: urgency_order.get(
            email["analysis"]["urgency"],
            3,
        )
    )

    return emails


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
    return search_emails(
        query=query,
        top_k=top_k,
    )


@app.get("/generate-reply/{email_id}")
def generate_reply_endpoint(email_id: str):
    try:
        email = get_email(email_id)

        reply = generate_reply(email)

        # Reply remains a draft until the user explicitly sends it
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