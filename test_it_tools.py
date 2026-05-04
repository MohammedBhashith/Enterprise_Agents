from tools import view_all_tickets, assign_ticket, resolve_ticket, get_inventory_status

print("Employee trying all tickets:")
print(view_all_tickets("EMP001"))

print("\nIT viewing all tickets:")
print(view_all_tickets("IT001"))

print("\nInventory:")
print(get_inventory_status("IT001"))

print("\nAssign ticket:")
print(assign_ticket("IT001", 1, "IT001"))

print("\nResolve ticket:")
print(resolve_ticket("IT001", 1))