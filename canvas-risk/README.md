# Canvas-Risk

A professional terminal-based TA dashboard for monitoring student performance and identifying at-risk students using the Canvas LMS API.

## Features

- **Canvas API Integration**: Pulls students, assignments, and submissions.
- **Weighted Risk Engine**: Identifies at-risk students based on:
  - Missing assignments (40%)
  - Grade trends (30%)
  - Late submissions (20%)
  - Inactivity (10%)
- **Interactive TUI**: Modern Textual-based dashboard with real-time sync.
- **CLI Reports**: Quick terminal tables for risk reports and ungraded work.
- **Local Cache**: SQLite database for offline viewing and trend analysis.

## Installation

1. Clone the repository and navigate to the directory:
   ```bash
   cd canvas-risk
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your Canvas API token, Base URL, and Course ID.

## Usage

### Sync Data
First, sync your local database with Canvas:
```bash
python main.py sync
```

### Launch Dashboard (TUI)
```bash
python main.py dashboard
```

### Quick CLI Reports
```bash
# Risk Report
python main.py risk-report

# Ungraded Work
python main.py ungraded
```

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Configuration

| Variable | Description |
|----------|-------------|
| `CANVAS_API_TOKEN` | Your Canvas personal access token. |
| `CANVAS_BASE_URL` | The API endpoint (e.g., `https://canvas.instructure.com/api/v1`). |
| `CANVAS_COURSE_ID` | The numeric ID of the course to monitor. |

## Project Structure

- `api/`: Canvas REST API client.
- `database/`: SQLAlchemy models and SQLite manager.
- `analytics/`: Risk scoring logic.
- `ui/`: Textual TUI screens.
- `commands/`: Typer CLI commands.
