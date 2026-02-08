# Dependency Management

## Scope

This document defines how dependencies are pinned, audited, and updated for the Sungrip Solar Chatbot.

## Policy

- Use pinned versions for reproducible builds.
- Keep dependency updates small and testable.
- Run security audits before releases.
- Do not commit secrets or credentials in dependency files.

## Backend (Python)

### Pinning Strategy

- [backend/requirements.txt](backend/requirements.txt) uses exact versions (pinned).
- For production, generate a locked file from a clean environment and store it in your deployment artifacts, not in git.

### Generate a Locked File (Optional)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip freeze > requirements-locked.txt
```

### Security Audit

```bash
cd backend
pip install pip-audit
pip-audit -r requirements.txt
```

## Frontend (Node.js)

If/when the frontend is implemented:

```bash
cd frontend
npm audit
npm audit fix
```

## Update Cadence

- Weekly: run security audits.
- Monthly: review dependency updates.
- Quarterly: apply non-urgent updates after testing.
- As needed: apply emergency security patches.

## Change Checklist

- Update dependency file(s).
- Run security audit(s).
- Run tests relevant to the change.
- Document changes if they affect deployment or security.
