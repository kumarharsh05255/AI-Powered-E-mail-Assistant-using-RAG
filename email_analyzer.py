import os
import json

from dotenv import load_dotenv
from groq import Groq

from prompts import (
    SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    SUMMARY_PROMPT,
    CLASSIFICATION_PROMPT,
    SENTIMENT_PROMPT,
)


load_dotenv()


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

LLM_MODEL = os.getenv("LLM_MODEL_NAME")


def format_email(email):
    # Convert the email dictionary into clean text for the LLM
    return f"""
From: {email["sender"]}
Subject: {email["subject"]}

{email["body"]}
"""


def call_llm(prompt, temperature=0):
    # Common LLM call used by all email analysis functions
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content


def analyze_email(email):
    # Main function: gets all analysis fields in one LLM call
    email_text = format_email(email)

    prompt = ANALYSIS_PROMPT.format(
        email=email_text
    )

    result = call_llm(prompt)

    return json.loads(result)


def summarize_email(email):
    email_text = format_email(email)

    prompt = SUMMARY_PROMPT.format(
        email=email_text
    )

    # Summary prompt returns normal text instead of JSON
    return call_llm(prompt)


def classify_email(email):
    email_text = format_email(email)

    prompt = CLASSIFICATION_PROMPT.format(
        email=email_text
    )

    result = call_llm(prompt)

    return json.loads(result)


def analyze_sentiment(email):
    email_text = format_email(email)

    prompt = SENTIMENT_PROMPT.format(
        email=email_text
    )

    result = call_llm(prompt)

    return json.loads(result)