# Phoenix

### AI Study Companion

Phoenix brings course material, adaptive practice, revision, and learning analytics into one workspace. Students can study from their own notes, track areas that need attention, and review key concepts. Teachers can explore class-wide learning patterns and plan targeted support for individual students.

[Features](#features) · [Getting Started](#getting-started) · [Usage](#usage) · [Configuration](#configuration) · [Documentation](#documentation)

## Features

| Feature | Description |
| --- | --- |
| Material library | Upload text-based PDFs, Markdown, or plain text, or paste notes. Preview extracted content before creating study material. |
| AI study packs | Generate summaries, topic labels, practice questions, explanations, and flashcards with source references using Gemini. |
| Adaptive practice | Focus on weaker concepts through guided practice, contextual hints, and follow-up questions. |
| Interactive revision | Review concepts, key relations, and common mistakes through flip cards with mnemonics and examples. |
| Learning insights | Explore topic heatmaps, accuracy trends, study activity, and practice history. |
| Teacher dashboard | Review combined class performance, inspect student reports, and create priority-based teaching plans. |
| Personal workspace | Save study progress locally and export or restore study backups. |

## Technology Stack

- **Application:** Python and Streamlit
- **AI integration:** Google Gemini API
- **Analytics:** pandas and Streamlit charts
- **Document processing:** pypdf
- **Storage:** JSON checkpoints and browser-session state

## Getting Started

### Prerequisites

- Python 3.14
- Git
- A Gemini API key, optional for AI-generated study packs

### 1. Clone the repository

```bash
git clone https://github.com/vanshhhhh-hue/Team-Phoenix-PS-2.3.git
cd Team-Phoenix-PS-2.3
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS and Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies and start Phoenix

```bash
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. Windows users can also launch the application with `Start-Phoenix.cmd` after completing setup.

## Usage

### Explore the workspace

Use the sidebar to navigate between Dashboard, Library, Quiz, Flash Cards, Insights, and Teacher Dashboard.

- **Dashboard:** view recent activity, topic performance, and recommended practice.
- **Library:** browse chapters, read notes, and start practice for a selected topic.
- **Quiz:** complete focused practice with guidance when a concept needs more attention.
- **Flash Cards:** select a chapter, flip cards to review concepts, and rate your recall.
- **Insights:** filter learning history and identify topics to revisit.
- **Teacher Dashboard:** review class heatmaps and teaching priorities, then open individual student reports.

### Study from your own material

1. Choose **Study your own material** in the sidebar workspace menu, or **Add your material** in Library.
2. Upload a PDF, TXT, or Markdown file, or paste explanatory notes.
3. Preview the extracted content and build a study pack.
4. Practise, review flashcards, and check the resulting learning insights.

For progress that persists between sessions, start a personal workspace:

```powershell
# Windows PowerShell
$env:PHOENIX_MODE = "local"
python -m streamlit run app.py
```

```bash
# macOS / Linux
PHOENIX_MODE=local python -m streamlit run app.py
```

Personal workspaces save to `.local/study.json` by default. Backup controls are available in workspace settings.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `PHOENIX_MODE` | Application mode; use `local` to enable persistent workspace storage | `demo` |
| `PHOENIX_DATA_DIR` | Storage directory for the personal workspace | `.local` |
| `GEMINI_API_KEY` | Server-side API key for Gemini generation | Not set |
| `GEMINI_MODEL` | Model used for study-pack generation | `gemini-flash-lite-latest` |

Set runtime variables in your shell or hosting environment. For Gemini, create a root `.env` file using [`.env.example`](.env.example) as a reference:

```dotenv
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-flash-lite-latest
```

In the uploaded-material workspace, enable **Use Gemini when available** under Workspace settings. Without a usable API connection, Phoenix provides a labelled local extractive-recall fallback. API keys stay on the server and are excluded from study backups.

## Project Structure

```text
app.py                   Application entry point
src/phoenix/             UI, study workflows, analytics, AI integration, and storage
assets/                  Branding assets
data/                    Supporting exercise definitions
scripts/                 Launch, verification, and fixture utilities
tests/                   Domain and application regression tests
docs/                    Architecture, deployment, and technical documentation
.streamlit/              Application theme and server configuration
.github/workflows/       Continuous integration
```

## Development

Run the offline verification suite and dependency checks:

```bash
python scripts/verify.py
python -m pip check
```

Tests cover practice behavior, reporting, revision, storage, navigation, and session isolation. Live provider checks are available separately through `python scripts/smoke_ai.py`.

## Supported Inputs and Scope

- PDF, TXT, and Markdown uploads up to **10 MB**; text-based PDFs up to **60 pages**.
- Up to **20 documents** and **8 MiB** of personal workspace data.
- Scanned PDFs require OCR before upload.
- AI-generated material should be reviewed against its source.
- Authentication and multi-tenant storage are not included; local persistence is designed for a single owner.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Technical reference](docs/engineering/API_CONTRACT.md)

## Contributing

Open an issue to discuss a bug or proposed change. For pull requests, describe the affected workflow, include relevant verification, and keep credentials and personal study data out of commits.
