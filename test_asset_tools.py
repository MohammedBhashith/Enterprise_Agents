from tools import (
    request_asset,
    check_asset_request_status,
    get_pending_asset_requests_for_manager,
    approve_asset_manager,
    get_pending_asset_requests_for_it,
    approve_asset_it,
)

print("Employee requests asset:")
print(request_asset("EMP001", "Monitor", "Need second screen for development"))

print("\nEmployee checks asset status:")
print(check_asset_request_status("EMP001"))

print("\nManager pending assets:")
print(get_pending_asset_requests_for_manager("MGR001"))

print("\nManager approves asset request 1:")
print(approve_asset_manager("MGR001", 1, "Approved"))

print("\nIT pending assets:")
print(get_pending_asset_requests_for_it("IT001"))

print("\nIT approves asset request 1:")
print(approve_asset_it("IT001", 1, "Approved"))

print("\nEmployee checks asset status again:")
print(check_asset_request_status("EMP001"))