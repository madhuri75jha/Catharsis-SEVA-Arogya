"""Lambda-backed prescription PDF generation service."""
import base64
import json
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class LambdaPDFService:
    """Invoke Lambda to generate prescription PDFs."""

    def __init__(self, region: str, function_name: str):
        self.function_name = function_name
        self.client = boto3.client(
            "lambda",
            region_name=region,
            config=Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 2}),
        )

    def generate_pdf(
        self,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Invoke Lambda and normalize its response payload."""
        try:
            response = self.client.invoke(
                FunctionName=self.function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload).encode("utf-8"),
            )

            if response.get("StatusCode") != 200:
                logger.error("Lambda invocation returned non-200 status: %s", response.get("StatusCode"))
                return None

            raw_payload = response.get("Payload")
            if raw_payload is None:
                logger.error("Lambda response payload missing")
                return None

            data = json.loads(raw_payload.read().decode("utf-8") or "{}")

            # Handle APIGW-style envelope
            if isinstance(data, dict) and "body" in data:
                body = data.get("body")
                if isinstance(body, str):
                    data = json.loads(body or "{}")
                elif isinstance(body, dict):
                    data = body

            if not isinstance(data, dict):
                logger.error("Unexpected Lambda response type: %s", type(data).__name__)
                return None

            if data.get("success") is False:
                logger.warning("Lambda PDF generation failed: %s", data.get("message"))
                return data

            return data

        except (ClientError, BotoCoreError, json.JSONDecodeError) as e:
            logger.error("Failed invoking Lambda PDF service: %s", str(e))
            return None

    @staticmethod
    def decode_pdf_base64(pdf_base64: str) -> Optional[bytes]:
        """Decode base64 PDF content returned by Lambda."""
        try:
            return base64.b64decode(pdf_base64)
        except Exception as e:
            logger.error("Failed decoding base64 PDF payload: %s", str(e))
            return None
