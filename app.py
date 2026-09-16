import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)

APP_NAME = os.getenv(
    "APP_NAME",
    "AI Powered Email Assistant",
)


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📧",
    layout="wide",
)


# -------------------------
# Helper Functions
# -------------------------

def check_backend():
    try:
        response = requests.get(
            f"{API_URL}/health",
            timeout=5,
        )

        return response.ok

    except requests.RequestException:
        return False


def select_email(email):
    # Clear old AI results when the user opens another email
    st.session_state["selected_email"] = email
    st.session_state.pop("analysis", None)
    st.session_state.pop("draft_reply", None)


# -------------------------
# Page Header
# -------------------------

st.title(APP_NAME)

st.caption(
    "Understand, prioritize, search, and reply to emails with AI."
)


# -------------------------
# Sidebar
# -------------------------

st.sidebar.title("📧 Mail Assistant")


if check_backend():
    st.sidebar.success("Backend connected")
else:
    st.sidebar.error("Backend unavailable")


email_limit = st.sidebar.number_input(
    "Emails to load",
    min_value=1,
    max_value=50,
    value=10,
)


# Load emails directly from Gmail
if st.sidebar.button(
    "Load Recent Emails",
    use_container_width=True,
):
    try:
        with st.spinner("Loading emails..."):
            response = requests.get(
                f"{API_URL}/emails",
                params={
                    "limit": email_limit,
                },
                timeout=30,
            )

        if response.ok:
            st.session_state["emails"] = response.json()
            st.sidebar.success("Emails loaded")

        else:
            st.sidebar.error(
                response.json().get(
                    "detail",
                    "Could not load emails",
                )
            )

    except requests.RequestException:
        st.sidebar.error(
            "Could not connect to backend"
        )


# Analyze + embed new emails into ChromaDB
if st.sidebar.button(
    "Sync Emails",
    use_container_width=True,
):
    try:
        with st.spinner(
            "Analyzing and storing emails..."
        ):
            response = requests.post(
                f"{API_URL}/sync-emails",
                params={
                    "limit": email_limit,
                },
                timeout=120,
            )

        if response.ok:
            result = response.json()

            st.sidebar.success(
                f"Stored {result['stored']} | "
                f"Skipped {result['skipped']}"
            )

        else:
            st.sidebar.error(
                response.json().get(
                    "detail",
                    "Sync failed",
                )
            )

    except requests.RequestException:
        st.sidebar.error(
            "Could not connect to backend"
        )


# -------------------------
# Semantic Search
# -------------------------

st.sidebar.divider()

st.sidebar.subheader("Semantic Search")

search_query = st.sidebar.text_input(
    "Search your emails",
    placeholder="e.g. leave requests",
)


if st.sidebar.button(
    "Search",
    use_container_width=True,
):
    if not search_query.strip():
        st.sidebar.warning(
            "Enter something to search."
        )

    else:
        try:
            response = requests.get(
                f"{API_URL}/search-emails",
                params={
                    "query": search_query,
                    "top_k": 5,
                },
                timeout=30,
            )

            if response.ok:
                st.session_state[
                    "search_results"
                ] = response.json()

            else:
                st.sidebar.error(
                    "Search failed"
                )

        except requests.RequestException:
            st.sidebar.error(
                "Could not connect to backend"
            )


# -------------------------
# Search Results
# -------------------------

if "search_results" in st.session_state:
    st.subheader("🔎 Semantic Search Results")

    results = st.session_state[
        "search_results"
    ]

    documents = results.get(
        "documents",
        [[]],
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]],
    )[0]

    distances = results.get(
        "distances",
        [[]],
    )[0]

    if not documents:
        st.info(
            "No indexed emails found. "
            "Try syncing your emails first."
        )

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        with st.expander(
            metadata.get(
                "subject",
                "No Subject",
            )
        ):
            st.write(
                "**From:**",
                metadata.get(
                    "sender",
                    "",
                ),
            )

            st.write(
                "**Urgency:**",
                metadata.get(
                    "urgency",
                    "",
                ),
            )

            st.write(
                "**Topic:**",
                metadata.get(
                    "topic",
                    "",
                ),
            )

            st.write(document)

            st.caption(
                f"Vector distance: "
                f"{distance:.3f}"
            )


    st.divider()


# -------------------------
# Inbox + Email Preview
# -------------------------

if "emails" not in st.session_state:
    st.info(
        "👈 Click **Load Recent Emails** "
        "to open your inbox."
    )

else:
    emails = st.session_state["emails"]

    inbox_column, email_column = st.columns(
        [1, 2],
        gap="large",
    )


    # -------------------------
    # Inbox
    # -------------------------

    with inbox_column:
        st.subheader("Inbox")

        st.caption(
            f"{len(emails)} recent emails"
        )

        for email in emails:
            with st.container(border=True):
                subject = (
                    email["subject"]
                    or "No Subject"
                )

                st.markdown(
                    f"**{subject}**"
                )

                st.caption(
                    email["sender"]
                )

                preview = (
                    email["body"]
                    .replace("\n", " ")
                    [:120]
                )

                if preview:
                    st.write(
                        preview + "..."
                    )

                if st.button(
                    "Open",
                    key=f"open_{email['id']}",
                    use_container_width=True,
                ):
                    select_email(email)
                    st.rerun()


    # -------------------------
    # Selected Email
    # -------------------------

    with email_column:

        if "selected_email" not in st.session_state:
            st.subheader("Select an email")

            st.write(
                "Choose an email from the inbox "
                "to preview and analyze it."
            )

        else:
            email = st.session_state[
                "selected_email"
            ]

            st.subheader(
                email["subject"]
                or "No Subject"
            )

            st.write(
                f"**From:** {email['sender']}"
            )

            st.caption(
                email["date"]
            )

            st.divider()

            st.markdown("### Message")

            st.write(
                email["body"]
                or "No readable text body found."
            )


            # -------------------------
            # AI Analysis
            # -------------------------

            st.divider()

            st.markdown("### AI Analysis")

            if st.button(
                "Analyze Email",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Analyzing email..."
                    ):
                        response = requests.get(
                            f"{API_URL}/analyze/"
                            f"{email['id']}",
                            timeout=60,
                        )

                    if response.ok:
                        st.session_state[
                            "analysis"
                        ] = response.json()

                    else:
                        st.error(
                            "Email analysis failed."
                        )

                except requests.RequestException:
                    st.error(
                        "Could not connect "
                        "to backend."
                    )


            if "analysis" in st.session_state:
                analysis = st.session_state[
                    "analysis"
                ]

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Urgency",
                    analysis.get(
                        "urgency",
                        "-",
                    ),
                )

                col2.metric(
                    "Sentiment",
                    analysis.get(
                        "sentiment",
                        "-",
                    ),
                )

                col3.metric(
                    "Topic",
                    analysis.get(
                        "topic",
                        "-",
                    ),
                )

                st.write(
                    "**Summary:**",
                    analysis.get(
                        "summary",
                        "",
                    ),
                )

                st.write(
                    "**Intent:**",
                    analysis.get(
                        "intent",
                        "",
                    ),
                )

                safety1, safety2 = st.columns(2)

                profanity = analysis.get(
                    "profanity",
                    False,
                )

                unsafe = analysis.get(
                    "unsafe_content",
                    False,
                )

                safety1.write(
                    "**Profanity:**",
                    "⚠️ Detected"
                    if profanity
                    else "✅ Not detected",
                )

                safety2.write(
                    "**Unsafe Content:**",
                    "⚠️ Detected"
                    if unsafe
                    else "✅ Not detected",
                )


            # -------------------------
            # AI Reply
            # -------------------------

            st.divider()

            st.markdown("### AI Reply")

            if st.button(
                "Generate AI Reply",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Generating reply..."
                    ):
                        response = requests.get(
                            f"{API_URL}/generate-reply/"
                            f"{email['id']}",
                            timeout=60,
                        )

                    if response.ok:
                        result = response.json()

                        st.session_state[
                            "draft_reply"
                        ] = result["reply"]

                    else:
                        st.error(
                            "Could not generate reply."
                        )

                except requests.RequestException:
                    st.error(
                        "Could not connect "
                        "to backend."
                    )


            # The AI never sends automatically.
            # The user can edit the draft before explicitly sending it.
            if "draft_reply" in st.session_state:
                edited_reply = st.text_area(
                    "Review and edit reply",
                    value=st.session_state[
                        "draft_reply"
                    ],
                    height=250,
                )

                st.warning(
                    "Review the reply before sending. "
                    "Sending cannot be undone."
                )

                if st.button(
                    "Send Reply",
                    type="primary",
                    use_container_width=True,
                ):
                    if not edited_reply.strip():
                        st.warning(
                            "Reply cannot be empty."
                        )

                    else:
                        try:
                            with st.spinner(
                                "Sending reply..."
                            ):
                                response = requests.post(
                                    f"{API_URL}/send-reply/"
                                    f"{email['id']}",
                                    params={
                                        "reply_text":
                                            edited_reply,
                                    },
                                    timeout=60,
                                )

                            if response.ok:
                                st.success(
                                    "Reply sent successfully."
                                )

                                st.session_state.pop(
                                    "draft_reply",
                                    None,
                                )

                            else:
                                st.error(
                                    "Failed to send reply."
                                )

                        except requests.RequestException:
                            st.error(
                                "Could not connect "
                                "to backend."
                            )