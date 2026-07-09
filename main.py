import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

from email_tools import get_configured_email_count, get_last_emails
from file_tools import save_summary

load_dotenv()

EMAIL_COUNT = get_configured_email_count()

SYSTEM_PROMPT = f"""You are an email assistant with exactly two tools: \
`get_last_emails` and `save_summary`.

Every time you are invoked, follow this procedure precisely:

1. Call `get_last_emails` exactly once to fetch the {EMAIL_COUNT} most \
recent messages from the user's inbox. The tool takes no arguments -- it \
always returns exactly the configured number of emails on its own.
2. Read every returned email carefully.
3. Write a clear, well-organized Markdown summary with this structure:

   # Inbox Summary - <today's date, human readable>

   For each email, a section:

   ## <Subject>
   - **From:** <sender>
   - **Date:** <date>
   - **Summary:** 2-4 sentences that actually synthesize the body content -- \
what it's about, any request or action needed, and urgency if apparent. Do \
not just restate the subject line.

   End with a "## Overview" section (2-3 sentences) calling out anything that \
needs the user's attention: deadlines, unanswered questions, or \
suspicious/spam-looking mail.

4. Call `save_summary` exactly once, passing the complete Markdown text as \
the `content` argument. The tool names the file automatically from today's \
date -- never invent or pass a filename yourself.
5. After saving, reply with a short confirmation naming the file and briefly \
listing the senders/subjects you summarized.

Rules:
- Call one tool at a time. Never call `save_summary` in the same turn as \
`get_last_emails` -- you must read the actual returned email content first, \
then call `save_summary` in a separate, later step.
- Never fabricate email content. Only summarize what `get_last_emails` \
actually returned. If it returns an error or no messages, report that \
plainly instead of writing a summary or calling `save_summary`.
- Keep summaries factual and concise -- no filler, no repeating raw email text.
- Never include credentials, passwords, or API keys in your output.
"""


def build_agent():
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0,
        model_kwargs={"parallel_tool_calls": False},
    )
    tools = [get_last_emails, save_summary]
    return create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


def _missing_env_vars() -> list[str]:
    required = ["GROQ_API_KEY", "EMAIL_ADDRESS", "EMAIL_APP_PASSWORD"]
    missing = []
    for name in required:
        value = os.environ.get(name, "")
        if not value or value.startswith("your_") or value.startswith("paste_"):
            missing.append(name)
    return missing


def main() -> None:
    missing = _missing_env_vars()
    if missing:
        print(
            "Missing or placeholder environment variables in .env: "
            f"{', '.join(missing)}. Fill them in before running."
        )
        return

    agent = build_agent()
    agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Fetch my last {EMAIL_COUNT} inbox emails and write today's summary file.",
                }
            ]
        }
    )


if __name__ == "__main__":
    main()
