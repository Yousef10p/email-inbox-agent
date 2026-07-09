import os
from datetime import datetime

from langchain_core.tools import tool

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


@tool
def save_summary(content: str) -> str:
    """Save the given Markdown summary text to a file.

    The filename is always generated automatically from today's date in
    'dd mm yy.md' format (e.g. '09 07 26.md') and saved in the project
    directory. Only pass the Markdown `content` -- never invent or pass a
    filename yourself.
    """
    filename = datetime.now().strftime("%d %m %y") + ".md"
    path = os.path.join(_PROJECT_ROOT, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Summary saved to {path}"
