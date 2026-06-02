# Hire-Lens

## Security Setup

Create a local `.env` file (do not commit it) and define at least:

- `SECRET_KEY` (minimum 32 characters)
- `JWT_SECRET_KEY` (minimum 32 characters and different from `SECRET_KEY`)

You can copy from `.env.example` and replace placeholder values.

## Resume AI and ATS Endpoints

- AI resume optimization endpoint: `POST /resume/optimize/<resume_id>`
- ATS analysis endpoint: `POST /resume/analyze/<resume_id>`