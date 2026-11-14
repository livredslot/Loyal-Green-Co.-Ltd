# Loyal Green factory system – project notes

Custom factory/inventory/sales system for Loyal Green Co., Ltd (Myanmar, paper cups/plates/bowls + repacked plastics). Design: https://claude.ai/artifact/9FPmyhBvKo9iQAzzqx8FkP. Team data requests: `../Pending Actions - Information Needed.docx`; samples in `../Samples`.

## Commands (PowerShell; Git Bash is broken on this laptop)

- Python: `$env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe` (venv kept outside OneDrive on purpose)
- Tests: `<python> manage.py test`
- Dev server: `<python> manage.py runserver` → http://127.0.0.1:8000
- No Docker on the laptop (company machine). Docker is only for the AWS server (`docker-compose.yml`, `Caddyfile`, `.env.example`).

## Rules for this codebase

- Keep it simple: few screens, server-rendered Django templates, no front-end framework. Must work on a phone.
- Screens in English. Customer documents print English or English + Myanmar (Unicode, Myanmar Text / Pyidaungsu font).
- Money is kyats with no decimals. Foreign purchases keep original amount + exchange rate.
- Stock moves only through documents; every movement writes the stock ledger. Valuation: weighted average; import costs added as landed cost; factory overhead by machine hours.
- Nothing is deleted once posted; mistakes are reversed. Models that matter get `HistoricalRecords()` (django-simple-history) for the audit trail.
- Roles are Django groups (`accounts/roles.py`): Director, Sales Manager, Production Lead, Warehouse Lead, Accountant. `core.view_costs` hides costs/profit; `core.approve_actions` for approvals. Grant model permissions to groups in a migration when a module is added.
- Commercial Tax 5% on all invoices (`CompanyProfile.commercial_tax_rate`). Prices are stored before tax.

## Build order (version 1)

1. Items, units, recipes, locations, users
2. Purchasing, goods received, import costs, stock, reorder alerts
3. Production and repacking
4. Sales orders, delivery orders, invoices, payments, credit alerts
5. Costing, reports, dashboard
