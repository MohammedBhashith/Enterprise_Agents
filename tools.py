import sqlite3
from datetime import datetime, date
from database import get_connection, get_user
from email_service import send_email_via_power_automate
from rbac import (
    can_apply_leave,
    can_approve_leave,
    can_raise_ticket,
    can_manage_ticket,
    can_request_asset,
    can_approve_asset_as_manager,
    can_approve_asset_as_it,
)

HOLIDAYS = ["2026-05-01", "2026-08-15", "2026-10-02"]


def calculate_days(start_date: str, end_date: str) -> int:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return (end - start).days + 1


def has_overlap_leave(user_id: str, start_date: str, end_date: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM leave_requests
        WHERE user_id = ?
        AND status IN ('Pending', 'Approved')
        AND NOT (end_date < ? OR start_date > ?)
    """, (user_id, start_date, end_date))

    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def apply_leave(user_id: str, leave_type: str, start_date: str, end_date: str, reason: str):
    if not can_apply_leave(user_id):
        return "Access denied. You are not allowed to apply leave."

    user = get_user(user_id)
    if not user:
        return "Invalid user ID."

    try:
        leave_days = calculate_days(start_date, end_date)
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    if leave_days <= 0:
        return "Invalid leave dates."

    if start_date in HOLIDAYS or end_date in HOLIDAYS:
        return "Leave rejected because selected date includes a company holiday."

    if has_overlap_leave(user_id, start_date, end_date):
     return "Leave rejected because you already have a leave request for these dates."

    balance_ok, balance_message = has_enough_leave_balance(user_id, leave_type, leave_days)
    if not balance_ok:
       return balance_message

    manager_id = user["manager_id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO leave_requests
        (user_id, leave_type, start_date, end_date, reason, status, manager_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        leave_type,
        start_date,
        end_date,
        reason,
        "Pending",
        manager_id,
        datetime.now().isoformat()
    ))

    leave_id = cur.lastrowid
    manager_email = None
    if manager_id:
        manager = get_user(manager_id)
        if manager:
            manager_email = manager["email"]

    if manager_id:
        cur.execute("""
            INSERT INTO approvals
            (request_type, request_id, approver_id, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "Leave",
            leave_id,
            manager_id,
            "Pending",
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    email_status = ""
    if manager_email:
        email_status = send_email_via_power_automate(
            to_email=manager_email,
            subject=f"Leave Approval Request - {user['name']}",
            body=(
                f"Dear Manager,\n\n"
                f"{user['name']} ({user_id}) has requested {leave_type}.\n\n"
                f"Dates: {start_date} to {end_date}\n"
                f"Reason: {reason}\n"
                f"Leave ID: {leave_id}\n\n"
                f"Please review and approve/reject the request."
            )
        )

    return (
        f"Leave request submitted successfully. Leave ID: {leave_id}. "
        f"Status: Pending manager approval.\n\n"
        f"{email_status}"
    )

   # return f"Leave request submitted successfully. Leave ID: {leave_id}. Status: Pending manager approval."


def check_leave_status(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT leave_id, leave_type, start_date, end_date, status
        FROM leave_requests
        WHERE user_id = ?
        ORDER BY leave_id DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No leave requests found."

    result = "Your leave requests:\n\n"
    for row in rows:
        result += f"Leave ID {row[0]} | {row[1]} | {row[2]} to {row[3]} | Status: {row[4]}\n\n"

    return result


def approve_leave(approver_id: str, leave_id: int, decision: str, comments: str = ""):
    if not can_approve_leave(approver_id):
        return "Access denied. Only managers, HR, or admins can approve leave."

    decision = decision.capitalize()
    if decision not in ["Approved", "Rejected"]:
        return "Decision must be Approved or Rejected."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT leave_id FROM leave_requests WHERE leave_id = ?", (leave_id,))
    if not cur.fetchone():
        conn.close()
        return "Leave request not found."
    
    cur.execute("""
        SELECT lr.user_id, u.name, u.email, lr.leave_type, lr.start_date, lr.end_date
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.leave_id = ?
    """, (leave_id,))

    leave_info = cur.fetchone()

    cur.execute("""
        UPDATE leave_requests
        SET status = ?
        WHERE leave_id = ?
    """, (decision, leave_id))

    if decision == "Approved":
        cur.execute("""
            SELECT user_id, leave_type, start_date, end_date
            FROM leave_requests
            WHERE leave_id = ?
        """, (leave_id,))

        leave_row = cur.fetchone()

        if leave_row:
            leave_user_id, leave_type, start_date, end_date = leave_row
            leave_days = calculate_days(start_date, end_date)

            if "casual" in leave_type.lower():
                cur.execute("""
                    UPDATE leave_balances
                    SET casual_balance = casual_balance - ?
                    WHERE user_id = ?
                """, (leave_days, leave_user_id))

            elif "sick" in leave_type.lower():
                cur.execute("""
                    UPDATE leave_balances
                    SET sick_balance = sick_balance - ?
                    WHERE user_id = ?
                """, (leave_days, leave_user_id))

    cur.execute("""
        UPDATE approvals
        SET status = ?, comments = ?, updated_at = ?
        WHERE request_type = 'Leave' AND request_id = ?
    """, (decision, comments, datetime.now().isoformat(), leave_id))

    conn.commit()
    conn.close()

    email_status = ""
    if leave_info:
        leave_user_id, emp_name, emp_email, leave_type, start_date, end_date = leave_info

        email_status = send_email_via_power_automate(
            to_email=emp_email,
            subject=f"Leave Request {decision} - Leave ID {leave_id}",
            body=(
                f"Dear {emp_name},\n\n"
                f"Your leave request has been {decision.lower()}.\n\n"
                f"Leave ID: {leave_id}\n"
                f"Leave Type: {leave_type}\n"
                f"Dates: {start_date} to {end_date}\n"
                f"Comments: {comments if comments else 'No comments'}\n\n"
                f"Regards,\nHR System"
            )
        )

    return f"Leave ID {leave_id} has been {decision.lower()}.\n\n{email_status}"

    #return f"Leave ID {leave_id} has been {decision.lower()}."


def cancel_leave(user_id: str, leave_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, status FROM leave_requests
        WHERE leave_id = ?
    """, (leave_id,))

    row = cur.fetchone()

    if not row:
        conn.close()
        return "Leave request not found."

    leave_user_id, status = row

    if leave_user_id != user_id:
        conn.close()
        return "Access denied. You can cancel only your own leave request."

    if status == "Approved":
        conn.close()
        return "Approved leave cannot be cancelled from this tool. Please contact HR."

    cur.execute("""
        UPDATE leave_requests
        SET status = 'Cancelled'
        WHERE leave_id = ?
    """, (leave_id,))

    conn.commit()
    conn.close()

    return f"Leave ID {leave_id} cancelled successfully."


def check_known_outage(issue_type: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT description FROM known_outages
        WHERE LOWER(issue_type) LIKE LOWER(?)
        AND status = 'Active'
    """, (f"%{issue_type}%",))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def check_maintenance(issue_type: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT system_name, description, start_time, end_time
        FROM maintenance_schedule
        WHERE LOWER(system_name) LIKE LOWER(?)
        AND status = 'Scheduled'
    """, (f"%{issue_type}%",))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return f"{row[0]} maintenance: {row[1]} from {row[2]} to {row[3]}."


def has_duplicate_ticket(user_id: str, issue_type: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ticket_id FROM it_tickets
        WHERE user_id = ?
        AND LOWER(issue_type) = LOWER(?)
        AND status IN ('Open', 'In Progress')
    """, (user_id, issue_type))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def create_ticket(user_id: str, issue_type: str, description: str, priority: str = "Medium"):
    if not can_raise_ticket(user_id):
        return "Access denied. You are not allowed to raise IT tickets."

    if not get_user(user_id):
        return "Invalid user ID."

    outage = check_known_outage(issue_type)
    if outage:
        return f"Known outage detected: {outage}. Ticket not created to avoid duplication."

    maintenance = check_maintenance(issue_type)
    if maintenance:
        return f"Planned maintenance found: {maintenance}. Ticket not created."

    duplicate_ticket = has_duplicate_ticket(user_id, issue_type)
    if duplicate_ticket:
        return f"You already have an open ticket for this issue. Ticket ID: {duplicate_ticket}."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO it_tickets
        (user_id, issue_type, description, priority, status, assigned_engineer, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        issue_type,
        description,
        priority,
        "Open",
        "IT001",
        datetime.now().isoformat()
    ))

    ticket_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    user = get_user(user_id)
    
    email_status = send_email_via_power_automate(
        to_email=user["email"],
        subject=f"IT Ticket Created - Ticket ID {ticket_id}",
        body=(
            f"Dear {user['name']},\n\n"
            f"Your IT ticket has been created successfully.\n\n"
            f"Ticket ID: {ticket_id}\n"
            f"Issue Type: {issue_type}\n"
            f"Priority: {priority}\n"
            f"Status: Open\n"
            f"Assigned Engineer: IT001\n\n"
            f"Regards,\nIT Support System"
        )
    )
    
    return (
        f"IT ticket created successfully. Ticket ID: {ticket_id}. Status: Open.\n\n"
        f"{email_status}"
    )


def check_ticket_status(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ticket_id, issue_type, priority, status, assigned_engineer
        FROM it_tickets
        WHERE user_id = ?
        ORDER BY ticket_id DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No IT tickets found."

    result = "### Your IT Tickets\n\n"

    for row in rows:
        result += (
            f"#### Ticket ID {row[0]}\n"
            f"- **Issue:** {row[1]}\n"
            f"- **Priority:** {row[2]}\n"
            f"- **Status:** {row[3]}\n"
            f"- **Assigned Engineer:** {row[4]}\n\n"
        )

    return result


def resolve_ticket(it_user_id: str, ticket_id: int):
    if not can_manage_ticket(it_user_id):
        return "Access denied. Only IT Team or Admin can resolve tickets."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.ticket_id, t.user_id, t.issue_type, u.name, u.email
        FROM it_tickets t
        JOIN users u ON t.user_id = u.user_id
        WHERE t.ticket_id = ?
    """, (ticket_id,))

    ticket_info = cur.fetchone()

    if not ticket_info:
        conn.close()
        return "Ticket not found."

    cur.execute("""
        UPDATE it_tickets
        SET status = 'Resolved'
        WHERE ticket_id = ?
    """, (ticket_id,))

    conn.commit()
    conn.close()

    _, emp_id, issue_type, emp_name, emp_email = ticket_info

    email_status = send_email_via_power_automate(
        to_email=emp_email,
        subject=f"IT Ticket Resolved - Ticket ID {ticket_id}",
        body=(
            f"Dear {emp_name},\n\n"
            f"Your IT ticket has been resolved.\n\n"
            f"Ticket ID: {ticket_id}\n"
            f"Issue Type: {issue_type}\n"
            f"Status: Resolved\n\n"
            f"Regards,\nIT Support Team"
        )
    )

    return f"Ticket ID {ticket_id} resolved successfully.\n\n{email_status}"

def request_asset(user_id: str, asset_type: str, reason: str):
    if not can_request_asset(user_id):
        return "Access denied. You are not allowed to request assets."

    if not get_user(user_id):
        return "Invalid user ID."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT request_id FROM asset_requests
        WHERE user_id = ?
        AND asset_type = ?
        AND status NOT IN ('Rejected', 'Fulfilled')
    """, (user_id, asset_type))

    duplicate = cur.fetchone()
    if duplicate:
        conn.close()
        return f"You already have an active asset request. Request ID: {duplicate[0]}."

    cur.execute("""
        INSERT INTO asset_requests
        (user_id, asset_type, reason, status, manager_status, it_status, inventory_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        asset_type,
        reason,
        "Manager Pending",
        "Pending",
        "Pending",
        "Pending",
        datetime.now().isoformat()
    ))

    request_id = cur.lastrowid

    user = get_user(user_id)
    manager_id = user["manager_id"]

    if manager_id:
        cur.execute("""
            INSERT INTO approvals
            (request_type, request_id, approver_id, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "Asset",
            request_id,
            manager_id,
            "Pending",
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    
    manager_email = None
    if manager_id:
        manager = get_user(manager_id)
        if manager:
            manager_email = manager["email"]
    
    email_status = ""
    if manager_email:
        email_status = send_email_via_power_automate(
            to_email=manager_email,
            subject=f"Asset Approval Request - Request ID {request_id}",
            body=(
                f"Dear Manager,\n\n"
                f"{user['name']} ({user_id}) has requested an asset.\n\n"
                f"Request ID: {request_id}\n"
                f"Asset: {asset_type}\n"
                f"Reason: {reason}\n"
                f"Status: Manager Pending\n\n"
                f"Please approve or reject this request."
            )
        )
    
    return (
        f"Asset request submitted successfully. Request ID: {request_id}. Status: Manager Pending.\n\n"
        f"{email_status}"
    )

def approve_asset_manager(manager_id: str, request_id: int, decision: str):
    if not can_approve_asset_as_manager(manager_id):
        return "Access denied. Only Manager or Admin can approve this step."

    decision = decision.capitalize()
    if decision not in ["Approved", "Rejected"]:
        return "Decision must be Approved or Rejected."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ar.user_id, u.name, u.email, ar.asset_type
        FROM asset_requests ar
        JOIN users u ON ar.user_id = u.user_id
        WHERE ar.request_id = ?
    """, (request_id,))

    asset_info = cur.fetchone()

    if not asset_info:
        conn.close()
        return "Asset request not found."

    emp_id, emp_name, emp_email, asset_type = asset_info

    status = "Rejected" if decision == "Rejected" else "IT Pending"

    cur.execute("""
        UPDATE asset_requests
        SET manager_status = ?, status = ?
        WHERE request_id = ?
    """, (decision, status, request_id))

    conn.commit()
    conn.close()

    email_status = send_email_via_power_automate(
        to_email=emp_email,
        subject=f"Asset Request {decision} - Request ID {request_id}",
        body=(
            f"Dear {emp_name},\n\n"
            f"Your asset request has been {decision.lower()} by the manager.\n\n"
            f"Request ID: {request_id}\n"
            f"Asset: {asset_type}\n"
            f"Current Status: {status}\n\n"
            f"Regards,\nAsset Management System"
        )
    )

    return f"Asset request {request_id} manager step: {decision}.\n\n{email_status}"


def approve_asset_it(it_user_id: str, request_id: int, decision: str):
    if not can_approve_asset_as_it(it_user_id):
        return "Access denied. Only IT Team or Admin can approve this step."

    decision = decision.capitalize()
    if decision not in ["Approved", "Rejected"]:
        return "Decision must be Approved or Rejected."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ar.user_id, u.name, u.email, ar.asset_type
        FROM asset_requests ar
        JOIN users u ON ar.user_id = u.user_id
        WHERE ar.request_id = ?
    """, (request_id,))

    asset_info = cur.fetchone()

    if not asset_info:
        conn.close()
        return "Asset request not found."

    emp_id, emp_name, emp_email, asset_type = asset_info

    if decision == "Rejected":
        cur.execute("""
            UPDATE asset_requests
            SET it_status = 'Rejected', status = 'Rejected'
            WHERE request_id = ?
        """, (request_id,))

        conn.commit()
        conn.close()

        email_status = send_email_via_power_automate(
            to_email=emp_email,
            subject=f"Asset Request Rejected by IT - Request ID {request_id}",
            body=(
                f"Dear {emp_name},\n\n"
                f"Your asset request has been rejected by IT.\n\n"
                f"Request ID: {request_id}\n"
                f"Asset: {asset_type}\n"
                f"Status: Rejected\n\n"
                f"Regards,\nIT Asset Team"
            )
        )

        return f"Asset request {request_id} rejected by IT.\n\n{email_status}"

    cur.execute("""
        SELECT available_count FROM inventory
        WHERE asset_type = ?
    """, (asset_type,))

    inventory = cur.fetchone()

    if not inventory or inventory[0] <= 0:
        cur.execute("""
            UPDATE asset_requests
            SET it_status = 'Approved',
                inventory_status = 'Unavailable',
                status = 'Inventory Unavailable'
            WHERE request_id = ?
        """, (request_id,))

        conn.commit()
        conn.close()

        email_status = send_email_via_power_automate(
            to_email=emp_email,
            subject=f"Asset Inventory Unavailable - Request ID {request_id}",
            body=(
                f"Dear {emp_name},\n\n"
                f"Your asset request was approved by IT, but inventory is currently unavailable.\n\n"
                f"Request ID: {request_id}\n"
                f"Asset: {asset_type}\n"
                f"Status: Inventory Unavailable\n\n"
                f"Regards,\nIT Asset Team"
            )
        )

        return f"Asset request {request_id} approved by IT, but inventory is unavailable.\n\n{email_status}"

    cur.execute("""
        UPDATE inventory
        SET available_count = available_count - 1
        WHERE asset_type = ?
    """, (asset_type,))

    cur.execute("""
        UPDATE asset_requests
        SET it_status = 'Approved',
            inventory_status = 'Available',
            status = 'Fulfilled'
        WHERE request_id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    email_status = send_email_via_power_automate(
        to_email=emp_email,
        subject=f"Asset Request Fulfilled - Request ID {request_id}",
        body=(
            f"Dear {emp_name},\n\n"
            f"Your asset request has been approved by IT and fulfilled.\n\n"
            f"Request ID: {request_id}\n"
            f"Asset: {asset_type}\n"
            f"Status: Fulfilled\n\n"
            f"Regards,\nIT Asset Team"
        )
    )

    return f"Asset request {request_id} approved by IT and fulfilled successfully.\n\n{email_status}"

def get_leave_balance(user_id: str):
    if not get_user(user_id):
        return "Invalid user ID."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT casual_balance, sick_balance
        FROM leave_balances
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return "Leave balance not found for this user."

    return (
    "### Leave Balance\n\n"
    f"- Casual Leave: **{row[0]} days**\n"
    f"- Sick Leave: **{row[1]} days**"
)


def view_leave_history(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT leave_id, leave_type, start_date, end_date, reason, status
        FROM leave_requests
        WHERE user_id = ?
        ORDER BY leave_id DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No leave history found."

    result = "### Leave History\n\n"
    for row in rows:
        result += (
            f"- **ID {row[0]}** | {row[1]} | {row[2]} → {row[3]} | "
            f"{row[5]}\n"
        )

    return result


def view_pending_leaves(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT leave_id, leave_type, start_date, end_date, reason, status
        FROM leave_requests
        WHERE user_id = ?
        AND status = 'Pending'
        ORDER BY leave_id DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No pending leave requests found."

    result = "### Pending Leave Requests\n\n"
    for row in rows:
        result += (
            f"Leave ID {row[0]} | Type: {row[1]} | "
            f"{row[2]} to {row[3]} | Reason: {row[4]} | Status: {row[5]}\n\n"
        )

    return result

def get_pending_leave_requests_for_manager(manager_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT lr.leave_id, lr.user_id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.reason, lr.status
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.manager_id = ?
        AND lr.status = 'Pending'
        ORDER BY lr.leave_id DESC
    """, (manager_id,))

    rows = cur.fetchall()
    conn.close()

    return rows


def reject_leave(approver_id: str, leave_id: int, comments: str = ""):
    return approve_leave(approver_id, leave_id, "Rejected", comments)


def has_enough_leave_balance(user_id: str, leave_type: str, leave_days: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT casual_balance, sick_balance
        FROM leave_balances
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Leave balance not found."

    casual_balance, sick_balance = row

    if "casual" in leave_type.lower():
        if casual_balance < leave_days:
            return False, f"Insufficient casual leave balance. Available: {casual_balance} days."
        return True, "Sufficient casual leave balance."

    if "sick" in leave_type.lower():
        if sick_balance < leave_days:
            return False, f"Insufficient sick leave balance. Available: {sick_balance} days."
        return True, "Sufficient sick leave balance."

    return True, "Leave type does not require balance validation."

def view_all_tickets(it_user_id: str):
    if not can_manage_ticket(it_user_id):
        return "Access denied. Only IT Team or Admin can view all tickets."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ticket_id, user_id, issue_type, description, priority, status, assigned_engineer, created_at
        FROM it_tickets
        ORDER BY ticket_id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No IT tickets found."

    result = "### All IT Tickets\n\n"

    for row in rows:
        result += (
            f"#### Ticket ID {row[0]}\n"
            f"- **User:** {row[1]}\n"
            f"- **Issue:** {row[2]}\n"
            f"- **Priority:** {row[4]}\n"
            f"- **Status:** {row[5]}\n"
            f"- **Assigned Engineer:** {row[6]}\n\n"
        )

    return result


def assign_ticket(it_user_id: str, ticket_id: int, engineer_id: str):
    if not can_manage_ticket(it_user_id):
        return "Access denied. Only IT Team or Admin can assign tickets."

    engineer = get_user(engineer_id)

    if not engineer:
        return "Invalid engineer ID."

    if engineer["role"] not in ["IT Team", "Admin"]:
        return "Ticket can be assigned only to an IT Team member or Admin."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT ticket_id FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
    if not cur.fetchone():
        conn.close()
        return "Ticket not found."

    cur.execute("""
        UPDATE it_tickets
        SET assigned_engineer = ?, status = 'In Progress'
        WHERE ticket_id = ?
    """, (engineer_id, ticket_id))

    conn.commit()
    conn.close()

    return f"Ticket ID {ticket_id} assigned to {engineer_id} and marked as In Progress."


def get_inventory_status(user_id: str):
    user = get_user(user_id)

    if not user:
        return "Invalid user ID."

    if user["role"] not in ["IT Team", "Admin", "Manager"]:
        return "Access denied. Only IT Team, Admin, or Manager can view inventory."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT asset_type, available_count
        FROM inventory
        ORDER BY asset_type
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No inventory records found."

    result = "### Inventory Status\n\n"
    for asset_type, count in rows:
        result += f"- **{asset_type}:** {count} available\n"

    return result


def get_all_ticket_rows(it_user_id: str):
    if not can_manage_ticket(it_user_id):
        return []

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ticket_id, user_id, issue_type, description, priority, status, assigned_engineer, created_at
        FROM it_tickets
        ORDER BY ticket_id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def check_asset_request_status(user_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT request_id, asset_type, reason, status, manager_status, it_status, inventory_status, created_at
        FROM asset_requests
        WHERE user_id = ?
        ORDER BY request_id DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No asset requests found."

    result = "### Your Asset Requests\n\n"

    for row in rows:
        result += (
            f"#### Request ID {row[0]}\n"
            f"- **Asset:** {row[1]}\n"
            f"- **Reason:** {row[2]}\n"
            f"- **Overall Status:** {row[3]}\n"
            f"- **Manager Status:** {row[4]}\n"
            f"- **IT Status:** {row[5]}\n"
            f"- **Inventory Status:** {row[6]}\n"
            f"- **Created At:** {row[7]}\n\n"
        )

    return result


def get_pending_asset_requests_for_manager(manager_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ar.request_id, ar.user_id, u.name, ar.asset_type, ar.reason, ar.status, ar.created_at
        FROM asset_requests ar
        JOIN users u ON ar.user_id = u.user_id
        WHERE u.manager_id = ?
        AND ar.manager_status = 'Pending'
        ORDER BY ar.request_id DESC
    """, (manager_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_pending_asset_requests_for_it(it_user_id: str):
    if not can_approve_asset_as_it(it_user_id):
        return []

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ar.request_id, ar.user_id, u.name, ar.asset_type, ar.reason, ar.status, ar.created_at
        FROM asset_requests ar
        JOIN users u ON ar.user_id = u.user_id
        WHERE ar.manager_status = 'Approved'
        AND ar.it_status = 'Pending'
        ORDER BY ar.request_id DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def reject_asset_manager(manager_id: str, request_id: int):
    return approve_asset_manager(manager_id, request_id, "Rejected")


def reject_asset_it(it_user_id: str, request_id: int):
    return approve_asset_it(it_user_id, request_id, "Rejected")


def get_pending_leave_requests_for_approver(user_id: str):
    user = get_user(user_id)

    if not user:
        return []

    conn = get_connection()
    cur = conn.cursor()

    if user["role"] in ["HR Team", "Admin"]:
        cur.execute("""
            SELECT lr.leave_id, lr.user_id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.reason, lr.status
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.user_id
            WHERE lr.status = 'Pending'
            ORDER BY lr.leave_id DESC
        """)
    else:
        cur.execute("""
            SELECT lr.leave_id, lr.user_id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.reason, lr.status
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.user_id
            WHERE lr.manager_id = ?
            AND lr.status = 'Pending'
            ORDER BY lr.leave_id DESC
        """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_pending_asset_requests_for_approver(user_id: str):
    user = get_user(user_id)

    if not user:
        return []

    conn = get_connection()
    cur = conn.cursor()

    if user["role"] in ["HR Team", "Admin"]:
        cur.execute("""
            SELECT ar.request_id, ar.user_id, u.name, ar.asset_type, ar.reason, ar.status, ar.created_at
            FROM asset_requests ar
            JOIN users u ON ar.user_id = u.user_id
            WHERE ar.manager_status = 'Pending'
            ORDER BY ar.request_id DESC
        """)
    else:
        cur.execute("""
            SELECT ar.request_id, ar.user_id, u.name, ar.asset_type, ar.reason, ar.status, ar.created_at
            FROM asset_requests ar
            JOIN users u ON ar.user_id = u.user_id
            WHERE u.manager_id = ?
            AND ar.manager_status = 'Pending'
            ORDER BY ar.request_id DESC
        """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    return rows