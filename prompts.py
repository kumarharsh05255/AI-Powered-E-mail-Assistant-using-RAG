SYSTEM_PROMPT = """
You are an AI Email Assistant.

Analyze emails accurately, concisely, and professionally.

When a prompt requests JSON:
- Return valid JSON only.
- Do not use Markdown.
- Do not use code blocks.
- Do not include explanations before or after the JSON.
"""


ANALYSIS_PROMPT = """
Analyze the following email.

Return exactly these fields:

{{
    "summary": "...",
    "urgency": "High",
    "intent": "...",
    "topic": "...",
    "sentiment": "Positive",
    "profanity": false,
    "unsafe_content": false
}}

Rules:

- summary: Give a short and clear summary of the email.
- urgency: Must be exactly "High", "Medium", or "Low".
- intent: Describe what the sender wants or is trying to communicate.
- topic: Identify the main subject or category of the email.
- sentiment: Must be exactly "Positive", "Neutral", or "Negative".
- profanity: true only if the email contains profane, obscene, insulting,
  or abusive language. Otherwise false.
- unsafe_content: true if the email contains threats, harmful instructions,
  dangerous requests, harassment, or other clearly unsafe content.
  Otherwise false.

Urgency guidelines:

High:
- Requires immediate attention.
- Contains an important deadline.
- Serious complaint or escalation.
- Security-related issue.
- Urgent payment or business issue.

Medium:
- Normal work request requiring action.
- Meeting request.
- Leave request.
- Routine business request that is not immediately urgent.

Low:
- Informational email.
- Newsletter.
- General update.
- Routine communication requiring little or no action.

Email:

{email}
"""


SUMMARY_PROMPT = """
Summarize the following email in 2-3 concise sentences.

Email:

{email}
"""


CLASSIFICATION_PROMPT = """
Classify the following email.

Return exactly these fields:

{{
    "urgency": "High",
    "intent": "...",
    "topic": "..."
}}

Rules:

- urgency: Must be exactly "High", "Medium", or "Low".
- intent: Describe what the sender wants or is trying to communicate.
- topic: Identify the main subject or category of the email.

Email:

{email}
"""


SENTIMENT_PROMPT = """
Analyze the sentiment and safety of the following email.

Return exactly these fields:

{{
    "sentiment": "Positive",
    "profanity": false,
    "unsafe_content": false
}}

Rules:

- sentiment: Must be exactly "Positive", "Neutral", or "Negative".
- profanity: true only if the email contains profane, obscene, insulting,
  or abusive language. Otherwise false.
- unsafe_content: true if the email contains threats, harmful instructions,
  dangerous requests, harassment, or other clearly unsafe content.
  Otherwise false.

Email:

{email}
"""


REPLY_PROMPT = """
You are an AI Email Assistant.

Generate a professional, concise, and context-aware reply to the original email.

Use the relevant historical context only when it is useful.
If the context is not relevant, reply based only on the original email.

Original Email:

{email}


Relevant Historical Context:

{context}


Instructions:

- Return only the email reply text.
- Do not return JSON.
- Do not include fields such as "to", "subject", "body", "reply", or "response".
- Do not wrap the reply in quotation marks.
- Do not use Markdown code blocks.
- Do not mention historical emails, retrieved context, RAG, embeddings,
  or vector databases.
"""