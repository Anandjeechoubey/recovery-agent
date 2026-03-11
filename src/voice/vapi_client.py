from __future__ import annotations

import httpx

from src.config import settings

VAPI_BASE_URL = "https://api.vapi.ai"


class VapiClient:
    def __init__(self):
        self.api_key = settings.vapi_api_key
        self.phone_number_id = settings.vapi_phone_number_id
        self.webhook_url = settings.vapi_webhook_url

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_outbound_call(
        self,
        phone_number: str,
        system_prompt: str,
        first_message: str,
        metadata: dict | None = None,
    ) -> str:
        """Create an outbound call via Vapi. Returns call ID."""
        payload = {
            "phoneNumberId": self.phone_number_id,
            "customer": {"number": phone_number},
            "assistant": {
                "model": {
                    "provider": "openai",
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                    ],
                },
                "firstMessage": first_message,
                "serverUrl": self.webhook_url,
                "recordingEnabled": True,
                "endCallMessage": "Thank you for your time. Goodbye.",
            },
            "metadata": metadata or {},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VAPI_BASE_URL}/call/phone",
                headers=self._headers(),
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def get_call(self, call_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VAPI_BASE_URL}/call/{call_id}",
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def end_call(self, call_id: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{VAPI_BASE_URL}/call/{call_id}",
                headers=self._headers(),
                timeout=30.0,
            )
