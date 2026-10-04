import json
import re
import time

from groq import Groq

from config import (
    get_groq_api_key,
    GROQ_TEXT_MODEL,
    GROQ_FALLBACK_MODEL,
    GROQ_WHISPER_MODEL,
)


class AIEngine:
    """
    Central AI engine for RescueMind AI.

    AI output is treated as analysis/recommendation.
    It is NOT treated as a verified emergency fact.
    """

    def __init__(self):

        self.api_key = get_groq_api_key()

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Please add it in Streamlit Cloud -> Settings -> Secrets."
            )

        self.client = Groq(api_key=self.api_key)


    def _chat(
        self,
        system_prompt,
        user_prompt,
        model=None,
        temperature=0.1
    ):

        models = [model or GROQ_TEXT_MODEL]

        if GROQ_FALLBACK_MODEL not in models:
            models.append(GROQ_FALLBACK_MODEL)

        last_error = None

        for selected_model in models:

            for attempt in range(2):

                try:

                    response = self.client.chat.completions.create(
                        model=selected_model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        temperature=temperature,
                    )

                    return response.choices[0].message.content

                except Exception as exc:

                    last_error = exc

                    time.sleep(
                        1.5 * (attempt + 1)
                    )

        raise RuntimeError(
            f"Groq request failed: {last_error}"
        )


    def analyze_json(
        self,
        system_prompt,
        user_prompt,
        schema=None
    ):

        models = [
            GROQ_TEXT_MODEL,
            GROQ_FALLBACK_MODEL
        ]

        last_error = None

        for model in models:

            for attempt in range(2):

                try:

                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        temperature=0.0,
                        response_format={
                            "type": "json_object"
                        },
                    )

                    raw = (
                        response
                        .choices[0]
                        .message
                        .content
                        or "{}"
                    )

                    parsed = self._parse_json(raw)

                    if parsed is not None:
                        return parsed

                    last_error = ValueError(
                        "Model returned invalid JSON."
                    )

                except Exception as exc:

                    last_error = exc

                    time.sleep(
                        1.5 * (attempt + 1)
                    )

        raise RuntimeError(
            f"Structured Groq analysis failed: {last_error}"
        )


    @staticmethod
    def _parse_json(raw):

        raw = raw.strip()

        # Try normal JSON
        try:
            return json.loads(raw)

        except Exception:
            pass

        # Try extracting JSON object
        match = re.search(
            r"\{.*\}",
            raw,
            flags=re.DOTALL
        )

        if match:

            try:
                return json.loads(
                    match.group(0)
                )

            except Exception:
                return None

        return None


    def transcribe_audio(
        self,
        audio_bytes,
        filename,
        language=None
    ):

        """
        Transcribe emergency voice reports
        using Groq Whisper.

        Transcript is AI-generated and
        requires human verification.
        """

        try:

            file_tuple = (
                filename,
                audio_bytes
            )

            kwargs = {
                "file": file_tuple,
                "model": GROQ_WHISPER_MODEL,
                "response_format": "json",
                "temperature": 0.0,
            }

            if language:
                kwargs["language"] = language

            result = (
                self.client
                .audio
                .transcriptions
                .create(**kwargs)
            )

            return {
                "text": getattr(
                    result,
                    "text",
                    ""
                ) or "",

                "model": GROQ_WHISPER_MODEL,

                "confidence": None,

                "verified": False,
            }

        except Exception as exc:

            raise RuntimeError(
                f"Voice transcription failed: {exc}"
            )


    def analyze_incident(self, report):

        system_prompt = """
You are the Emergency Intake and Severity
Analysis Agent inside RescueMind AI.

RescueMind AI is a hackathon prototype.

Analyze the supplied emergency report conservatively.

Rules:

- Never invent facts.
- Separate submitted information from AI inference.
- If information is missing, explicitly mention it.
- Recommendations require human verification.
- Do not guess the number of people at risk.
- Return ONLY valid JSON.

Required JSON:

{
    "category": "Flood|Earthquake|Fire|Road Accident|Medical Emergency|Other",
    "summary": "short summary",
    "severity": "Critical|High|Medium|Low|Unknown",
    "severity_score": 0,
    "people_at_risk": 0,
    "urgency_reason": "reason",
    "detected_signals": [],
    "missing_information": [],
    "recommended_actions": [],
    "confidence": 0.0,
    "needs_human_verification": true
}

Use 0 for people_at_risk when
the report does not provide a number.

Do not guess a number.
"""

        user_prompt = json.dumps(
            report,
            ensure_ascii=False
        )

        return self.analyze_json(
            system_prompt,
            user_prompt
        )


def get_ai_engine():

    return AIEngine()
