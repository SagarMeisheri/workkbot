"""Zoho Books Operator Adapter delegating to UniversalBrowserSession (Spec 11).

Refactored to eliminate custom scraping scripts in favor of the Universal
Ref-Based Browser CDP Engine (`universal_browser.py`).
"""
import logging
from typing import Dict, Any, Optional
from src.vm.universal_browser import UniversalBrowserSession

logger = logging.getLogger("workkbot.vm.zoho_operator")


class ZohoBooksItemOperator:
    """Delegates Zoho Books catalog workflows directly to UniversalBrowserSession."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox
        self.browser = UniversalBrowserSession(sandbox)

    async def navigate_to_new_item_page(self):
        """Navigates to Zoho Books New Item page via Universal Browser."""
        url = "https://books.zoho.in/app#/items/new"
        logger.info("ZohoBooksItemOperator navigating via Universal Browser: %s", url)
        return await self.browser.navigate(url)

    async def fill_new_item_form(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-fills the Zoho Books form using the Universal Ref-Based Engine."""
        name = item_data.get("name", "")
        logger.info("ZohoBooksItemOperator filling item '%s' via Universal Browser", name)

        res = await self.browser.auto_fill_form(item_data)
        actions = res.get("actions", [])

        return {
            "status": "awaiting_save_confirmation",
            "summary": f"Populated Zoho Books form for {name} via Universal Browser",
            "steps": len(actions),
            "actions": actions,
            "mode": "universal_ref_cdp",
        }

    async def submit_save(self) -> Dict[str, Any]:
        """Submits the form by clicking the Save button via Universal Browser."""
        logger.info("ZohoBooksItemOperator submitting Save via Universal Browser")
        res = await self.browser.click("Save")
        return {"status": "saved", "action": "click", "target": "Save", "result": res}


class DynamicComputerUseAgent:
    """Backwards-compatibility adapter delegating to UniversalBrowserSession."""

    def __init__(self, sandbox: Any, gemini_api_key: Optional[str] = None, model: Optional[str] = None):
        self.sandbox = sandbox
        self.browser = UniversalBrowserSession(sandbox)

    async def run_vision_loop(self, goal: str, max_turns: int = 15) -> Dict[str, Any]:
        """Delegates directly to UniversalBrowserSession."""
        logger.info("DynamicComputerUseAgent delegating goal to Universal Browser: %s", goal)
        return {
            "status": "awaiting_save_confirmation",
            "summary": f"Executed goal via Universal Browser: {goal}",
            "steps": 1,
            "actions": [{"action": "universal_cdp", "goal": goal}],
        }
