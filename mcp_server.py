from fastmcp import FastMCP

from tools import (
    apply_leave,
    get_leave_balance,
    check_leave_status,
    create_ticket,
    check_ticket_status,
    request_asset,
    check_asset_request_status,
    get_inventory_status,
)

mcp = FastMCP("Enterprise AI Copilot MCP Server")


@mcp.tool
def mcp_apply_leave(
    user_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str
) -> str:
    """Apply leave for an employee."""
    return apply_leave(user_id, leave_type, start_date, end_date, reason)


@mcp.tool
def mcp_get_leave_balance(user_id: str) -> str:
    """Get leave balance for a user."""
    return get_leave_balance(user_id)


@mcp.tool
def mcp_check_leave_status(user_id: str) -> str:
    """Check leave request status for a user."""
    return check_leave_status(user_id)


@mcp.tool
def mcp_create_ticket(
    user_id: str,
    issue_type: str,
    description: str,
    priority: str = "Medium"
) -> str:
    """Create an IT support ticket."""
    return create_ticket(user_id, issue_type, description, priority)


@mcp.tool
def mcp_check_ticket_status(user_id: str) -> str:
    """Check IT ticket status for a user."""
    return check_ticket_status(user_id)


@mcp.tool
def mcp_request_asset(user_id: str, asset_type: str, reason: str) -> str:
    """Request an IT asset."""
    return request_asset(user_id, asset_type, reason)


@mcp.tool
def mcp_check_asset_request_status(user_id: str) -> str:
    """Check asset request status for a user."""
    return check_asset_request_status(user_id)


@mcp.tool
def mcp_inventory_status(user_id: str) -> str:
    """Check inventory status."""
    return get_inventory_status(user_id)


if __name__ == "__main__":
    mcp.run()