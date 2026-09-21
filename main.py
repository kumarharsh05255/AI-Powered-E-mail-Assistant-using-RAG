from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from gmail_client import (
    fetch_emails,
    get_email,
    send_reply,
)
from vector_store import (
    email_exists,
    store_email,
    search_emails,
    get_stored_emails,
)
from email_analyzer import analyze_email
from rag import generate_reply_stream


app = FastAPI(
    title="AI Powered Email Assistant"
)


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
    """
    Fetch recent Gmail emails, analyze and store only new ones,
    then return the inbox with stored/skipped counts.
    """
    try:
        recent_emails = fetch_emails(limit)
        stored_emails = get_stored_emails()

        stored_by_id = {
            email["id"]: email
            for email in stored_emails
        }

        result = []
        stored = 0
        skipped = 0

        for email in recent_emails:
            if email_exists(email["id"]):
                skipped += 1

                stored_email = stored_by_id.get(
                    email["id"]
                )

                if stored_email:
                    email["analysis"] = stored_email.get(
                        "analysis"
                    )

                result.append(email)
                continue

            analysis = analyze_email(email)

            was_stored = store_email(
                email,
                analysis,
            )

            if was_stored:
                stored += 1
            else:
                skipped += 1

            email["analysis"] = analysis
            result.append(email)

        return {
            "emails": result,
            "stored": stored,
            "skipped": skipped,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/search-emails")
def search_email_endpoint(
    query: str,
    top_k: int = 5,
):
    try:
        return search_emails(
            query=query,
            top_k=top_k,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/generate-reply/{email_id}")
def generate_reply_endpoint(email_id: str):
    try:
        email = get_email(email_id)

        return StreamingResponse(
            generate_reply_stream(email),
            media_type="text/plain",
        )

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
