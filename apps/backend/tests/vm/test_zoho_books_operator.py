"""Tests for Dynamic Computer Use Vision Loop in Zoho Books (Spec 11).

Validates that the operator relies on real dynamic vision tool calls from Gemini
rather than hardcoded coordinates, and properly drives the E2B sandbox mouse/keyboard primitives.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.vm.zoho_books_operator import DynamicComputerUseAgent, ZohoBooksItemOperator


class MockSandbox:
    def __init__(self):
        self.clicks = []
        self.typed_texts = []
        self.pressed_keys = []
        self.scrolls = []
        self.drags = []

    def screenshot(self) -> bytes:
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"

    def left_click(self, x: int, y: int):
        self.clicks.append((x, y))

    def write(self, text: str):
        self.typed_texts.append(text)

    def press(self, key: str):
        self.pressed_keys.append(key)

    def scroll(self, direction: str, ticks: int = 3):
        self.scrolls.append((direction, ticks))

    def drag(self, start: list, end: list):
        self.drags.append((start, end))


@pytest.mark.asyncio
async def test_dynamic_vision_loop_executes_actions():
    """Verifies that the vision agent parses LLM function calls dynamically."""
    sandbox = MockSandbox()
    agent = DynamicComputerUseAgent(sandbox, gemini_api_key="test-key")

    # Mock candidate with function calls from Gemini vision reasoning
    mock_fc_click = MagicMock()
    mock_fc_click.name = "click"
    mock_fc_click.args = {"x": 345, "y": 210, "reason": "Focus Name field"}

    mock_fc_type = MagicMock()
    mock_fc_type.name = "type_text"
    mock_fc_type.args = {"text": "Basmati Rice 5kg", "reason": "Type item name"}

    mock_fc_complete = MagicMock()
    mock_fc_complete.name = "task_completed"
    mock_fc_complete.args = {"summary": "Item name entered"}

    part1 = MagicMock()
    part1.function_call = mock_fc_click

    part2 = MagicMock()
    part2.function_call = mock_fc_type

    part3 = MagicMock()
    part3.function_call = mock_fc_complete

    mock_resp1 = MagicMock()
    mock_resp1.candidates = [MagicMock(content=MagicMock(parts=[part1, part2]))]

    mock_resp2 = MagicMock()
    mock_resp2.candidates = [MagicMock(content=MagicMock(parts=[part3]))]

    with patch.object(agent.client.models, "generate_content", side_effect=[mock_resp1, mock_resp2]):
        result = await agent.run_vision_loop(goal="Add item Basmati Rice 5kg", max_turns=5)

    assert result["status"] == "awaiting_save_confirmation"
    assert (345, 210) in sandbox.clicks
    assert "Basmati Rice 5kg" in sandbox.typed_texts


@pytest.mark.asyncio
async def test_zoho_books_operator_delegation():
    """Verifies that ZohoBooksItemOperator delegates to the dynamic vision loop."""
    sandbox = MockSandbox()
    operator = ZohoBooksItemOperator(sandbox)

    item_data = {
        "name": "Organic Honey 500g",
        "type": "Goods",
        "unit": "jar",
        "selling_price": 350.0,
        "cost_price": 280.0,
        "description": "Pure raw forest honey",
    }

    mock_result = {
        "status": "awaiting_save_confirmation",
        "summary": "Filled Organic Honey 500g form",
        "steps": 3,
    }

    with patch.object(operator.agent, "run_vision_loop", new_callable=AsyncMock) as mock_loop:
        mock_loop.return_value = mock_result
        res = await operator.fill_new_item_form(item_data)

    assert res["status"] == "awaiting_save_confirmation"
    mock_loop.assert_called_once()
    prompt_used = mock_loop.call_args.kwargs["goal"]
    assert "Organic Honey 500g" in prompt_used
    assert "350.0" in prompt_used


def test_e2b_api_key_configuration():
    """Verifies that E2B_API_KEY is recognized in Settings and exported to os.environ."""
    import os
    from src.config import settings
    assert hasattr(settings, "E2B_API_KEY")
    assert settings.E2B_API_KEY != ""
    assert os.environ.get("E2B_API_KEY") == settings.E2B_API_KEY

