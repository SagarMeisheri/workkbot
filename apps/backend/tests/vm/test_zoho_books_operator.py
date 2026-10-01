"""Tests for Autonomous Zoho Books Operator delegating to Universal Browser (Spec 11).

Validates:
1. Zero hardcoded scraping scripts - delegates to UniversalBrowserSession.
2. Playwright locators execute fill, click, select directly on the cloud browser page.
3. Save button click over Kernel CDP.
4. Settings API key verification.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.vm.zoho_books_operator import ZohoBooksItemOperator, DynamicComputerUseAgent


class MockCdpElement:
    def __init__(self, key=""):
        self.key = key
        self.count = AsyncMock(return_value=1)
        self.click = AsyncMock()
        self.fill = AsyncMock()
        self.dispatch_event = AsyncMock()


class MockCdpPage:
    """Mock Playwright Page connected over Kernel CDP."""

    def __init__(self):
        self.locators = {}
        self.keyboard = MagicMock()
        self.keyboard.press = AsyncMock()
        self.url = "https://books.zoho.in/app#/items/new"
        self.goto = AsyncMock()
        self.wait_for_selector = AsyncMock()

    def locator(self, selector):
        if selector not in self.locators:
            loc = MockCdpElement(selector)
            loc.first = loc
            self.locators[selector] = loc
        return self.locators[selector]

    async def evaluate(self, script):
        return [
            {"ref": "e1", "tag": "input", "role": "textbox", "label": "Item Name *", "value": ""},
            {"ref": "e2", "tag": "input", "role": "radio", "label": "Goods", "checked": True},
            {"ref": "e3", "tag": "input", "role": "textbox", "label": "Selling Price *", "value": ""},
            {"ref": "e4", "tag": "input", "role": "textbox", "label": "Cost Price *", "value": ""},
            {"ref": "e5", "tag": "button", "role": "button", "label": "Save", "value": ""},
        ]


class MockCdpSandbox:
    """Mock KernelBrowserSession connected over CDP."""

    def __init__(self, page):
        self._page = page

    async def get_page(self):
        return self._page


@pytest.mark.asyncio
async def test_zoho_books_operator_cdp_form_fill():
    """Verifies that ZohoBooksItemOperator fills the form via Universal Browser."""
    page = MockCdpPage()
    sandbox = MockCdpSandbox(page)
    operator = ZohoBooksItemOperator(sandbox)

    item_data = {
        "name": "Organic Honey 500g",
        "type": "Goods",
        "selling_price": 350.0,
        "cost_price": 280.0,
    }

    res = await operator.fill_new_item_form(item_data)

    assert res["status"] == "awaiting_save_confirmation"
    assert res["mode"] == "universal_ref_cdp"
    assert res["steps"] >= 3

    # Verify Playwright fill calls via stamped ref
    name_loc = page.locators['[data-workkbot-ref="e1"]']
    name_loc.fill.assert_called_with("Organic Honey 500g")

    rate_loc = page.locators['[data-workkbot-ref="e3"]']
    rate_loc.fill.assert_called_with("350.0")


@pytest.mark.asyncio
async def test_zoho_books_operator_submit_save():
    """Verifies that submit_save clicks the Save button via Universal Browser."""
    page = MockCdpPage()
    sandbox = MockCdpSandbox(page)
    operator = ZohoBooksItemOperator(sandbox)

    save_res = await operator.submit_save()
    assert save_res["status"] == "saved"
    assert save_res["action"] == "click"
    assert save_res["target"] == "Save"


@pytest.mark.asyncio
async def test_dynamic_computer_use_agent_delegation():
    """Verifies backwards compatibility wrapper delegates to Universal Browser."""
    page = MockCdpPage()
    sandbox = MockCdpSandbox(page)
    agent = DynamicComputerUseAgent(sandbox)

    res = await agent.run_vision_loop("Add Basmati Rice")
    assert res["status"] == "awaiting_save_confirmation"


def test_kernel_and_e2b_api_key_configuration():
    """Verifies that KERNEL_API_KEY is configured in Settings and exported."""
    import os
    from src.config import settings
    assert hasattr(settings, "KERNEL_API_KEY")
    assert settings.KERNEL_API_KEY != ""
    assert os.environ.get("KERNEL_API_KEY") == settings.KERNEL_API_KEY
