from fastapi import HTTPException
from google import genai
from google.genai import types
from basic.prompts import main_response_prompt
from dotenv import load_dotenv
import os
load_dotenv()

class LLM():
    def __init__(self):
        api_keys_str = os.getenv("GOOGLE_GENAI_API_KEYS", "")
        self.api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        self.model = "gemini-2.0-flash-lite"

    def is_authentication_error(self, e: Exception) -> bool:
        error_msg = str(e).lower()
        return any(keyword in error_msg for keyword in ['permission_denied', 'invalid api key', 'authentication'])

    def generate_response(self, user_query: str) -> str:
        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="text/plain",
            system_instruction=[types.Part.from_text(text=(main_response_prompt)),],
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_query),
                ],
            ),
        ]

        for key in self.api_keys:
            client = genai.Client(api_key=key)
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=generate_content_config,
                )
                content = response.text.strip()
                return content.replace("```json", "").replace("```", "").strip()
            except Exception as e:
                if self.is_authentication_error(e):
                    print(e)
                    continue
                else:
                    raise e

        raise HTTPException(status_code=401, detail="All API keys failed authentication.")