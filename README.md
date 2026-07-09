# Email Inbox Agent

A LangChain agent that logs into your Gmail inbox via IMAP, reads the 5 most
recent emails, and writes a Markdown summary to a file named after today's
date (`dd mm yy.md`). Summarization is done by a Groq-hosted LLM
(`llama-3.3-70b-versatile`).

## ⚠️ Before you do anything else

This project handles **your email password and an API key** in a plain-text
`.env` file. Treat that file as a secret:

- Never commit `.env` to git or share it (it's already in `.gitignore`).
- Use a Gmail **App Password**, never your real account password (see below).
- If a key/password ever leaks (e.g. pasted in chat, committed by accident),
  rotate it immediately — revoke the App Password in your Google Account and
  regenerate the Groq API key at https://console.groq.com/keys.

## Prerequisites

- Python 3.11+ installed **from python.org** (not an MSYS2/Git-Bash Python —
  those produce a Unix-style venv layout on Windows and will fail to install
  some packages). Check with:

  ```powershell
  python --version
  ```

- A Gmail account with **2-Step Verification enabled** (required to create
  an App Password).
- A Groq API key from https://console.groq.com/keys.

## 1. Create a Gmail App Password

Gmail rejects plain-password IMAP logins. You need a 16-character App
Password instead:

1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if it isn't already on.
3. Go to https://myaccount.google.com/apppasswords
4. Create a new App Password (name it e.g. "Inbox Agent").
5. Copy the 16-character password (spaces don't matter).

## 2. Set up the project

From the project folder in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` is blocked by execution policy, run once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## 3. Configure credentials

Copy `.env.example` to `.env` (if `.env` doesn't already exist) and fill in:

```
GROQ_API_KEY=your_groq_api_key_here
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_APP_PASSWORD=your_16_char_app_password_here
IMAP_SERVER=imap.gmail.com
EMAIL_COUNT=5
```

`EMAIL_APP_PASSWORD` must be the App Password from step 1 — not your normal
Gmail password.

`EMAIL_COUNT` controls how many recent inbox emails are fetched and
summarized. It's read directly by the tool and the agent's prompt, not
chosen by the model, so it's always respected exactly. Defaults to `5` if
unset or invalid. Raising it increases the request size sent to Groq —
watch the rate-limit note below.

## 4. Run it

```powershell
.\venv\Scripts\python.exe main.py
```

On success, a file like `09 07 26.md` appears in the project folder with a
Markdown summary of your last 5 inbox emails.

## 5. Run it automatically on a schedule (optional)

The script itself is a one-shot run, not a background daemon. To run it
automatically at a specific time each day, use Windows Task Scheduler with
`run_agent.bat` (it `cd`s into the project folder, runs the agent through
the venv's Python, and appends output/errors to `run_log.txt` so you can
see what happened even though Task Scheduler runs silently).

The target schedule is **6:05 AM Riyadh (KSA) time**. This machine's system
timezone is already `Arab Standard Time (UTC+03:00, Riyadh)`, so the local
time you set in Task Scheduler is the same as Riyadh time — no conversion
needed, just use `06:05`. (If you ever move this to a machine set to a
different timezone, convert 6:05 AM KSA to that machine's local time first.)

### Start / create the scheduled task

**GUI:**
1. Open Task Scheduler (Start menu → search "Task Scheduler").
2. Action → Create Basic Task.
3. Name: `InboxAgent`.
4. Trigger: **Daily**, Start time: **6:05:00 AM**.
5. Action: **Start a program**.
6. Program/script: `D:\code\Email Inbox Agent\run_agent.bat`.
7. Finish. (Optional but recommended: open the task's Properties afterward
   and check "Wake the computer to run this task" under the Conditions tab,
   so it still fires if the PC is asleep at 6:05 AM.)

**Or one command** (run in PowerShell):

```powershell
schtasks /create /tn "InboxAgent" /tr "'D:\code\Email Inbox Agent\run_agent.bat'" /sc daily /st 06:05
```

### Check it's set up / run it on demand to test

```powershell
schtasks /query /tn "InboxAgent" /v /fo list
schtasks /run /tn "InboxAgent"
```

After a manual or scheduled run, check `run_log.txt` in the project folder
if something seems off.

### Stop it

To pause the schedule without deleting it (keeps the task, just stops it
from firing):

```powershell
schtasks /change /tn "InboxAgent" /disable
```

Re-enable it later with:

```powershell
schtasks /change /tn "InboxAgent" /enable
```

To remove it completely:

```powershell
schtasks /delete /tn "InboxAgent" /f
```

(GUI equivalent: Task Scheduler → find `InboxAgent` in the task list →
right-click → **Disable** or **Delete**.)

## How it works

- `email_tools.py` — `get_last_emails` tool: opens an IMAP connection,
  fetches the `EMAIL_COUNT` newest INBOX messages (env-controlled, not a
  model argument), returns sender/subject/date/body (body truncated to
  ~600 characters to stay under Groq's free-tier token-per-minute limit).
- `file_tools.py` — `save_summary` tool: writes the given Markdown text to
  `dd mm yy.md`, always naming the file from today's date regardless of
  what the model passes.
- `run_agent.bat` — wrapper for Task Scheduler: `cd`s into the project
  folder, runs `main.py` through the venv's Python, logs to
  `run_log.txt`.
- `main.py` — builds the agent with `langchain.agents.create_agent`, wires
  up both tools and a `ChatGroq` model, and runs one summarization pass.
  `parallel_tool_calls` is disabled so the model is forced to read the real
  fetched emails before writing the summary (without this, it would call
  both tools at once and hallucinate the summary before seeing real data).

## Troubleshooting

- **`IMAP login/search failed`** — almost always means `EMAIL_APP_PASSWORD`
  is wrong, is your regular password instead of an App Password, or
  2-Step Verification isn't enabled.
- **`413 ... rate_limit_exceeded` from Groq** — your emails' bodies pushed
  the request over Groq's free-tier tokens-per-minute limit. Lower
  `EMAIL_COUNT` in `.env`, lower the truncation length in `email_tools.py`
  (`_get_body` usage in `get_last_emails`), or upgrade your Groq tier.
- **Missing/placeholder environment variables** printed at startup — one of
  the three required `.env` values is empty or still has its placeholder
  value; fill it in and re-run.
- **A deleted email still shows up** — the agent always reads live from
  Gmail's IMAP server (no local caching). If a message you deleted still
  appears, check it's actually gone from the Inbox in the Gmail web UI
  first (not just archived) — IMAP sync can lag a few seconds after
  deleting from a mobile client.
