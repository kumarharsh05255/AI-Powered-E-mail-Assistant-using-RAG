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


def generate_reply_stream(email):
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
        if distance < 1.5:
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

    # Stream the reply from Groq instead of waiting for the full response
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.3,
        stream=True,
    )

    # Send each generated piece as soon as it becomes available
    for chunk in stream:
        content = chunk.choices[0].delta.content

        if content:
            yield content