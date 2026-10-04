import json
from groq import Groq

from config import get_groq_api_key


class AIEngine:
    """
    Central interface for communicating with the Groq API.

    Agents will use this engine rather than directly
    calling the LLM themselves.
    """

    def __init__(self):
        self.api_key = get_groq_api_key()

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Add it through Streamlit Secrets."
            )

        self.client = Groq(api_key=self.api_key)

    def analyze_text(
        self,
        system_prompt,
        user_prompt,
        model="llama-3.3-70b-versatile"
    ):
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
            temperature=0.1,
        )

        return response.choices[0].message.content

    def analyze_json(
        self,
        system_prompt,
        user_prompt,
        model="llama-3.3-70b-versatile"
    ):
        """
        Request structured JSON from the model.
        """

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
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        try:
            return json.loads(content)

        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "AI returned invalid JSON.",
                "raw_response": content
            }
