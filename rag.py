import os

from dotenv import load_dotenv
from groq import Groq

from prompts import REPLY_PROMPT
from vector_store import search_emails


load_dotenv()


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

LLM_MODEL = os.getenv("LLM_MODEL_NAME")


def generate_reply(email):
    # Search ChromaDB for emails semantically similar to the current email
    results = search_emails(
        email["body"],
        top_k=3,
    )

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    relevant_emails = []

    # Smaller ChromaDB distance means the emails are more similar
    for document, distance in zip(documents, distances):
        if distance < 1.0:
            relevant_emails.append(document)

    if relevant_emails:
        context = "\n\n---\n\n".join(relevant_emails)
    else:
        context = "No relevant historical context found."

    email_text = f"""
From: {email["sender"]}
Subject: {email["subject"]}

{email["body"]}
"""

    prompt = REPLY_PROMPT.format(
        email=email_text,
        context=context,
    )

    # Generate the final reply using the current email + retrieved context
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content