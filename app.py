import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


BACKEND_URL = "http://127.0.0.1:8000"
APP_NAME = "AI-Powered Email Assistant"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📧",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

if "show_startup_message" not in st.session_state:
    st.session_state["show_startup_message"] = True

if "active_view" not in st.session_state:
    st.session_state["active_view"] = "startup"


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>

        .block-container {
            padding-top: 1rem;
        }

        .stApp {
            font-size: 14px;
        }

        section[data-testid="stSidebar"] {
            font-size: 14px;
        }

        /* Hide "Press Enter to apply" */
        div[data-testid="InputInstructions"] {
            display: none;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

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

    st.session_state["selected_email"] = email

    st.session_state.pop(
        "analysis",
        None,
    )

    st.session_state.pop(
        "draft_reply",
        None,
    )


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


def find_email_by_id(email_id):

    """
    Find an already-loaded email using its real email ID.
    """

    emails = st.session_state.get(
        "emails",
        [],
    )

    for email in emails:

        if str(email.get("id")) == str(email_id):

            return email

    return None


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f'<div style="text-align:center; margin-bottom:40px;">'
    f'<h1 style="font-size:42px; margin:0; line-height:1.1;">'
    f'{APP_NAME}'
    f'</h1>'
    f'<div style="font-size:15px; color:#888; margin-top:-15px;">'
    f'Understand, prioritize, search, and reply to emails with AI.'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "📧 Mail Assistant"
)


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


# ============================================================
# LOAD RECENT EMAILS
# ============================================================

if st.sidebar.button(
    "Load Recent Emails",
    use_container_width=True,
):

    st.session_state[
        "show_startup_message"
    ] = False

    st.session_state[
        "active_view"
    ] = "inbox"

    st.session_state.pop(
        "search_results",
        None,
    )

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

            st.session_state[
                "emails"
            ] = response.json()

            st.session_state[
                "prioritized"
            ] = False

            st.session_state.pop(
                "selected_email",
                None,
            )

            st.session_state.pop(
                "analysis",
                None,
            )

            st.session_state.pop(
                "draft_reply",
                None,
            )

        else:

            st.sidebar.error(
                "Could not load emails."
            )

    except requests.RequestException:

        st.sidebar.error(
            "Could not connect to backend."
        )


# ============================================================
# STORE + RANK
# ============================================================

if st.sidebar.button(
    "Store in VectorDB and Rank by Urgency",
    use_container_width=True,
):

    st.session_state[
        "show_startup_message"
    ] = False

    st.session_state[
        "active_view"
    ] = "inbox"

    st.session_state.pop(
        "search_results",
        None,
    )

    try:

        with st.spinner(
            "Analyzing and ranking emails..."
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
                "Email sync failed."
            )

        else:

            sync_result = (
                sync_response.json()
            )

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

                st.session_state.pop(
                    "selected_email",
                    None,
                )

                st.session_state.pop(
                    "analysis",
                    None,
                )

                st.session_state.pop(
                    "draft_reply",
                    None,
                )

                st.sidebar.success(
                    f"Stored {sync_result['stored']} | "
                    f"Skipped {sync_result['skipped']}"
                )

            else:

                st.sidebar.error(
                    "Could not load ranked inbox."
                )

    except requests.RequestException:

        st.sidebar.error(
            "Could not connect to backend."
        )


# ============================================================
# SEMANTIC SEARCH
# ============================================================

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

    st.session_state[
        "show_startup_message"
    ] = False

    if not search_query.strip():

        st.sidebar.warning(
            "Enter something to search."
        )

    else:

        try:

            with st.spinner(
                "Searching emails..."
            ):

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

                st.session_state[
                    "active_view"
                ] = "search"

            else:

                st.sidebar.error(
                    "Search failed."
                )

        except requests.RequestException:

            st.sidebar.error(
                "Search failed."
            )


# ============================================================
# STARTUP VIEW
# ============================================================

if (
    st.session_state.get(
        "active_view"
    ) == "startup"
    and st.session_state.get(
        "show_startup_message",
        False,
    )
):

    st.info(
        "👈 Load or sync your emails to begin."
    )


# ============================================================
# SEARCH RESULTS
# ============================================================

if (
    st.session_state.get(
        "active_view"
    ) == "search"
    and "search_results" in st.session_state
):

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

    if not documents:

        st.info(
            "No matching emails found."
        )

    else:

        st.caption(
            f"{len(documents)} matching emails"
        )

        for index, (
            document,
            metadata,
        ) in enumerate(
            zip(
                documents,
                metadatas,
            )
        ):

            # --------------------------------
            # Metadata
            # --------------------------------

            email_id = metadata.get(
                "email_id"
            )

            subject = metadata.get(
                "subject",
                "No Subject",
            )

            sender = metadata.get(
                "sender",
                "",
            )

            urgency = metadata.get(
                "urgency",
                "",
            )

            topic = metadata.get(
                "topic",
                "",
            )

            sentiment = metadata.get(
                "sentiment",
                "",
            )

            summary = metadata.get(
                "summary",
                "",
            )

            # --------------------------------
            # Search Email Card
            # --------------------------------

            with st.container(
                border=True
            ):

                content_col, action_col = st.columns(
                    [4, 1],
                    vertical_alignment="top",
                )

                # ============================
                # LEFT
                # ============================

                with content_col:

                    st.markdown(
                        f"**{subject}**"
                    )

                    if sender:

                        st.caption(
                            sender
                        )

                    # Prefer AI summary
                    if summary:

                        preview = summary

                    else:

                        preview = (
                            str(document)
                            .replace("\n", " ")
                            .strip()
                        )

                        # Remove duplicated Subject prefix
                        if preview.startswith(
                            "Subject:"
                        ):

                            body_position = (
                                preview.find(
                                    "Body:"
                                )
                            )

                            if body_position != -1:

                                preview = preview[
                                    body_position + 5:
                                ].strip()

                    if len(preview) > 180:

                        preview = (
                            preview[:180]
                            + "..."
                        )

                    if preview:

                        st.write(
                            preview
                        )

                    details = []

                    if topic:

                        details.append(
                            topic
                        )

                    if sentiment:

                        details.append(
                            sentiment
                        )

                    if details:

                        st.caption(
                            " • ".join(
                                details
                            )
                        )

                # ============================
                # RIGHT
                # ============================

                with action_col:

                    if urgency:

                        st.markdown(
                            f"{urgency_icon(urgency)} "
                            f"**{urgency.upper()}**"
                        )

                # ============================
                # OPEN
                # ============================

                if st.button(
                    "Open",
                    key=f"search_open_{index}",
                    use_container_width=True,
                ):

                    if not email_id:

                        st.error(
                            "This search result does not "
                            "contain an email ID."
                        )

                    else:

                        # Try to find the complete loaded email
                        search_email = (
                            find_email_by_id(
                                email_id
                            )
                        )

                        # If it isn't loaded, construct it
                        # from the search result
                        if search_email is None:

                            search_email = {
                                "id": email_id,
                                "subject": subject,
                                "sender": sender,
                                "body": document,
                            }

                        select_email(
                            search_email
                        )

                        st.session_state[
                            "analysis"
                        ] = {
                            "urgency":
                                urgency,
                            "topic":
                                topic,
                            "sentiment":
                                sentiment,
                            "summary":
                                summary,
                        }

                        st.session_state[
                            "active_view"
                        ] = "inbox"

                        st.rerun()


# ============================================================
# INBOX
# ============================================================

if (
    st.session_state.get(
        "active_view"
    ) == "inbox"
    and "emails" in st.session_state
):

    emails = st.session_state[
        "emails"
    ]

    inbox_column, email_column = st.columns(
        [1, 2],
        gap="large",
    )

    # ========================================================
    # INBOX LIST
    # ========================================================

    with inbox_column:

        st.subheader(
            "Inbox"
        )

        if st.session_state.get(
            "prioritized",
            False,
        ):

            st.caption(
                "Sorted by Urgency (High to Low)"
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

                content_col, action_col = st.columns(
                    [3, 1],
                    vertical_alignment="top",
                )

                # ============================================
                # EMAIL INFO
                # ============================================

                with content_col:

                    st.markdown(
                        f"**{email.get('subject', 'No Subject')}**"
                    )

                    st.caption(
                        email.get(
                            "sender",
                            "",
                        )
                    )

                    if analysis:

                        summary = analysis.get(
                            "summary",
                            "",
                        )

                        if summary:

                            st.write(
                                summary
                            )

                        topic = analysis.get(
                            "topic",
                            "",
                        )

                        sentiment = analysis.get(
                            "sentiment",
                            "",
                        )

                        details = []

                        if topic:

                            details.append(
                                topic
                            )

                        if sentiment:

                            details.append(
                                sentiment
                            )

                        if details:

                            st.caption(
                                " • ".join(
                                    details
                                )
                            )

                    else:

                        preview = (
                            email.get(
                                "body",
                                "",
                            )
                            .replace(
                                "\n",
                                " ",
                            )
                            [:120]
                        )

                        if preview:

                            st.write(
                                preview + "..."
                            )

                # ============================================
                # RIGHT
                # ============================================

                with action_col:

                    if analysis:

                        urgency = analysis.get(
                            "urgency",
                            "-",
                        )

                        st.markdown(
                            f"{urgency_icon(urgency)} "
                            f"**{urgency.upper()}**"
                        )

                    else:

                        st.caption(
                            "Not analyzed"
                        )

                # ============================================
                # OPEN
                # ============================================

                if st.button(
                    "Open",
                    key=(
                        f"open_"
                        f"{email['id']}"
                    ),
                    use_container_width=True,
                ):

                    select_email(
                        email
                    )

                    if analysis:

                        st.session_state[
                            "analysis"
                        ] = analysis

                    st.rerun()

    # ========================================================
    # EMAIL PREVIEW
    # ========================================================

    with email_column:

        if (
            "selected_email"
            not in st.session_state
        ):

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

            # ================================================
            # EMAIL HEADER
            # ================================================

            st.subheader(
                email.get(
                    "subject",
                    "No Subject",
                )
            )

            st.markdown(
                f"**From:** "
                f"{email.get('sender', '')}"
            )

            if email.get(
                "date"
            ):

                st.caption(
                    email.get(
                        "date"
                    )
                )

            st.divider()

            # ================================================
            # MESSAGE
            # ================================================

            st.markdown(
                "### Message"
            )

            st.write(
                email.get(
                    "body",
                    "",
                )
                or
                "No readable text body found."
            )

            # ================================================
            # AI ANALYSIS
            # ================================================

            st.divider()

            st.markdown(
                "### AI Analysis"
            )

            if (
                "analysis"
                not in st.session_state
            ):

                if st.button(
                    "Analyze Email",
                    key="preview_analyze",
                    use_container_width=True,
                ):

                    try:

                        with st.spinner(
                            "Analyzing email..."
                        ):

                            response = requests.get(
                                f"{BACKEND_URL}"
                                f"/analyze/"
                                f"{email['id']}",
                                timeout=60,
                            )

                        if response.ok:

                            analysis_result = (
                                response.json()
                            )

                            st.session_state[
                                "analysis"
                            ] = analysis_result

                            # Update the inbox copy
                            for inbox_email in (
                                st.session_state.get(
                                    "emails",
                                    [],
                                )
                            ):

                                if (
                                    str(
                                        inbox_email.get(
                                            "id"
                                        )
                                    )
                                    ==
                                    str(
                                        email.get(
                                            "id"
                                        )
                                    )
                                ):

                                    inbox_email[
                                        "analysis"
                                    ] = (
                                        analysis_result
                                    )

                                    break

                            st.rerun()

                        else:

                            st.error(
                                "Analysis failed."
                            )

                    except requests.RequestException:

                        st.error(
                            "Analysis failed."
                        )

            # ================================================
            # ANALYSIS RESULTS
            # ================================================

            if (
                "analysis"
                in st.session_state
            ):

                analysis = (
                    st.session_state[
                        "analysis"
                    ]
                )

                col1, col2, col3 = st.columns(
                    3
                )

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

                summary = analysis.get(
                    "summary",
                    "",
                )

                intent = analysis.get(
                    "intent",
                    "",
                )

                if summary:

                    st.markdown(
                        f"**Summary:** "
                        f"{summary}"
                    )

                if intent:

                    st.markdown(
                        f"**Intent:** "
                        f"{intent}"
                    )

                profanity = analysis.get(
                    "profanity",
                    False,
                )

                unsafe = analysis.get(
                    "unsafe_content",
                    False,
                )

                safety1, safety2 = st.columns(
                    2
                )

                safety1.write(
                    f"**Profanity:** "
                    f"{'⚠️ Detected' if profanity else '✅ Not detected'}"
                )

                safety2.write(
                    f"**Unsafe Content:** "
                    f"{'⚠️ Detected' if unsafe else '✅ Not detected'}"
                )

            # ================================================
            # AI REPLY
            # ================================================

            st.divider()

            st.markdown(
                "### AI Reply"
            )

            if st.button(
                "Generate AI Reply",
                key="preview_generate_reply",
                use_container_width=True,
            ):

                try:

                    # stream=True keeps the HTTP connection open
                    # while the backend sends reply chunks.
                    response = requests.get(
                        f"{BACKEND_URL}"
                        f"/generate-reply/"
                        f"{email['id']}",
                        stream=True,
                        timeout=60,
                    )

                    if response.ok:

                        reply_placeholder = st.empty()

                        full_reply = ""

                        # Display each chunk as soon as it arrives.
                        for chunk in response.iter_content(
                            chunk_size=None,
                            decode_unicode=True,
                        ):

                            if chunk:

                                full_reply += chunk

                                reply_placeholder.markdown(
                                    full_reply + "▌"
                                )

                        # Remove the cursor after streaming finishes.
                        reply_placeholder.markdown(
                            full_reply
                        )

                        st.session_state[
                            "draft_reply"
                        ] = full_reply

                        st.rerun()

                    else:

                        st.error(
                            "Reply generation failed."
                        )

                except requests.RequestException:

                    st.error(
                        "Reply generation failed."
                    )

            # ================================================
            # REPLY EDITOR
            # ================================================

            if (
                "draft_reply"
                in st.session_state
            ):

                edited_reply = st.text_area(
                    "Review and edit reply",
                    value=(
                        st.session_state[
                            "draft_reply"
                        ]
                    ),
                    height=250,
                )

                st.warning(
                    "Review the reply before sending."
                )

                # ============================================
                # SEND REPLY
                # ============================================

                if st.button(
                    "Send Reply",
                    type="primary",
                    key="send_reply",
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
                                    f"{BACKEND_URL}"
                                    f"/send-reply/"
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
                                "Could not connect to backend."
                            )