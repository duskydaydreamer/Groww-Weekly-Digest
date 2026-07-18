# App Store Review Pulse

A fully automated AI-driven pipeline that scrapes app reviews, extracts emerging themes using Groq (LLaMA 3), and delivers a comprehensive "Weekly Pulse" summary straight to your Google Docs and Gmail via a Model Context Protocol (MCP) server.

## Features
- **Data Ingestion**: Scrapes Google Play and Apple App Store reviews.
- **PII Scrubbing**: Automatically removes Personally Identifiable Information using Microsoft Presidio.
- **AI Theme Clustering**: Uses Groq (LLaMA 3) to analyze sentiment and cluster reviews into actionable themes.
- **MCP Delivery**: Securely interfaces with Google Docs and Gmail APIs to format and deliver the pulse report.
- **Fully Automated**: Uses GitHub Actions to run every Monday at 9:00 AM automatically.

## Quick Start

### 1. Local Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your secrets.
```bash
cp .env.example .env
```

### 3. Run Locally
Execute the Master Switch CLI:
```bash
# Run end-to-end
python run_pulse.py

# Run step-by-step
python run_pulse.py --step ingest
python run_pulse.py --step scrub
python run_pulse.py --step cluster

# Run without sending emails/docs
python run_pulse.py --dry-run
```

## GitHub Actions Automation

This project is configured to run automatically every Monday at 9:00 AM UTC via GitHub Actions.

To make the automation work, you must add the following **Repository Secrets** in your GitHub repository settings (`Settings > Secrets and variables > Actions > New repository secret`):

| Secret Name | Description |
|---|---|
| `GROQ_API_KEY` | Your API key from Groq to run the AI analysis. |
| `PULSE_EMAIL_TO` | The email address that should receive the weekly draft. |
| `PULSE_DOC_ID` | The ID of the Google Doc where the report will be appended. |
| `MCP_SERVER_URL` | The URL to your hosted MCP Server (e.g., Render URL). |
| `MCP_AUTH_TOKEN` | The authentication token required to talk to your MCP server. |

Once those secrets are added, the pipeline will run 100% autonomously!
