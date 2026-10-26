# BrickIT

BrickIT is a Django business-management app for tracking day-to-day operations, sales, and costs. It is designed for a small business team and includes sign-in protected pages.

## Features

- Sign-in protected business overview with production, sales, delivery, inventory, and customer balance summaries
- Production records that update inventory for 4-inch and 6-inch bricks
- Sales records with customer, payment, amount due, delivery status, and sorting/filtering by month, year, and brick type
- Customer profiles with contact information, balances, and sales history
- Delivery status tracking
- Employee records, attendance, and salary payment tracking
- Analytics with year selection, monthly sales charts, and top customers filterable by month
- Electricity, fuel, and miscellaneous cost records, with an interactive monthly comparison chart that reveals exact amounts
- Responsive navigation for desktop and mobile screens

## Technology

- Python 3.13
- Django 6.1
- SQLite for local development
- PostgreSQL when `DATABASE_URL` is configured (as on Render)
- WhiteNoise for serving static files in production

## Run locally

In PowerShell, from the project directory:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and sign in with the superuser credentials you created. The migrations add the default 4-inch and 6-inch brick types with zero starting inventory when they are missing.

## Sign-in and account recovery

Application pages require an authenticated account. Create local accounts with `python manage.py createsuperuser`; on Render, the `bootstrap_admin` command can create the initial administrator from environment variables. SMS one-time-password reset is not included. If the administrator loses access, change the password through Django admin or run `python manage.py changepassword <username>` in an authorized environment connected to the correct database.

## Deploy on Render

The repository includes [`render.yaml`](render.yaml) for a Render Blueprint deployment. It configures a Django web service and PostgreSQL database, collects static files, applies migrations, and runs the app with Gunicorn.

Before the first deployment, add these environment variables to the Render web service in its dashboard:

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOOTSTRAP_ADMIN_USERNAME` | Yes | Username for the initial administrator |
| `BOOTSTRAP_ADMIN_PASSWORD` | Yes | Strong password for the initial administrator |
| `BOOTSTRAP_ADMIN_EMAIL` | No | Email address for the administrator |

The deployment runs `python manage.py bootstrap_admin`. It creates the initial administrator only when both username and password are configured; it does not reset an existing administrator's password. Set these values before the first deploy, and keep them private. Never commit credentials or production secrets to GitHub.

Render supplies the database URL and generated secret key through the Blueprint configuration. The production settings disable debug mode and use the Render hostname for allowed hosts and HTTPS handling.

## Data and backups

Local development uses `db.sqlite3`; a deployed instance uses the PostgreSQL database configured by `DATABASE_URL`. These databases are separate, so local records do not automatically appear on the deployed site. Back up the production database regularly and check the retention and backup options for the database plan you choose.

## License

No license has been specified yet. All rights are reserved by the repository owner unless a license is added.
