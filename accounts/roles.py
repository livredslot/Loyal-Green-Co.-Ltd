"""
The five roles from the design document, and the special permissions each one gets.

Roles are Django groups, created by core/migrations/0002_roles.py. Model
permissions (add/change/view) are given to groups as each module is built.
"""

DIRECTOR = "Director"
SALES_MANAGER = "Sales Manager"
PRODUCTION_LEAD = "Production Lead"
WAREHOUSE_LEAD = "Warehouse Lead"
ACCOUNTANT = "Accountant"

ROLES = [DIRECTOR, SALES_MANAGER, PRODUCTION_LEAD, WAREHOUSE_LEAD, ACCOUNTANT]

# Codenames of permissions defined on core.CompanyProfile
VIEW_COSTS = "view_costs"
APPROVE = "approve_actions"
EDIT_COMPANY = "change_companyprofile"

ROLE_PERMISSIONS = {
    DIRECTOR: [VIEW_COSTS, APPROVE, EDIT_COMPANY],
    SALES_MANAGER: [VIEW_COSTS],
    PRODUCTION_LEAD: [VIEW_COSTS],
    WAREHOUSE_LEAD: [],
    ACCOUNTANT: [VIEW_COSTS],
}
