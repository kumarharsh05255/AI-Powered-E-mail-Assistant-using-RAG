import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


BACKEND_URL="http://127.0.0.1:8000"


APP_NAME="AI-Powered Email Assistant"


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📧",
    layout="wide",
)


# -------------------------
# Helpers
# -------------------------

def check_backend():
    try:
        response = requests.get(
            f"{BACKEND_URL}/health",
            timeout=5,
        )

        return response.ok

    except requests.RequestException:
        return False


def select_email(email):
    # Remove results belonging to the previously selected email
    st.session_state["selected_email"] = email
    st.session_state.pop("analysis", None)
    st.session_state.pop("draft_reply", None)


def urgency_icon(urgency):
    icons = {
        "High": "🔴",
        "Medium": "🟡",
        "Low": "🟢",
    }

    return icons.get(
        urgency,
        "⚪",
    )


# -------------------------
# Header
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
    st.sidebar.success(
        "Backend connected"
    )
else:
    st.sidebar.error(
        "Backend unavailable"
    )


email_limit = st.sidebar.number_input(
    "Emails to load",
    min_value=1,
    max_value=50,
    value=10,
)


if st.sidebar.button(
    "Load Recent Emails",
    use_container_width=True,
):
    try:
        with st.spinner(
            "Loading emails..."
        ):
            response = requests.get(
                f"{BACKEND_URL}/emails",
                params={
                    "limit": email_limit,
                },
                timeout=30,
            )

        if response.ok:
            st.session_state["emails"] = response.json()
            st.session_state["prioritized"] = False

        else:
            st.sidebar.error(
                "Could not load emails"
            )

    except requests.RequestException:
        st.sidebar.error(
            "Could not connect to backend"
        )


if st.sidebar.button(
    "Sync & Prioritize",
    use_container_width=True,
):
    try:
        # First sync new emails so their analysis is available
        with st.spinner(
            "Analyzing and prioritizing emails..."
        ):
            sync_response = requests.post(
                f"{BACKEND_URL}/sync-emails",
                params={
                    "limit": email_limit,
                },
                timeout=120,
            )

        if not sync_response.ok:
            st.sidebar.error(
                "Email sync failed"
            )

        else:
            sync_result = sync_response.json()

            # Load the analyzed inbox already sorted by urgency
            inbox_response = requests.get(
                f"{BACKEND_URL}/inbox",
                timeout=30,
            )

            if inbox_response.ok:
                st.session_state[
                    "emails"
                ] = inbox_response.json()

                st.session_state[
                    "prioritized"
                ] = True

                st.sidebar.success(
                    f"Stored {sync_result['stored']} | "
                    f"Skipped {sync_result['skipped']}"
                )

    except requests.RequestException:
        st.sidebar.error(
            "Could not connect to backend"
        )


# -------------------------
# Semantic Search
# -------------------------

st.sidebar.divider()

st.sidebar.subheader(
    "Semantic Search"
)

search_query = st.sidebar.text_input(
    "Search your emails",
    placeholder="e.g. leave requests",
)


if st.sidebar.button(
    "Search",
    use_container_width=True,
):
    if search_query.strip():
        try:
            response = requests.get(
                f"{BACKEND_URL}/search-emails",
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

        except requests.RequestException:
            st.sidebar.error(
                "Search failed"
            )


# -------------------------
# Search Results
# -------------------------

if "search_results" in st.session_state:
    st.subheader(
        "🔎 Search Results"
    )

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
            "Sync emails first."
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
# Inbox
# -------------------------

if "emails" not in st.session_state:
    st.info(
        "👈 Load or sync your emails to begin."
    )

else:
    emails = st.session_state["emails"]

    inbox_column, email_column = st.columns(
        [1, 2],
        gap="large",
    )


    with inbox_column:
        st.subheader("Inbox")

        if st.session_state.get(
            "prioritized",
            False,
        ):
            st.caption(
                "Sorted by AI urgency"
            )
        else:
            st.caption(
                f"{len(emails)} recent emails"
            )


        for email in emails:
            analysis = email.get(
                "analysis"
            )

            with st.container(
                border=True
            ):
                if analysis:
                    urgency = analysis.get(
                        "urgency",
                        "",
                    )

                    st.write(
                        f"{urgency_icon(urgency)} "
                        f"**{urgency.upper()}**"
                    )

                st.markdown(
                    f"**{email.get('subject', 'No Subject')}**"
                )

                st.caption(
                    email.get(
                        "sender",
                        "",
                    )
                )

                # Synced emails already have an AI summary
                if analysis:
                    st.write(
                        analysis.get(
                            "summary",
                            "",
                        )
                    )

                    st.caption(
                        f"{analysis.get('topic', '')} • "
                        f"{analysis.get('sentiment', '')}"
                    )

                else:
                    preview = (
                        email.get(
                            "body",
                            "",
                        )
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

                    # Reuse saved analysis when opening a synced email
                    if analysis:
                        st.session_state[
                            "analysis"
                        ] = analysis

                    st.rerun()


    # -------------------------
    # Email Preview
    # -------------------------

    with email_column:

        if "selected_email" not in st.session_state:
            st.subheader(
                "Select an email"
            )

            st.write(
                "Choose an email from the inbox "
                "to preview it."
            )

        else:
            email = st.session_state[
                "selected_email"
            ]

            st.subheader(
                email.get(
                    "subject",
                    "No Subject",
                )
            )

            st.write(
                f"**From:** "
                f"{email.get('sender', '')}"
            )

            st.caption(
                email.get(
                    "date",
                    "",
                )
            )

            st.divider()

            st.markdown(
                "### Message"
            )

            st.write(
                email.get(
                    "body",
                    "",
                )
                or "No readable text body found."
            )


            # -------------------------
            # AI Analysis
            # -------------------------

            st.divider()

            st.markdown(
                "### AI Analysis"
            )


            if "analysis" not in st.session_state:

                if st.button(
                    "Analyze Email",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner(
                            "Analyzing email..."
                        ):
                            response = requests.get(
                                f"{BACKEND_URL}/analyze/"
                                f"{email['id']}",
                                timeout=60,
                            )

                        if response.ok:
                            st.session_state[
                                "analysis"
                            ] = response.json()

                            st.rerun()

                    except requests.RequestException:
                        st.error(
                            "Analysis failed"
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

            st.markdown(
                "### AI Reply"
            )


            if st.button(
                "Generate AI Reply",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Generating reply..."
                    ):
                        response = requests.get(
                            f"{BACKEND_URL}/generate-reply/"
                            f"{email['id']}",
                            timeout=60,
                        )

                    if response.ok:
                        st.session_state[
                            "draft_reply"
                        ] = response.json()[
                            "reply"
                        ]

                        st.rerun()

                except requests.RequestException:
                    st.error(
                        "Reply generation failed"
                    )


            # AI creates only a draft. Sending always requires user approval.
            if "draft_reply" in st.session_state:
                edited_reply = st.text_area(
                    "Review and edit reply",
                    value=st.session_state[
                        "draft_reply"
                    ],
                    height=250,
                )

                st.warning(
                    "Review the reply before sending."
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
                                    f"{BACKEND_URL}/send-reply/"
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