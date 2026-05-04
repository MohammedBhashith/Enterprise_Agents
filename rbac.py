from database import get_user


EMPLOYEE = "Employee"
MANAGER = "Manager"
HR_TEAM = "HR Team"
IT_TEAM = "IT Team"
ADMIN = "Admin"


def get_role(user_id: str):
    user = get_user(user_id)
    if not user:
        return None
    return user["role"]


def is_valid_user(user_id: str) -> bool:
    return get_user(user_id) is not None


def is_admin(user_id: str) -> bool:
    return get_role(user_id) == ADMIN


def is_manager(user_id: str) -> bool:
    return get_role(user_id) == MANAGER


def is_hr(user_id: str) -> bool:
    return get_role(user_id) == HR_TEAM


def is_it(user_id: str) -> bool:
    return get_role(user_id) == IT_TEAM


def can_ask_policy(user_id: str) -> bool:
    return get_role(user_id) in [EMPLOYEE, MANAGER, HR_TEAM, IT_TEAM, ADMIN]


def can_apply_leave(user_id: str) -> bool:
    return get_role(user_id) in [EMPLOYEE, MANAGER, HR_TEAM, IT_TEAM, ADMIN]


def can_cancel_leave(user_id: str, leave_user_id: str) -> bool:
    role = get_role(user_id)
    return user_id == leave_user_id or role in [HR_TEAM, ADMIN]


def can_view_leave(user_id: str, leave_user_id: str) -> bool:
    role = get_role(user_id)
    return user_id == leave_user_id or role in [MANAGER, HR_TEAM, ADMIN]


def can_approve_leave(user_id: str) -> bool:
    return get_role(user_id) in [MANAGER, HR_TEAM, ADMIN]


def can_raise_ticket(user_id: str) -> bool:
    return get_role(user_id) in [EMPLOYEE, MANAGER, HR_TEAM, IT_TEAM, ADMIN]


def can_view_ticket(user_id: str, ticket_user_id: str) -> bool:
    role = get_role(user_id)
    return user_id == ticket_user_id or role in [IT_TEAM, ADMIN]


def can_manage_ticket(user_id: str) -> bool:
    return get_role(user_id) in [IT_TEAM, ADMIN]


def can_request_asset(user_id: str) -> bool:
    return get_role(user_id) in [EMPLOYEE, MANAGER, HR_TEAM, IT_TEAM, ADMIN]


def can_approve_asset_as_manager(user_id: str) -> bool:
    return get_role(user_id) in [MANAGER, ADMIN]


def can_approve_asset_as_it(user_id: str) -> bool:
    return get_role(user_id) in [IT_TEAM, ADMIN]


def can_view_logs(user_id: str) -> bool:
    return get_role(user_id) in [ADMIN, HR_TEAM, IT_TEAM]


def can_access_document(user_id: str, document_department: str) -> bool:
    role = get_role(user_id)

    if role == ADMIN:
        return True

    if document_department == "HR":
        return role in [EMPLOYEE, MANAGER, HR_TEAM]

    if document_department == "IT":
        return role in [EMPLOYEE, MANAGER, IT_TEAM]

    return False


def validate_user_or_message(user_id: str):
    if not is_valid_user(user_id):
        return False, "Invalid user ID. Please enter a valid employee ID."
    return True, "User validated successfully."