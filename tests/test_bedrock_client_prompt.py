"""Regression tests for BedrockClient prompt construction."""

from aws_services.bedrock_client import BedrockClient
from models.bedrock_extraction import MedicalEntity, EntityType


def _new_client_without_init():
    """Create BedrockClient instance without running __init__ (no AWS calls)."""
    return BedrockClient.__new__(BedrockClient)


def test_construct_prompt_accepts_medical_entity_with_string_entity_type():
    client = _new_client_without_init()

    # use_enum_values=True can store enum values as strings in model instances.
    entity = MedicalEntity(
        entity_type=EntityType.CONDITION,
        text="scratchy throat",
        confidence=0.95,
        begin_offset=0,
        end_offset=14,
    )

    prompt = client._construct_prompt(
        transcript="Patient reports throat irritation.",
        entities=[entity],
    )

    assert "Extracted Medical Entities:" in prompt
    assert "CONDITION: scratchy throat" in prompt


def test_construct_prompt_accepts_dict_entities():
    client = _new_client_without_init()

    prompt = client._construct_prompt(
        transcript="Patient has fever and cough.",
        entities=[
            {"entity_type": "CONDITION", "text": "fever"},
            {"type": "MEDICATION", "text": "paracetamol"},
        ],
    )

    assert "CONDITION: fever" in prompt
    assert "MEDICATION: paracetamol" in prompt
