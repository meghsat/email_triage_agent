import streamlit as st
from streamlit_autorefresh import st_autorefresh
import asyncio
from datetime import datetime

from triage_agent import get_agent
from config import settings

st.set_page_config(
    page_title="Personal Triage",
    layout="wide",
    initial_sidebar_state="collapsed"
)

refresh_interval = settings.refresh_interval_minutes * 60 * 1000
st_autorefresh(interval=refresh_interval, key="data_refresh")

st.markdown("""
<style>
    .email-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        margin-bottom: 0.5rem;
    }
    .event-card {
        padding: 1rem;
        border-left: 4px solid #4CAF50;
        background-color: #f1f8f4;
        margin-bottom: 0.5rem;
    }
    .urgent-badge {
        background-color: #ff4444;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=settings.refresh_interval_minutes * 60, show_spinner=False)
def fetch_data():
    agent = get_agent()
    return asyncio.run(agent.run_triage())


def main():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("Personal Triage Dashboard")
    with col2:
        if st.button("Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col3:
        st.caption(f"Auto-refresh: {settings.refresh_interval_minutes}min")

    with st.spinner("Fetching latest data..."):
        result = fetch_data()

    if result.errors:
        for error in result.errors:
            st.error(f"{error}")

    st.caption(f"Last updated: {result.last_updated.strftime('%B %d, %Y at %I:%M %p')}")

    # Extract unique accounts for filtering
    account_emails = set()
    account_labels = {}

    for email in result.emails:
        if email.account_email:
            account_emails.add(email.account_email)
            account_labels[email.account_email] = email.account_label

    for event in result.calendar_events:
        if event.account_email:
            account_emails.add(event.account_email)
            account_labels[event.account_email] = event.account_label

    # Initialize filtered data
    selected_account = None
    filtered_emails = result.emails
    filtered_events = result.calendar_events

    # Show account filter if multiple accounts
    if len(account_emails) > 1:
        st.subheader("Filter by Account")
        all_accounts = ["All Accounts"] + [
            f"{account_labels.get(email, email)} ({email})"
            for email in sorted(account_emails)
        ]

        selected_display = st.selectbox(
            "Select Account",
            all_accounts,
            key="account_filter"
        )

        if selected_display != "All Accounts":
            selected_account = selected_display.split("(")[1].rstrip(")")
            filtered_emails = [
                e for e in result.emails
                if e.account_email == selected_account
            ]
            filtered_events = [
                ev for ev in result.calendar_events
                if ev.account_email == selected_account
            ]

    st.divider()

    st.header("Email Summary (Last 24 Hours)")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Emails", len(filtered_emails))
    with col2:
        unread_count = sum(1 for e in filtered_emails if e.is_unread)
        st.metric("Unread", unread_count)
    with col3:
        urgent_count = result.analysis.urgent_count if result.analysis else 0
        st.metric("Urgent", urgent_count, delta_color="inverse")
    with col4:
        if len(account_emails) > 1:
            st.metric("Accounts", len(account_emails))

    if result.analysis:
        # Filter analysis based on filtered emails
        filtered_subjects = {email.subject for email in filtered_emails}

        # Filter categories to only include subjects from filtered emails
        filtered_categories = []
        if result.analysis.categories:
            for cat in result.analysis.categories:
                matching_subjects = [s for s in cat.subjects if s in filtered_subjects]
                if matching_subjects:
                    from lemonade_client import EmailCategory
                    filtered_cat = EmailCategory(
                        name=cat.name,
                        count=len(matching_subjects),
                        subjects=matching_subjects
                    )
                    filtered_categories.append(filtered_cat)

        # Recalculate urgent count for filtered emails
        filtered_urgent_count = sum(
            1 for cat in filtered_categories
            if cat.name.lower() in ['urgent', 'time-sensitive', 'action required']
        )

        st.write("**Overview:**")
        if selected_account:
            # Show filtered summary
            if filtered_categories:
                category_summary = ", ".join([f"{cat.count} {cat.name}" for cat in filtered_categories[:3]])
                st.info(f"Showing {len(filtered_emails)} emails from {account_labels.get(selected_account, selected_account)}: {category_summary}")
            else:
                st.info(f"Showing {len(filtered_emails)} emails from {account_labels.get(selected_account, selected_account)}")
        else:
            st.info(result.analysis.summary)

        if filtered_categories:
            st.write("**Categories:**")
            for cat in filtered_categories:
                with st.expander(f"{cat.name.title()} ({cat.count})"):
                    for subject in cat.subjects:
                        st.markdown(f"- {subject}")

    with st.expander(f"View All {len(filtered_emails)} Emails"):
        for email in filtered_emails:
            # Add account badge if multi-account
            account_badge = ""
            if len(account_emails) > 1 and email.account_label:
                account_badge = f"**[{email.account_label}]** "

            unread_badge = "🟦 " if email.is_unread else ""
            st.markdown(f"""
            {account_badge}**{unread_badge}{email.subject}**
            From: {email.sender} | {email.date_str}
            {email.snippet[:150]}...
            [Open in Gmail]({email.link})
            """)
            st.divider()

    st.divider()

    st.header("Emails Needing Response")

    if selected_account:
        filtered_response_emails = [
            e for e in result.emails_needing_response
            if e.account_email == selected_account
        ]
    else:
        filtered_response_emails = result.emails_needing_response

    if not filtered_response_emails:
        st.success("No emails requiring your response right now!")
    else:
        st.warning(f"{len(filtered_response_emails)} email(s) need your attention")

        for i, email in enumerate(filtered_response_emails, 1):
            account_info = ""
            if len(account_emails) > 1 and email.account_label:
                account_info = f"<span style='background-color: #fff3cd; padding: 2px 6px; border-radius: 3px;'>{email.account_label}</span> "

            st.markdown(f"""
            <div class="email-card">
                {account_info}<strong>{i}. {email.subject}</strong><br>
                <small>From: {email.sender} | {email.date_str}</small><br>
                {email.snippet}<br>
                <a href="{email.link}" target="_blank">📧 Open in Gmail</a>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.header("Today's Calendar")

    if not filtered_events:
        st.info("No events scheduled for today.")
    else:
        st.write(f"**{len(filtered_events)} event(s) today:**")

        for event in filtered_events:
            status_emoji = "🔴" if "In progress" in event.time_until else "🟢"

            account_badge = ""
            if len(account_emails) > 1 and event.account_label:
                account_badge = f"<span style='background:#e3f2fd;padding:2px 6px;border-radius:3px;font-size:0.85em;'>{event.account_label}</span> "

            st.markdown(f"""
            <div class="event-card">
                {account_badge}{status_emoji} <strong>{event.summary}</strong>
                <span style="float: right; color: #666;">{event.time_until}</span><br>
                <small>{event.duration_str}</small><br>
                {f'<small>{event.location}</small><br>' if event.location else ''}
                {f'<small>{len(event.attendees)} attendees</small><br>' if event.attendees else ''}
                <a href="{event.link}" target="_blank">📆 Open in Calendar</a>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
