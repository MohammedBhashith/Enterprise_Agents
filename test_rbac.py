from rbac import (
    get_role,
    can_apply_leave,
    can_approve_leave,
    can_manage_ticket,
    can_access_document,
)

users = ["EMP001", "MGR001", "HR001", "IT001", "ADMIN001", "WRONG001"]

for user_id in users:
    print("User:", user_id)
    print("Role:", get_role(user_id))
    print("Can apply leave:", can_apply_leave(user_id))
    print("Can approve leave:", can_approve_leave(user_id))
    print("Can manage ticket:", can_manage_ticket(user_id))
    print("Can access HR doc:", can_access_document(user_id, "HR"))
    print("Can access IT doc:", can_access_document(user_id, "IT"))
    print("-" * 40)