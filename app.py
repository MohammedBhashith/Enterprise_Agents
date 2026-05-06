import streamlit as st

from graph import run_agent
from database import get_user
from logger import get_logs
from tools import get_pending_leave_requests_for_manager, approve_leave, reject_leave,get_all_ticket_rows,assign_ticket,resolve_ticket,get_inventory_status,get_pending_asset_requests_for_manager,get_pending_asset_requests_for_it,approve_asset_manager,approve_asset_it,reject_asset_manager,reject_asset_it


st.set_page_config(
    page_title="Enterprise AI Copilot",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.main-title {
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 5px;
}
.sub-title {
    font-size: 16px;
    color: #9ca3af;
    margin-bottom: 25px;
}
.info-card {
    padding: 18px;
    border-radius: 14px;
    background-color: #111827;
    border: 1px solid #374151;
    margin-bottom: 14px;
}
.metric-card {
    padding: 16px;
    border-radius: 12px;
    background-color: #1f2937;
    border: 1px solid #374151;
    text-align: center;
}
.small-muted {
    color: #9ca3af;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


st.markdown('<div class="main-title">Enterprise Multi-Agent AI Copilot</div>', unsafe_allow_html=True)



# ---------------- SIDEBAR ----------------

st.sidebar.title("User Login")

user_id = st.sidebar.text_input("Enter User ID", value="EMP001").strip()
user = get_user(user_id)

if user:
    st.sidebar.success(f"Logged in as {user['name']}")
    st.sidebar.markdown(f"**Role:** {user['role']}")
    st.sidebar.markdown(f"**Department:** {user['department']}")
else:
    st.sidebar.error("Invalid User ID")

page = st.sidebar.radio(
    "Navigation",
    ["Home", "Chat Assistant", "Manager Approvals", "IT Dashboard", "Demo Prompts", "Logs"]
)


# ---------------- HOME ----------------

if page == "Home":
    st.subheader("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card"><h3>HR Agent</h3><p>Leave + Policy</p></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card"><h3>IT Agent</h3><p>Tickets + Assets</p></div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card"><h3>RAG</h3><p>Policy Search</p></div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card"><h3>RBAC</h3><p>Secure Access</p></div>', unsafe_allow_html=True)

    st.write("")

    st.markdown("""
    ### Implemented Concepts

    - LangGraph workflow orchestration
    - Router, HR, IT, and RAG agents
    - Role-based access control
    - SQLite enterprise database
    - ChromaDB vector search
    - Local embeddings for lower API usage
    - Gemini/Groq model switching
    - Memory and logging
    - Manager approval dashboard
    """)

    st.info("Use the Chat Assistant page to test HR and IT workflows.")


# ---------------- CHAT ----------------

elif page == "Chat Assistant":
    st.subheader("Chat Assistant")

    if user:
        st.caption(f"Current user: {user['name']} | Role: {user['role']} | ID: {user_id}")
    else:
        st.warning("Please enter a valid User ID in the sidebar.")

    chat_key = f"messages_{user_id}"
    memory_key = f"conversation_memory_{user_id}"

    if memory_key not in st.session_state:
        st.session_state[memory_key] = {
            "first_query": None,
            "last_query": None,
            "pending_leave": None,
        }
    
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    col1, col2 = st.columns([1, 5])

    with col1:
        if st.button("Clear Chat"):
            st.session_state[chat_key] = []
            st.rerun()

    

    st.divider()

    if not st.session_state[chat_key]:
        st.markdown("""
        Try asking:
        - `hi`
        - `What is the notice period policy?`
        - `I want sick leave on May 5 because I have fever`
        - `show my leave balance`
        - `I have an issue in my laptop`
        """)

    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("Ask about HR policies, leave, IT tickets, or assets...")

    if query:
        memory = st.session_state[memory_key]

        if memory["first_query"] is None:
            memory["first_query"] = query
        
        memory["last_query"] = query
        if "chat_history" not in memory:
            memory["chat_history"] = []
        
        memory["chat_history"].append(query)
        st.session_state[chat_key].append({
            "role": "user",
            "content": query
        })

        with st.chat_message("user"):
            st.markdown(query)

        if not user:
            response = "Invalid user ID. Please enter a valid user ID in the sidebar."
        else:
            with st.spinner("Processing through LangGraph..."):
                response = run_agent(
                        user_id,
                        query,
                        st.session_state[memory_key]
                    )

        st.session_state[chat_key].append({
            "role": "assistant",
            "content": response
        })

        with st.chat_message("assistant"):
            st.markdown(response)


# ---------------- MANAGER APPROVALS ----------------

elif page == "Manager Approvals":
    st.subheader("Manager Leave Approvals")

    if not user:
        st.error("Please login with a valid user ID.")

    elif user["role"] not in ["Manager", "HR Team", "Admin"]:
        st.warning("Access denied. Only Manager, HR Team, or Admin can access approvals.")

    else:
        # ---------------- LEAVE APPROVALS ----------------
        pending_leaves = get_pending_leave_requests_for_manager(user_id)

        if not pending_leaves:
            st.info("No pending leave requests found.")
        else:
            st.success(f"{len(pending_leaves)} pending leave request(s) found.")

            for leave in pending_leaves:
                leave_id, emp_id, emp_name, leave_type, start_date, end_date, reason, status = leave

                with st.container(border=True):
                    st.markdown(f"### Leave Request #{leave_id}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Employee:** {emp_name} ({emp_id})")
                        st.write(f"**Leave Type:** {leave_type}")
                        st.write(f"**Status:** {status}")

                    with col2:
                        st.write(f"**Start Date:** {start_date}")
                        st.write(f"**End Date:** {end_date}")
                        st.write(f"**Reason:** {reason}")

                    btn1, btn2 = st.columns(2)

                    with btn1:
                        if st.button(f"Approve #{leave_id}", key=f"approve_{leave_id}"):
                            result = approve_leave(user_id, leave_id, "Approved", "Approved from dashboard")
                            st.success(result)
                            st.rerun()

                    with btn2:
                        if st.button(f"Reject #{leave_id}", key=f"reject_{leave_id}"):
                            result = reject_leave(user_id, leave_id, "Rejected from dashboard")
                            st.warning(result)
                            st.rerun()

        # ---------------- ASSET APPROVALS ----------------
        st.divider()
        st.subheader("Manager Asset Approvals")

        assets = get_pending_asset_requests_for_manager(user_id)

        if not assets:
            st.info("No pending asset requests.")
        else:
            st.success(f"{len(assets)} pending asset request(s) found.")

            for asset in assets:
                req_id, emp_id, emp_name, asset_type, reason, status, created_at = asset

                with st.container(border=True):
                    st.markdown(f"### Asset Request #{req_id}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Employee:** {emp_name} ({emp_id})")
                        st.write(f"**Asset:** {asset_type}")
                        st.write(f"**Status:** {status}")

                    with col2:
                        st.write(f"**Reason:** {reason}")
                        st.write(f"**Created At:** {created_at}")

                    btn1, btn2 = st.columns(2)

                    with btn1:
                        if st.button(f"Approve Asset #{req_id}", key=f"mgr_asset_appr_{req_id}"):
                            st.success(approve_asset_manager(user_id, req_id, "Approved"))
                            st.rerun()

                    with btn2:
                        if st.button(f"Reject Asset #{req_id}", key=f"mgr_asset_rej_{req_id}"):
                            st.warning(reject_asset_manager(user_id, req_id))
                            st.rerun()

elif page == "IT Dashboard":
    st.subheader("IT Ticket Dashboard")

    if not user:
        st.error("Please login with a valid user ID.")

    elif user["role"] not in ["IT Team", "Admin"]:
        st.warning("Access denied. Only IT Team or Admin can access IT Dashboard.")

    else:
        # ---------------- INVENTORY ----------------
        st.markdown(get_inventory_status(user_id))

        st.divider()

        # ---------------- TICKETS ----------------
        tickets = get_all_ticket_rows(user_id)

        if not tickets:
            st.info("No tickets found.")
        else:
            st.success(f"{len(tickets)} ticket(s) found.")

            for ticket in tickets:
                ticket_id, emp_id, issue_type, description, priority, status, assigned_engineer, created_at = ticket

                with st.container(border=True):
                    st.markdown(f"### Ticket #{ticket_id}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**User:** {emp_id}")
                        st.write(f"**Issue:** {issue_type}")
                        st.write(f"**Priority:** {priority}")
                        st.write(f"**Status:** {status}")

                    with col2:
                        st.write(f"**Assigned Engineer:** {assigned_engineer}")
                        st.write(f"**Created At:** {created_at}")
                        st.write(f"**Description:** {description}")

                    assign_col, resolve_col = st.columns(2)

                    with assign_col:
                        engineer_id = st.text_input(
                            f"Engineer for Ticket {ticket_id}",
                            value=assigned_engineer or "IT001",
                            key=f"engineer_{ticket_id}"
                        )

                        if st.button(f"Assign Ticket {ticket_id}", key=f"assign_{ticket_id}"):
                            result = assign_ticket(user_id, ticket_id, engineer_id)
                            st.success(result)
                            st.rerun()

                    with resolve_col:
                        if st.button(f"Resolve Ticket {ticket_id}", key=f"resolve_{ticket_id}"):
                            result = resolve_ticket(user_id, ticket_id)
                            st.success(result)
                            st.rerun()

        # ---------------- IT ASSET APPROVALS ----------------
        st.divider()
        st.subheader("IT Asset Approvals")

        assets = get_pending_asset_requests_for_it(user_id)

        if not assets:
            st.info("No asset requests pending IT approval.")
        else:
            st.success(f"{len(assets)} asset request(s) pending IT approval.")

            for asset in assets:
                req_id, emp_id, emp_name, asset_type, reason, status, created_at = asset

                with st.container(border=True):
                    st.markdown(f"### Asset Request #{req_id}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Employee:** {emp_name} ({emp_id})")
                        st.write(f"**Asset:** {asset_type}")
                        st.write(f"**Status:** {status}")

                    with col2:
                        st.write(f"**Reason:** {reason}")
                        st.write(f"**Created At:** {created_at}")

                    btn1, btn2 = st.columns(2)

                    with btn1:
                        if st.button(f"IT Approve Asset #{req_id}", key=f"it_asset_appr_{req_id}"):
                            result = approve_asset_it(user_id, req_id, "Approved")
                            st.success(result)
                            st.rerun()

                    with btn2:
                        if st.button(f"IT Reject Asset #{req_id}", key=f"it_asset_rej_{req_id}"):
                            result = reject_asset_it(user_id, req_id)
                            st.warning(result)
                            st.rerun()        
# ---------------- DEMO PROMPTS ----------------

elif page == "Demo Prompts":
    st.subheader("Demo Prompts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### HR Policy
        ```txt
        What is the notice period policy?
        How many casual leaves are allowed?
        What is the work from home policy?
        ```

        ### HR Leave
        ```txt
        I want sick leave on May 5 because I have fever
        show my leave balance
        show my leave history
        show pending leave requests
        cancel leave 2
        ```
        """)

    with col2:
        st.markdown("""
        ### IT Tickets
        ```txt
        I have an issue in my laptop
        My VPN is not connecting
        my ticket status
        ```

        ### Asset Requests
        ```txt
        request asset Monitor need second screen
        manager approve asset 2
        it approve asset 2
        ```
        """)

    st.info("Use EMP001 as employee, MGR001 as manager, and IT001 as IT team user.")


# ---------------- LOGS ----------------

elif page == "Logs":
    st.subheader("System Logs")

    if user and user["role"] not in ["Admin", "HR Team", "IT Team", "Manager"]:
        st.warning("Access denied. Logs are visible only to authorized roles.")
    else:
        logs = get_logs()

        if not logs:
            st.info("No logs found.")
        else:
            for log in logs:
                user_id_log, query, intent, agent, tool_used, response, response_time, created_at = log

                with st.container(border=True):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**User:** {user_id_log}")
                        st.write(f"**Intent:** {intent}")

                    with col2:
                        st.write(f"**Agent:** {agent}")
                        st.write(f"**Tool:** {tool_used}")

                    with col3:
                        st.write(f"**Response Time:** {response_time} sec")
                        st.caption(f"Time: {created_at}")

                    st.write(f"**Query:** {query}")
                    st.write(f"**Response:** {response}")