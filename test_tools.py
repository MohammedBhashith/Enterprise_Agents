from tools import (
    apply_leave,
    check_leave_status,
    approve_leave,
    create_ticket,
    check_ticket_status,
    request_asset,
    approve_asset_manager,
    approve_asset_it,
)

print(apply_leave("EMP001", "Sick Leave", "2026-05-06", "2026-05-06", "Medical appointment"))
print(check_leave_status("EMP001"))
print(approve_leave("MGR001", 1, "Approved", "Approved by manager"))

print(create_ticket("EMP001", "VPN", "VPN is not connecting", "High"))
print(create_ticket("EMP001", "Laptop", "Laptop is overheating", "Medium"))
print(check_ticket_status("EMP001"))

print(request_asset("EMP001", "Monitor", "Need second monitor for development"))
print(approve_asset_manager("MGR001", 1, "Approved"))
print(approve_asset_it("IT001", 1, "Approved"))