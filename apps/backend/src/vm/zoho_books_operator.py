"""Autonomous Zoho Books Computer Use Operator (Spec 11).

Completely dynamic vision-driven agent loop.
Zero hardcoded coordinates.
The agent captures live screenshots from the E2B Desktop Sandbox, passes them to Gemini 2.0 Flash,
visually reasons over the desktop interface, identifies UI elements (Name, Type, Unit, Price, Cost, Save),
and autonomously executes mouse clicks, typing, and keypresses.
"""
import io
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger("workkbot.vm.zoho_operator")

COMPUTER_USE_SYSTEM_PROMPT = """You are an autonomous computer-use vision agent controlling an isolated Linux desktop sandbox (resolution: 1024x720).
You see the live screen via screenshots. Your goal is to autonomously navigate Zoho Books and fulfill the user's objective (e.g. create a new inventory or service item).

OPERATIONAL RULES:
1. Examine the screenshot carefully. Visually identify labels, text input boxes, dropdowns, radio buttons, and buttons.
2. Determine the center (x, y) pixel coordinates of the element you need to interact with next.
   - Screen width is 1024, height is 720.
   - Top-left corner is (0, 0), bottom-right is (1024, 720).
3. If an input field requires focus before typing, use `click_and_type(x, y, text)`.
4. If a dropdown requires selecting an option, click it, type the unit/option, and call `press_key("Enter")`.
5. Once all required and requested fields are filled, call `task_completed(summary)` to pause for user review before saving.
6. Do NOT click Save until the user has approved. When asked to save after confirmation, click the blue primary Save button.
"""


class DynamicComputerUseAgent:
    """Autonomous vision-driven computer-use loop executing tasks on E2B Desktop Sandboxes."""

    def __init__(self, sandbox: Any, gemini_api_key: Optional[str] = None, model: Optional[str] = None):
        self.sandbox = sandbox
        api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        model_name = model
        try:
            from src.config import settings
            if not api_key:
                api_key = settings.GEMINI_API_KEY
            if not model_name:
                model_name = getattr(settings, "DEFAULT_MODEL", "gemini-3.8-flash")
        except Exception:
            pass
        self.model = model_name or "gemini-3.8-flash"
        self.client = genai.Client(api_key=api_key)
        self.history: List[Any] = []
        self.actions_log: List[Dict[str, Any]] = []

    async def run_vision_loop(
        self,
        goal: str,
        max_turns: int = 15,
    ) -> Dict[str, Any]:
        """
        Executes the iterative Computer Use loop:
        1. Capture screenshot from E2B sandbox.
        2. Query Gemini 2.0 Flash with screenshot and target goal.
        3. Model visually detects elements and emits dynamic function calls.
        4. Execute action on E2B desktop (mouse/keyboard).
        5. Repeat until goal completion.
        """
        logger.info("Starting dynamic computer use vision loop for goal: %s", goal)

        # Declare tools for Gemini function calling
        def click(x: int, y: int, reason: str = ""):
            """Click at coordinates (x, y) on the screen."""
            pass

        def click_and_type(x: int, y: int, text: str, reason: str = ""):
            """Click at coordinates (x, y) to focus, then type text."""
            pass

        def type_text(text: str, reason: str = ""):
            """Type text into the currently active element."""
            pass

        def press_key(key: str, reason: str = ""):
            """Press a keyboard key (e.g. 'Enter', 'Tab', 'Escape', 'BackSpace')."""
            pass

        def scroll(direction: str, ticks: int = 3, reason: str = ""):
            """Scroll 'up' or 'down' on the active window."""
            pass

        def drag(start_x: int, start_y: int, end_x: int, end_y: int, reason: str = ""):
            """Drag mouse from (start_x, start_y) to (end_x, end_y)."""
            pass

        def task_completed(summary: str):
            """Call when all fields have been filled or the task is finished."""
            pass

        tools = [click, click_and_type, type_text, press_key, scroll, drag, task_completed]

        # 1. Capture initial live browser screenshot
        try:
            if hasattr(self.sandbox, "async_screenshot"):
                initial_screenshot = await self.sandbox.async_screenshot()
            else:
                initial_screenshot = self.sandbox.screenshot()
        except Exception as e:
            logger.error("Failed to capture initial screenshot from browser: %s", e)
            return {"status": "error", "message": f"Initial screenshot failed: {e}"}

        initial_user_parts = [
            types.Part.from_text(
                text=f"{COMPUTER_USE_SYSTEM_PROMPT}\n\nUSER OBJECTIVE:\n{goal}\n\nPlease analyze the screenshot and choose the first browser action."
            ),
            types.Part.from_bytes(data=initial_screenshot, mime_type="image/png"),
        ]
        conversation_contents: List[Any] = [types.Content(role="user", parts=initial_user_parts)]

        for turn in range(max_turns):
            # 2. Model visual reasoning
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=conversation_contents,
                    config=types.GenerateContentConfig(
                        tools=tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        temperature=0.1,
                    ),
                )
            except Exception as e:
                logger.error("Gemini vision inference error: %s", e)
                return {"status": "error", "message": f"Vision model error: {e}"}

            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content:
                logger.warning("Empty response from vision model on step %d", turn)
                break

            # Add model response (role="model")
            conversation_contents.append(candidate.content)

            # 3. Check for function calls
            has_action = False
            task_done = False
            task_summary = ""
            tool_response_parts: List[Any] = []

            for part in candidate.content.parts:
                if part.function_call:
                    has_action = True
                    fc = part.function_call
                    fn_name = fc.name
                    fn_args = fc.args or {}
                    logger.info("Step %d - Model decided action: %s with args: %s", turn + 1, fn_name, fn_args)

                    if fn_name == "task_completed":
                        task_done = True
                        task_summary = fn_args.get("summary", "Task completed")
                        self.actions_log.append({"action": "task_completed", "summary": task_summary})
                        break

                    action_executed = await self._execute_sandbox_action(fn_name, fn_args)
                    self.actions_log.append(action_executed)

                    # In Gemini API, function responses are provided with role='user'
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": "action_executed_successfully"},
                        )
                    )

            if task_done:
                return {
                    "status": "awaiting_save_confirmation",
                    "summary": task_summary,
                    "steps": turn + 1,
                    "actions": self.actions_log,
                }

            if not has_action:
                # Model provided plain text without tool calls
                text = response.text or ""
                logger.info("Model responded with text: %s", text)
                if "completed" in text.lower() or "finished" in text.lower() or "done" in text.lower():
                    return {
                        "status": "awaiting_save_confirmation",
                        "summary": text,
                        "steps": turn + 1,
                        "actions": self.actions_log,
                    }
                break

            # 4. Capture fresh screenshot after executing action
            try:
                if hasattr(self.sandbox, "async_screenshot"):
                    new_screenshot = await self.sandbox.async_screenshot()
                else:
                    new_screenshot = self.sandbox.screenshot()
            except Exception as e:
                logger.error("Failed to capture updated screenshot: %s", e)
                new_screenshot = None

            # 5. Send updated screenshot and tool confirmations back in next user turn
            user_parts = list(tool_response_parts)
            if new_screenshot:
                user_parts.append(types.Part.from_bytes(data=new_screenshot, mime_type="image/png"))
            user_parts.append(
                types.Part.from_text(text=f"Screen updated after action. Step {turn + 1}/{max_turns}. What is the next browser action?")
            )
            conversation_contents.append(types.Content(role="user", parts=user_parts))

        return {
            "status": "in_progress",
            "message": f"Completed {max_turns} vision steps",
            "actions": self.actions_log,
        }

    async def _execute_sandbox_action(self, fn_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches dynamic function call to Kernel CDP (or sandbox mouse/keyboard primitives)."""
        import asyncio
        if fn_name == "click":
            x, y = int(args.get("x", 0)), int(args.get("y", 0))
            if hasattr(self.sandbox, "async_left_click"):
                await self.sandbox.async_left_click(x, y)
            else:
                self.sandbox.left_click(x, y)
            return {"action": "click", "x": x, "y": y, "reason": args.get("reason")}

        elif fn_name == "click_and_type":
            x, y = int(args.get("x", 0)), int(args.get("y", 0))
            text = str(args.get("text", ""))
            if hasattr(self.sandbox, "async_left_click"):
                await self.sandbox.async_left_click(x, y)
            else:
                self.sandbox.left_click(x, y)
            await asyncio.sleep(0.2)
            if hasattr(self.sandbox, "async_write"):
                await self.sandbox.async_write(text)
            else:
                self.sandbox.write(text)
            return {"action": "click_and_type", "x": x, "y": y, "text": text, "reason": args.get("reason")}

        elif fn_name == "type_text":
            text = str(args.get("text", ""))
            if hasattr(self.sandbox, "async_write"):
                await self.sandbox.async_write(text)
            else:
                self.sandbox.write(text)
            return {"action": "type_text", "text": text, "reason": args.get("reason")}

        elif fn_name == "press_key":
            key = str(args.get("key", "Enter"))
            if hasattr(self.sandbox, "async_press"):
                await self.sandbox.async_press(key)
            else:
                self.sandbox.press(key)
            return {"action": "press_key", "key": key, "reason": args.get("reason")}

        elif fn_name == "scroll":
            direction = str(args.get("direction", "down"))
            ticks = int(args.get("ticks", 3))
            if hasattr(self.sandbox, "async_scroll"):
                await self.sandbox.async_scroll(direction, ticks)
            else:
                self.sandbox.scroll(direction, ticks)
            return {"action": "scroll", "direction": direction, "ticks": ticks}

        elif fn_name == "drag":
            start_x = int(args.get("start_x", 0))
            start_y = int(args.get("start_y", 0))
            end_x = int(args.get("end_x", 0))
            end_y = int(args.get("end_y", 0))
            if hasattr(self.sandbox, "async_drag"):
                await self.sandbox.async_drag([start_x, start_y], [end_x, end_y])
            else:
                self.sandbox.drag([start_x, start_y], [end_x, end_y])
            return {"action": "drag", "from": [start_x, start_y], "to": [end_x, end_y], "reason": args.get("reason")}

        return {"action": fn_name, "args": args}


class ZohoBooksItemOperator:
    """High-level orchestrator using DynamicComputerUseAgent to drive Zoho Books item catalog workflows."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox
        self.agent = DynamicComputerUseAgent(sandbox)

    async def navigate_to_new_item_page(self):
        """Opens or navigates browser to the Zoho Books New Item page."""
        logger.info("Opening Zoho Books New Item page")
        url = "https://books.zoho.in/app#/items/new"
        if hasattr(self.sandbox, "async_goto"):
            await self.sandbox.async_goto(url)
        elif hasattr(self.sandbox, "goto"):
            self.sandbox.goto(url)
        elif hasattr(self.sandbox, "open"):
            self.sandbox.open(url)
        elif hasattr(self.sandbox, "commands"):
            chrome_cmd = (
                f"google-chrome --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage "
                f"--disable-gpu --no-first-run --no-default-browser-check {url}"
            )
            self.sandbox.commands.run(chrome_cmd, background=True)
        elif hasattr(self.sandbox, "launch"):
            self.sandbox.launch("google-chrome", url)

    async def fill_new_item_form(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drives the Computer Use vision loop to fill the New Item form completely autonomously.
        Zero hardcoded coordinates.
        """
        # Formulate human-like instruction with the item details
        name = item_data.get("name", "New Item")
        item_type = item_data.get("type", "Goods")
        unit = item_data.get("unit", "")
        selling_price = item_data.get("selling_price", "")
        cost_price = item_data.get("cost_price", "")
        sales_desc = item_data.get("sales_description") or item_data.get("description", "")
        purchase_desc = item_data.get("purchase_description") or item_data.get("description", "")

        goal_prompt = (
            f"You are looking at the Zoho Books 'New Item' creation form.\n"
            f"Please fill out the following item details:\n"
            f"- Name*: '{name}'\n"
            f"- Type: '{item_type}' (Select Goods or Service radio button)\n"
            f"- Unit: '{unit}' (Type into Unit dropdown if provided)\n"
            f"- Selling Price*: '{selling_price}' (under Sales Information)\n"
            f"- Sales Description: '{sales_desc}'\n"
            f"- Cost Price*: '{cost_price}' (under Purchase Information)\n"
            f"- Purchase Description: '{purchase_desc}'\n\n"
            f"Do NOT click the blue Save button yet. When all requested fields are filled, call task_completed."
        )

        return await self.agent.run_vision_loop(goal=goal_prompt, max_turns=12)

    async def submit_save(self) -> Dict[str, Any]:
        """Uses the vision loop to locate and click the blue [Save] button."""
        goal_prompt = (
            "You are looking at the completed Zoho Books 'New Item' form. "
            "Locate the primary blue 'Save' button at the bottom-left of the form, "
            "click it to submit the new item, then call task_completed."
        )
        return await self.agent.run_vision_loop(goal=goal_prompt, max_turns=5)
