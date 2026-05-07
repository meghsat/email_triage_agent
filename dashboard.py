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

    st.divider()

    st.header("Email Summary (Last 24 Hours)")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Emails", len(result.emails))
    with col2:
        unread_count = sum(1 for e in result.emails if e.is_unread)
        st.metric("Unread", unread_count)
    with col3:
        urgent_count = result.analysis.urgent_count if result.analysis else 0
        st.metric("Urgent", urgent_count, delta_color="inverse")

    if result.analysis:
        st.write("**Overview:**")
        st.info(result.analysis.summary)

        if result.analysis.categories:
            st.write("**Categories:**")
            for cat in result.analysis.categories:
                with st.expander(f"📁 {cat.name.title()} ({cat.count})"):
                    for subject in cat.subjects:
                        st.markdown(f"- {subject}")

    with st.expander(f"📬 View All {len(result.emails)} Emails"):
        for email in result.emails:
            unread_badge = "🟦 " if email.is_unread else ""
            st.markdown(f"""
            **{unread_badge}{email.subject}**
            From: {email.sender} | {email.date_str}
            {email.snippet[:150]}...
            [Open in Gmail]({email.link})
            """)
            st.divider()

    st.divider()

    st.header("Emails Needing Response")

    if not result.emails_needing_response:
        st.success("No emails requiring your response right now!")
    else:
        st.warning(f"{len(result.emails_needing_response)} email(s) need your attention")

        for i, email in enumerate(result.emails_needing_response, 1):
            st.markdown(f"""
            <div class="email-card">
                <strong>{i}. {email.subject}</strong><br>
                <small>From: {email.sender} | {email.date_str}</small><br>
                {email.snippet}<br>
                <a href="{email.link}" target="_blank">📧 Open in Gmail</a>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.header("Today's Calendar")

    if not result.calendar_events:
        st.info("No events scheduled for today.")
    else:
        st.write(f"**{len(result.calendar_events)} event(s) today:**")

        for event in result.calendar_events:
            status_emoji = "🔴" if "In progress" in event.time_until else "🟢"

            st.markdown(f"""
            <div class="event-card">
                {status_emoji} <strong>{event.summary}</strong>
                <span style="float: right; color: #666;">{event.time_until}</span><br>
                <small>{event.duration_str}</small><br>
                {f'<small>{event.location}</small><br>' if event.location else ''}
                {f'<small>{len(event.attendees)} attendees</small><br>' if event.attendees else ''}
                <a href="{event.link}" target="_blank">📆 Open in Calendar</a>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
