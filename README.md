# CareerBridge — Job Recruitment Portal

A responsive, three-role recruitment portal based on the supplied Tamil project instructions.

## Features
- **Applicant:** self-register, log in, browse/search openings, apply with a PDF/DOC/DOCX resume, track decisions and interview date/time/place.
- **HR:** register with company name, wait for admin approval, publish and close vacancies with department/salary/location, review and download applicant resumes, accept/reject, schedule interviews.
- **Admin:** account created from environment variables; approve/reject HR registration, see users/applications and close/reopen job postings.
- Uploaded resumes are stored in the database rather than ephemeral Render disk.

## Run locally

1. Install Python 3.10+.
2. In this folder, run:

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Set admin credentials and secret:

   **Windows PowerShell**
   ```powershell
   $env:ADMIN_EMAIL="admin@example.com"
   $env:ADMIN_PASSWORD="use-a-long-unique-password"
   $env:SECRET_KEY="use-a-long-random-secret"
   python app.py
   ```

   **macOS/Linux**
   ```bash
   export ADMIN_EMAIL="admin@example.com"
   export ADMIN_PASSWORD="use-a-long-unique-password"
   export SECRET_KEY="use-a-long-random-secret"
   python app.py
   ```
4. Visit http://127.0.0.1:5000. Log in with your configured admin credentials.

Local data uses SQLite (`instance/portal.db`) unless DATABASE_URL is set.

## Publish on Render (public URL)

1. Create a free GitHub account/repository if needed. Extract this ZIP and upload the **contents of the `recruitment_portal` folder** to the root of a new GitHub repository. **Do not upload `.env`, database files, or passwords.**
2. Go to https://dashboard.render.com/ and sign in with GitHub.
3. Choose **New → Blueprint** and connect the GitHub repository.
4. Render reads `render.yaml`, which defines a Python web service and a PostgreSQL database. Review the plan/pricing shown in Render; database free-tier availability and limits can change. If a free database isn't offered, select a suitable paid plan or use an external PostgreSQL provider.
5. Enter a **strong, unique `ADMIN_PASSWORD`** when Render prompts for the secret. The default admin email is `admin@careerbridge.local`; change `ADMIN_EMAIL` in Render environment settings to your own email before first deployment if desired.
6. Click **Apply / Deploy**. Wait for the build and deploy to complete.
7. Open the public `https://careerbridge-portal-....onrender.com` URL shown on your Render dashboard. This URL can be shared with anyone. Register a recruiter account, log in as admin to approve it, and publish jobs.
8. To publish changes, commit/push edits to GitHub; Render automatically redeploys when connected to that branch.

**Alternative manual setup:** Create a Render PostgreSQL database, then a Web Service using this repository. Set build command `pip install -r requirements.txt`, start command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`, and environment variables `DATABASE_URL` (Postgres internal connection URL), `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `RENDER=true`.

## Notes for a public launch

- This is a working academic/demo application, not a fully audited production recruiting platform. Add CSRF protection, email verification, password reset, rate limiting, privacy/retention policies, malware scanning for uploads, and monitoring before using it with real applicant personal data.
- Admin is only created if `ADMIN_PASSWORD` is configured on startup. The password is hashed; changing the environment variable later does **not** reset an existing admin password.
- The database stores uploaded resume bytes; make sure your database has sufficient storage and backups.
- Interview schedules appear in the applicant dashboard; there is no email notification integration.
