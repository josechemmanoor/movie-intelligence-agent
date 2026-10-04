from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .rag import MovieRAG
from .mcp_client import send_email_via_mcp


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

ACTION_WORDS = {
    "send",
    "email",
    "mail",
    "share",
    "forward",
    "dispatch",
}


@dataclass
class AgentResult:
    kind: str
    message: str
    sources: list
    action: Optional[dict] = None


class MovieAgent:

    def __init__(self):
        self.rag = MovieRAG()

        self.client = (
            genai.Client(api_key=GEMINI_API_KEY)
            if GEMINI_API_KEY
            else None
        )

    def _is_action(self, query: str) -> bool:
        words = set(
            re.findall(
                r"[a-zA-Z]+",
                query.lower(),
            )
        )

        return bool(words & ACTION_WORDS)

    def _extract_email(self, query: str):
        match = EMAIL_RE.search(query)

        return match.group(0) if match else None

    def _detect_movie(self, query: str, hits: list):
        """
        Detect an explicitly provided movie title.

        Example:
        movie: Interstellar
        film: Interstellar
        """

        match = re.search(
            r"(?:movie|film)\s*[:=]\s*[\"']?([^,'\"\n]+)",
            query,
            re.I,
        )

        if match:
            return match.group(1).strip()

        if hits:
            return hits[0]["metadata"].get("movie_title")

        return None

    def _clarification_needed(
        self,
        query: str,
        result: dict,
        recipient: str | None,
    ):

        if not result["hits"]:
            return (
                "I couldn't find a relevant scene. "
                "Please provide the movie title or more details "
                "about the scene or quote."
            )

        if self._is_action(query) and not recipient:
            return (
                "Sure. Which email address should I send the "
                "movie scene summary or analysis to?"
            )

        # If retrieval is weak and no movie was specified,
        # avoid confidently guessing.
        best = result["hits"][0]["similarity"]

        if (
            best < 0.20
            and not re.search(
                r"(?:movie|film)\s*[:=]",
                query,
                re.I,
            )
        ):
            return (
                "I found multiple or weakly matching results. "
                "Could you provide the movie title or a few "
                "more words from the quote?"
            )

        return None

    def _build_email(
        self,
        query: str,
        result: dict,
        recipient: str,
    ):

        sources = result["sources"]

        source_text = "\n".join(
            f"- {source['citation']}: {source['text']}"
            for source in sources[:4]
        )

        # Default fallback in case Gemini is unavailable.
        movie = (
            sources[0]["movie"]
            if sources
            else "Movie"
        )

        subject = f"{movie} – Requested Scene"

        body = (
            "Here is the relevant movie information "
            "for your request:\n\n"
            + "\n\n".join(
                f"{source['citation']}\n{source['text']}"
                for source in sources[:4]
            )
        )

        if not self.client:
            return subject, body

        prompt = f"""
Create a concise professional email based ONLY on
the movie subtitle evidence below.

User request:
{query}

Recipient:
{recipient}

Evidence:

{source_text}

The email should include:

- a useful subject
- a short summary or analysis
- precise movie and timestamp citations

Do not invent information.

Return exactly:

SUBJECT: ...

BODY:

...
"""

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )

            text = response.text.strip()

            subject_match = re.search(
                r"SUBJECT:\s*(.+)",
                text,
            )

            body_match = re.search(
                r"BODY:\s*(.*)",
                text,
                re.S,
            )

            if subject_match:
                subject = subject_match.group(1).strip()

            if body_match:
                body = body_match.group(1).strip()

        except Exception as exc:
            print(
                f"Gemini email generation unavailable: {exc}"
            )

        return subject, body

    def handle(self, query: str) -> AgentResult:

        recipient = self._extract_email(query)

        # Retrieve movie information using RAG.
        result = self.rag.answer(query)

        # Check whether clarification is required.
        clarification = self._clarification_needed(
            query,
            result,
            recipient,
        )

        if clarification:
            return AgentResult(
                kind="clarification",
                message=clarification,
                sources=result["sources"],
            )

        # Normal informational question.
        if not self._is_action(query):
            return AgentResult(
                kind="answer",
                message=result["answer"],
                sources=result["sources"],
            )

        # Build email content.
        subject, body = self._build_email(
            query,
            result,
            recipient,
        )

        # Execute email through MCP.
        try:

            status = send_email_via_mcp(
                to=recipient,
                subject=subject,
                body=body,
            )

            message = (
                f"{result['answer']}\n\n"
                f"**MCP Email Action:** {status}"
            )

            return AgentResult(
                kind="email_sent",
                message=message,
                sources=result["sources"],
                action={
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                },
            )

        except Exception as exc:

            return AgentResult(
                kind="email_error",
                message=(
                    "I retrieved the requested movie "
                    "information, but the MCP email action "
                    f"could not be completed: {exc}\n\n"
                    f"**Generated subject:** {subject}\n\n"
                    f"{body}"
                ),
                sources=result["sources"],
                action={
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                },
            )