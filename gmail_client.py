import os
import base64
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


load_dotenv()


def get_gmail_service():
    # Scopes are stored comma-separated in .env
    scopes = os.getenv("GOOGLE_OAUTH_SCOPES", "").split(",")

    credentials = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri=os.getenv("TOKEN_URI"),
        scopes=scopes,
    )

    # Creates the Gmail API client used by the other functions
    return build(
        "gmail",
        "v1",
        credentials=credentials,
    )


def get_email_body(payload):
    # Some emails store the body directly in the main payload
    body_data = payload.get("body", {}).get("data")

    if body_data:
        return base64.urlsafe_b64decode(
            body_data
        ).decode(
            "utf-8",
            errors="ignore",
        )

    # Multipart emails may contain the text body inside nested parts
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")

            if data:
                return base64.urlsafe_b64decode(
                    data
                ).decode(
                    "utf-8",
                    errors="ignore",
                )

        # Recursively search nested multipart sections
        nested_body = get_email_body(part)

        if nested_body:
            return nested_body

    return ""


def parse_email(email_data):
    headers = email_data["payload"].get("headers", [])

    # Convert Gmail's header list into an easier dictionary
    header_values = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    return {
        "id": email_data["id"],
        "thread_id": email_data["threadId"],
        "sender": header_values.get("from", ""),
        "subject": header_values.get("subject", "No Subject"),
        "date": header_values.get("date", ""),
        "labels": email_data.get("labelIds", []),
        "body": get_email_body(email_data["payload"]),
    }


def fetch_emails(limit=10):
    service = get_gmail_service()

    # Gmail first returns message IDs, then we fetch each full message
    result = service.users().messages().list(
        userId="me",
        maxResults=limit,
    ).execute()

    messages = result.get("messages", [])
    emails = []

    for message in messages:
        email_data = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full",
        ).execute()

        emails.append(
            parse_email(email_data)
        )

    return emails


def get_email(email_id):
    # Fetch one specific email using its Gmail message ID
    service = get_gmail_service()

    email_data = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full",
    ).execute()

    return parse_email(email_data)


def send_reply(email_id, reply_text):
    service = get_gmail_service()

    # Fetch the original email so the reply stays in the same Gmail thread
    original_email = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full",
    ).execute()

    headers = original_email["payload"].get(
        "headers",
        [],
    )

    header_values = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    sender = header_values.get("from", "")
    subject = header_values.get("subject", "")
    message_id = header_values.get("message-id", "")

    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    # Build a standard email message containing the user-approved reply
    message = MIMEText(reply_text)

    message["To"] = sender
    message["Subject"] = subject

    # These headers help Gmail recognize this as a reply
    if message_id:
        message["In-Reply-To"] = message_id
        message["References"] = message_id

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    sent_message = service.users().messages().send(
        userId="me",
        body={
            "raw": raw_message,
            "threadId": original_email["threadId"],
        },
    ).execute()

    return {
        "message_id": sent_message["id"],
        "thread_id": sent_message["threadId"],
        "status": "sent",
    }