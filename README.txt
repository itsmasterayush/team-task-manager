Team Task Manager (Full-Stack)

Description:
A full-stack web application where users can create projects, assign tasks, and track progress with role-based access control (Admin/Member).

Features:
- Authentication (Signup/Login with JWT)
- Project & Team Management
- Task creation, assignment, and status tracking (TODO, IN_PROGRESS, DONE)
- Dashboard overview (Total, To Do, In Progress, Done, Overdue)
- Role-based Access Control (Admin vs. Member views and permissions)

Technology Stack:
- Backend: Python (Flask), SQLAlchemy, SQLite (local) / PostgreSQL (production), PyJWT
- Frontend: Vanilla HTML, CSS (Modern Premium UI), JavaScript (SPA)

Setup & Deployment:
1. GitHub Repository: Push this code to a new GitHub repository.
2. Railway Deployment:
   - Connect the GitHub repository to Railway.
   - Railway will automatically detect the Python environment via `requirements.txt` and `Procfile`.
   - Provision a PostgreSQL database in Railway and link it to the backend service. The app will automatically use the `DATABASE_URL` environment variable.

Local Development:
1. Install Python 3.11+.
2. Run `pip install -r backend/requirements.txt`
3. Run `python backend/app.py`
4. Open `frontend/index.html` in your web browser.

Default Admin Account (Local):
Email: admin@test.com
Password: admin123
