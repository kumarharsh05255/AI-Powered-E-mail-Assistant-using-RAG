import os
import re
import html
import base64
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


load_dotenv()


def get_gmail_service():
    # Scopes are stored comma-separated in .env
    scopes = os.getenv(
        "GOOGLE_OAUTH_SCOPES",
        "",
    ).split(",")

    credentials = Credentials(
        token=None,
        refresh_token=os.getenv(
            "GOOGLE_REFRESH_TOKEN"
        ),
        client_id=os.getenv(
            "GOOGLE_CLIENT_ID"
        ),
        client_secret=os.getenv(
            "GOOGLE_CLIENT_SECRET"
        ),
        token_uri=os.getenv(
            "TOKEN_URI"
        ),
        scopes=scopes,
    )

    return build(
        "gmail",
        "v1",
        credentials=credentials,
    )


def decode_body(data):
    # Gmail body data is URL-safe base64 encoded
    if not data:
        return ""

    try:
        padding = "=" * (
            -len(data) % 4
        )

        return base64.urlsafe_b64decode(
            data + padding
        ).decode(
            "utf-8",
            errors="ignore",
        )

    except Exception:
        return ""


def html_to_text(content):
    # Convert HTML into simple text for AI processing
    content = re.sub(
        r"<script.*?>.*?</script>",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    content = re.sub(
        r"<style.*?>.*?</style>",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    content = re.sub(
        r"<!--.*?-->",
        "",
        content,
        flags=re.DOTALL,
    )

    # Add line breaks before removing HTML tags
    content = re.sub(
        r"<br\s*/?>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"</(p|div|li|tr|h[1-6])>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"<[^>]+>",
        "",
        content,
    )

    content = html.unescape(
        content
    )

    # Basic cleanup for the AI-readable version
    content = re.sub(
        r"[ \t]+",
        " ",
        content,
    )

    content = re.sub(
        r" *\n *",
        "\n",
        content,
    )

    content = re.sub(
        r"\n{3,}",
        "\n\n",
        content,
    )

    return content.strip()


def find_body_parts(payload):
    plain_parts = []
    html_parts = []

    mime_type = payload.get(
        "mimeType",
        "",
    )

    body_data = payload.get(
        "body",
        {},
    ).get(
        "data"
    )

    if body_data:
        decoded = decode_body(
            body_data
        )

        if mime_type == "text/plain":
            plain_parts.append(
                decoded
            )

        elif mime_type == "text/html":
            html_parts.append(
                decoded
            )

    # Gmail messages can contain nested MIME sections
    for part in payload.get(
        "parts",
        [],
    ):
        child_plain, child_html = (
            find_body_parts(part)
        )

        plain_parts.extend(
            child_plain
        )

        html_parts.extend(
            child_html
        )

    return plain_parts, html_parts


def get_email_body(payload):
    plain_parts, html_parts = (
        find_body_parts(payload)
    )

    # Plain text is preferred for LLMs and embeddings
    if plain_parts:
        return "\n".join(
            plain_parts
        ).strip()

    # Convert HTML when the email has no plain-text version
    if html_parts:
        return html_to_text(
            "\n".join(
                html_parts
            )
        )

    return ""


def get_email_html(payload):
    _, html_parts = find_body_parts(
        payload
    )

    if html_parts:
        return "\n".join(
            html_parts
        ).strip()

    return ""


def parse_email(email_data):
    headers = email_data[
        "payload"
    ].get(
        "headers",
        [],
    )

    # Convert Gmail's header list into a dictionary
    header_values = {
        header["name"].lower():
            header["value"]
        for header in headers
    }

    payload = email_data[
        "payload"
    ]

    return {
        "id": email_data["id"],
        "thread_id": email_data[
            "threadId"
        ],
        "sender": header_values.get(
            "from",
            "",
        ),
        "subject": header_values.get(
            "subject",
            "No Subject",
        ),
        "date": header_values.get(
            "date",
            "",
        ),
        "labels": email_data.get(
            "labelIds",
            [],
        ),

        # Used by analysis, embeddings, search, and RAG
        "body": get_email_body(
            payload
        ),

        # Used only for the visual email preview
        "html_body": get_email_html(
            payload
        ),
    }


def fetch_emails(limit=10):
    service = get_gmail_service()

    # Gmail first returns IDs, then each full email is fetched
    result = service.users().messages().list(
        userId="me",
        maxResults=limit,
    ).execute()

    messages = result.get(
        "messages",
        [],
    )

    emails = []

    for message in messages:
        email_data = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="full",
            )
            .execute()
        )

        emails.append(
            parse_email(
                email_data
            )
        )

    return emails


def get_email(email_id):
    # Fetch one specific email using its Gmail message ID
    service = get_gmail_service()

    email_data = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=email_id,
            format="full",
        )
        .execute()
    )

    return parse_email(
        email_data
    )


def send_reply(
    email_id,
    reply_text,
):
    service = get_gmail_service()

    # Fetch original email so the reply stays in its Gmail thread
    original_email = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=email_id,
            format="full",
        )
        .execute()
    )

    headers = original_email[
        "payload"
    ].get(
        "headers",
        [],
    )

    header_values = {
        header["name"].lower():
            header["value"]
        for header in headers
    }

    sender = header_values.get(
        "from",
        "",
    )

    subject = header_values.get(
        "subject",
        "",
    )

    message_id = header_values.get(
        "message-id",
        "",
    )

    if not subject.lower().startswith(
        "re:"
    ):
        subject = f"Re: {subject}"

    # Build the user-approved reply
    message = MIMEText(
        reply_text
    )

    message["To"] = sender
    message["Subject"] = subject

    # Help Gmail keep the reply in the original thread
    if message_id:
        message[
            "In-Reply-To"
        ] = message_id

        message[
            "References"
        ] = message_id

    raw_message = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode(
            "utf-8"
        )
    )

    sent_message = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw_message,
                "threadId":
                    original_email[
                        "threadId"
                    ],
            },
        )
        .execute()
    )

    return {
        "message_id":
            sent_message["id"],
        "thread_id":
            sent_message["threadId"],
        "status": "sent",
    }