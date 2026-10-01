"""Tests for Universal Ref-Based Browser CDP Engine (Spec 11).

Validates:
1. Universal applicability across any website (zero hardcoded scraping scripts).
2. DOM ref stamping: assigns `data-workkbot-ref` to interactive elements.
3. Accurate ref-based targeting for `click(ref)` and `fill(ref, text)`.
4. Semantic auto-fill matching arbitrary key-value form payloads.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.vm.universal_browser import UniversalBrowserSession


class MockElement:
    def __init__(self, selector=""):
        self.selector = selector
        self.count = AsyncMock(return_value=1)
        self.click = AsyncMock()
        self.fill = AsyncMock()
        self.dispatch_event = AsyncMock()


class MockPlaywrightPage:
    def __init__(self):
        self.url = "https://example.com/form"
        self.goto = AsyncMock()
        self.keyboard = MagicMock()
        self.keyboard.press = AsyncMock()
        self.locators = {}

    def locator(self, selector):
        if selector not in self.locators:
            el = MockElement(selector)
            el.first = el
            self.locators[selector] = el
        return self.locators[selector]

    async def evaluate(self, script):
        # Simulates stamping and returning interactive elements from the DOM
        return [
            {"ref": "e1", "tag": "input", "role": "textbox", "label": "Item Name *", "value": ""},
            {"ref": "e2", "tag": "input", "role": "radio", "label": "Goods", "checked": True},
            {"ref": "e3", "tag": "input", "role": "radio", "label": "Service", "checked": False},
            {"ref": "e4", "tag": "input", "role": "textbox", "label": "Selling Price *", "value": ""},
            {"ref": "e5", "tag": "input", "role": "textbox", "label": "Cost Price *", "value": ""},
            {"ref": "e6", "tag": "textarea", "role": "textarea", "label": "Description", "value": ""},
            {"ref": "e7", "tag": "button", "role": "button", "label": "Save", "value": ""},
        ]


class MockSandbox:
    def __init__(self, page):
        self._page = page

    async def get_page(self):
        return self._page


@pytest.mark.asyncio
async def test_universal_browser_snapshot_stamps_refs():
    """Verifies that snapshot stamps refs and builds a semantic markdown tree."""
    page = MockPlaywrightPage()
    sandbox = MockSandbox(page)
    ub = UniversalBrowserSession(sandbox)

    snap = await ub.snapshot()
    assert snap["status"] == "success"
    assert snap["count"] == 7
    assert "[ref=e1] textbox \"Item Name *\"" in snap["snapshot_text"]
    assert "[ref=e7] button \"Save\"" in snap["snapshot_text"]


@pytest.mark.asyncio
async def test_universal_browser_click_and_fill_by_ref():
    """Verifies that click and fill target the exact stamped [data-workkbot-ref] locator."""
    page = MockPlaywrightPage()
    sandbox = MockSandbox(page)
    ub = UniversalBrowserSession(sandbox)

    # Click ref e2
    res_click = await ub.click("e2")
    assert res_click["status"] == "clicked"
    assert res_click["method"] == "ref"
    page.locators['[data-workkbot-ref="e2"]'].click.assert_called_once()

    # Fill ref e1
    res_fill = await ub.fill("e1", "Royal Basmati Rice 5kg")
    assert res_fill["status"] == "filled"
    assert res_fill["method"] == "ref"
    page.locators['[data-workkbot-ref="e1"]'].fill.assert_called_with("Royal Basmati Rice 5kg")


@pytest.mark.asyncio
async def test_universal_browser_auto_fill_form():
    """Verifies semantic form filling for arbitrary website forms."""
    page = MockPlaywrightPage()
    sandbox = MockSandbox(page)
    ub = UniversalBrowserSession(sandbox)

    payload = {
        "name": "Organic Honey 500g",
        "selling_price": 420.0,
        "cost_price": 310.0,
        "description": "Pure mountain honey",
    }

    res = await ub.auto_fill_form(payload)
    assert res["status"] == "completed"
    assert res["actions_count"] == 4

    # Verify that ref e1 (Item Name) received the name
    page.locators['[data-workkbot-ref="e1"]'].fill.assert_called_with("Organic Honey 500g")
    # Verify that ref e4 (Selling Price) received the price
    page.locators['[data-workkbot-ref="e4"]'].fill.assert_called_with("420.0")
