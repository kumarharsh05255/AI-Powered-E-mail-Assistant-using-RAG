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
    scopes = os.getenv("GOOGLE_OAUTH_SCOPES", "").split(",")

    credentials = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri=os.getenv("TOKEN_URI"),
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
        return base64.urlsafe_b64decode(
            data
        ).decode(
            "utf-8",
            errors="ignore",
        )

    except Exception:
        return ""


def html_to_text(content):
    # Remove content that is not useful as readable email text
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

    # Preserve useful line boundaries before removing HTML tags
    content = re.sub(
        r"<br\s*/?>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"</p>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"</div>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"</li>",
        "\n",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"<[^>]+>",
        "",
        content,
    )

    return html.unescape(content)


def remove_duplicate_paragraphs(body):
    paragraphs = re.split(
        r"\n\s*\n",
        body,
    )

    cleaned_paragraphs = []
    seen = set()

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Normalize whitespace only for duplicate comparison
        normalized = re.sub(
            r"\s+",
            " ",
            paragraph,
        ).strip().lower()

        if normalized not in seen:
            cleaned_paragraphs.append(
                paragraph
            )

            seen.add(
                normalized
            )

    return "\n\n".join(
        cleaned_paragraphs
    )


def clean_email_body(body):
    if not body:
        return ""

    body = html.unescape(
        body
    )

    # Remove HTML/Outlook comments left inside plain-text emails
    body = re.sub(
        r"<!--.*?-->",
        "",
        body,
        flags=re.DOTALL,
    )

    body = re.sub(
        r"<!\[if.*?\]>",
        "",
        body,
        flags=re.DOTALL | re.IGNORECASE,
    )

    body = re.sub(
        r"<!\[endif\]>",
        "",
        body,
        flags=re.IGNORECASE,
    )

    # Remove image placeholders such as [image: Google]
    body = re.sub(
        r"\[image:[^\]]*\]",
        "",
        body,
        flags=re.IGNORECASE,
    )

    # Remove Markdown-style images
    body = re.sub(
        r"!\[[^\]]*\]\([^)]+\)",
        "",
        body,
    )

    # Remove Markdown links but preserve their readable label
    body = re.sub(
        r"\[([^\]]+)\]\(https?://[^\s)]+\)",
        r"\1",
        body,
    )

    # Remove raw URLs. They add large amounts of tracking noise.
    body = re.sub(
        r"https?://\S+",
        "",
        body,
        flags=re.IGNORECASE,
    )

    # Remove empty brackets left after URL cleanup
    body = re.sub(
        r"\(\s*\)",
        "",
        body,
    )

    body = re.sub(
        r"\[\s*\]",
        "",
        body,
    )

    # Normalize spaces and blank lines
    body = re.sub(
        r"[ \t]+",
        " ",
        body,
    )

    body = re.sub(
        r" *\n *",
        "\n",
        body,
    )

    body = re.sub(
        r"\n{3,}",
        "\n\n",
        body,
    )

    body = body.strip()

    # Marketing emails sometimes repeat the same paragraph
    body = remove_duplicate_paragraphs(
        body
    )

    return body.strip()


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

    # Recursively inspect nested MIME sections
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

    # Prefer Gmail's plain-text representation
    if plain_parts:
        body = "\n".join(
            plain_parts
        )

        return clean_email_body(
            body
        )

    # Fall back to HTML when plain text is unavailable
    if html_parts:
        body = "\n".join(
            html_parts
        )

        body = html_to_text(
            body
        )

        return clean_email_body(
            body
        )

    return ""


def parse_email(email_data):
    headers = email_data["payload"].get(
        "headers",
        [],
    )

    # Convert Gmail's header list into an easier dictionary
    header_values = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    return {
        "id": email_data["id"],
        "thread_id": email_data["threadId"],
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
        "body": get_email_body(
            email_data["payload"]
        ),
    }


def fetch_emails(limit=10):
    service = get_gmail_service()

    # Gmail first returns IDs, then each full message is fetched
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
        email_data = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full",
        ).execute()

        emails.append(
            parse_email(
                email_data
            )
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

    return parse_email(
        email_data
    )


def send_reply(email_id, reply_text):
    service = get_gmail_service()

    # Fetch the original email so the reply stays in its Gmail thread
    original_email = service.users().messages().get(
        userId="me",
        id=email_id,
        format="full",
    ).execute()

    headers = original_email[
        "payload"
    ].get(
        "headers",
        [],
    )

    header_values = {
        header["name"].lower(): header["value"]
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

    # These headers help Gmail keep the reply in the same conversation
    if message_id:
        message["In-Reply-To"] = (
            message_id
        )

        message["References"] = (
            message_id
        )

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