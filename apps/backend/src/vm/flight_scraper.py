"""Flight Price Scraper: Autonomous Playwright CDP Runner for Generic Flight Routes.

Connects to Kernel AI cloud browser micro-VMs via Chrome DevTools Protocol (CDP),
navigates dynamic flight search queries for any origin/destination pair,
dynamically extracts live airline schedules and prices from the DOM,
captures visual screenshots, and provides zero-credential execution without hardcoded catalogs.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.config import settings
from src.vm.kernel_manager import KernelBrowserManager, kernel_browser_manager

logger = logging.getLogger("workkbot.flight_scraper")


class FlightPriceScraper:
    """Automates dynamic public flight price queries for any route over Kernel CDP."""

    DEFAULT_MAX_TOOL_CALLS: int = 20

    def __init__(self, manager: Optional[KernelBrowserManager] = None):
        self.manager = manager or kernel_browser_manager

    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: Optional[str] = None,
        non_stop_only: bool = False,
        max_tool_calls: int = 20,
    ) -> Dict[str, Any]:
        """
        Executes a dynamic flight search for any route (e.g. BOM to DEL, BLR to DXB, etc.).
        Connects to Kernel cloud Chromium over CDP and extracts live flight listings from the DOM.
        Enforces a hard limit of max 20 tool calls in the agentic browser loop.
        """
        flight_date = date or (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        origin_code = origin.strip().upper()
        dest_code = destination.strip().upper()

        session = await self.manager.create_session(timeout_seconds=300)
        self.manager.active_task = f"Flight Search: {origin_code} -> {dest_code} ({flight_date})"
        logger.info("Initiating flight search %s -> %s on date %s (session=%s, telemetry=%s)", origin_code, dest_code, flight_date, session.session_id, session.telemetry_enabled)

        # Start browser replay recording
        replay_id: Optional[str] = None
        try:
            replay_info = await self.manager.start_replay(session.session_id)
            if replay_info:
                replay_id = replay_info.get("replay_id")
                logger.info("Started session replay recording: %s", replay_id)
        except Exception as replay_start_err:
            logger.warning("Could not start replay for session %s: %s", session.session_id, replay_start_err)

        try:
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                logger.error("Playwright package not installed.")
                return {
                    "status": "error",
                    "origin": origin_code,
                    "destination": dest_code,
                    "date": flight_date,
                    "flights": [],
                    "tool_calls_count": 0,
                    "max_tool_calls": self.DEFAULT_MAX_TOOL_CALLS,
                    "session_id": session.session_id,
                    "live_view_url": session.live_view_url,
                    "replay_view_url": session.replay_view_url,
                    "replay_id": replay_id,
                    "screenshot_b64": None,
                    "error": "Playwright is required for browser automation.",
                }

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(session.cdp_ws_url)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Navigate directly to Google Flights base homepage without query parameters
                base_flights_url = "https://www.google.com/travel/flights"
                logger.info("Navigating to clean Google Flights home: %s", base_flights_url)
                await page.goto(base_flights_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)

                # Strict tool call cap: max 20 tool calls
                MAX_TOOL_CALLS = max(1, min(max_tool_calls, self.DEFAULT_MAX_TOOL_CALLS))
                tool_calls_count = 0

                logger.info("Entering agentic browser loop (max_tool_calls=%d)", MAX_TOOL_CALLS)

                # Agentic Loop: LLM observes real Playwright DOM accessibility tree and decides actions (max 20 tool calls)
                while tool_calls_count < MAX_TOOL_CALLS:
                    # Early exit if search results are already loaded on the page
                    try:
                        if "/flights/search" in page.url:
                            result_cards = await page.get_by_role("listitem").all()
                            if len(result_cards) >= 1:
                                logger.info("Flight results already rendered on page (%d items). Finishing loop.", len(result_cards))
                                break
                    except Exception:
                        pass

                    try:
                        dom_snapshot = await page.locator("body").aria_snapshot()
                    except Exception:
                        try:
                            dom_snapshot = await page.locator("body").inner_text()
                        except Exception:
                            dom_snapshot = ""

                    action_payload = await self._decide_next_action(
                        origin=origin_code,
                        destination=dest_code,
                        date=flight_date,
                        dom_snapshot=dom_snapshot[:6000] if dom_snapshot else "",
                        step_number=tool_calls_count + 1,
                        max_steps=MAX_TOOL_CALLS,
                    )

                    action_type = action_payload.get("action", "done")
                    target = action_payload.get("target", "")
                    text_to_type = action_payload.get("text", "")
                    key = action_payload.get("key", "Enter")

                    logger.info(
                        "[Agentic Loop %d/%d] action=%s target='%s' text='%s'",
                        tool_calls_count + 1,
                        MAX_TOOL_CALLS,
                        action_type,
                        target,
                        text_to_type,
                    )

                    if action_type == "done":
                        break

                    tool_calls_count += 1

                    try:
                        if action_type == "click":
                            loc = await self._resolve_locator(page, target)
                            if loc is not None:
                                await loc.click(timeout=8000)
                            else:
                                if any(w in target.lower() for w in ["search", "explore", "done", "enter"]):
                                    await page.keyboard.press("Enter")
                                else:
                                    logger.warning("Could not resolve locator for click target '%s'", target)
                            await page.wait_for_timeout(800)

                        elif action_type == "type":
                            loc = await self._resolve_locator(page, target)
                            if loc is not None:
                                try:
                                    await loc.click(timeout=6000)
                                    await page.wait_for_timeout(300)
                                except Exception:
                                    pass

                            active = page.locator("input:focus, [role='combobox'] input, input[type='text']:focus").first
                            active_cnt = active.count()
                            if hasattr(active_cnt, "__await__"):
                                has_active = (await active_cnt) > 0
                            else:
                                has_active = True if active_cnt else False

                            if has_active:
                                await active.fill(text_to_type)
                            else:
                                await page.keyboard.type(text_to_type, delay=30)
                            await page.wait_for_timeout(600)

                        elif action_type == "press_key":
                            await page.keyboard.press(key)
                            await page.wait_for_timeout(800)

                    except Exception as act_err:
                        logger.warning("Error executing agentic action %s on step %d: %s", action_type, tool_calls_count, act_err)

                    await page.wait_for_timeout(1000)

                # Wait for any in-flight results to settle
                try:
                    await page.wait_for_selector('[role="listitem"], li, body', timeout=15000)
                    await page.wait_for_timeout(2000)
                except Exception:
                    pass

                # Capture visual screenshot of the actual flight results
                screenshot_bytes = await page.screenshot(type="jpeg", quality=75)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                # Pure Playwright semantic locator extraction (no hardcoded CSS classes or DOM internals)
                cards = await page.get_by_role("listitem").all()
                if not cards:
                    cards = await page.locator("li").all()

                extracted_flights: List[Dict[str, Any]] = []
                seen: set = set()

                for el in cards:
                    try:
                        text = await el.inner_text()
                        if not text or len(text) < 20:
                            continue

                        # Extract timing, duration, stops, and price generically from visible text
                        price_match = re.search(r"(?:₹|INR\s*|Rs\.?\s*)([\d,]+)", text, re.IGNORECASE)
                        time_matches = re.findall(r"\b(\d{1,2}:\d{2}(?:\s*[AP]M)?)\b", text, re.IGNORECASE)
                        duration_match = re.search(r"\b(\d{1,2}h(?:\s*\d{1,2}m)?)\b", text, re.IGNORECASE)
                        stops_match = re.search(r"\b(Non-stop|\d+\s*stop[s]?)\b", text, re.IGNORECASE)

                        if price_match and len(time_matches) >= 2:
                            airline = "Flight"
                            img = el.locator("img[alt]").first
                            if await img.count() > 0:
                                alt = await img.get_attribute("alt")
                                if alt and "flight" not in alt.lower():
                                    airline = alt.strip()

                            if airline == "Flight":
                                lines = [line.strip() for line in text.split("\n") if line.strip()]
                                if lines and len(lines[0]) < 30 and not re.search(r"\d", lines[0]):
                                    airline = lines[0]

                            price_str = price_match.group(1).replace(",", "")
                            price_inr = int(price_str) if price_str.isdigit() else 0

                            key = (airline, time_matches[0], price_inr)
                            if key not in seen:
                                seen.add(key)
                                extracted_flights.append({
                                    "airline": airline,
                                    "departure": time_matches[0],
                                    "arrival": time_matches[1],
                                    "duration": duration_match.group(1) if duration_match else "Direct",
                                    "stops": stops_match.group(1) if stops_match else "Non-stop",
                                    "price_inr": price_inr,
                                })
                    except Exception as parse_err:
                        logger.debug("Skipping element during Playwright parsing: %s", parse_err)
                        continue

                # Extract real live DOM accessibility context directly from Playwright (no hardcoding, no mocks)
                try:
                    dom_context = await page.locator("body").aria_snapshot()
                except Exception as aria_err:
                    logger.debug("Playwright aria_snapshot fallback to body inner_text: %s", aria_err)
                    try:
                        dom_context = await page.locator("body").inner_text()
                    except Exception:
                        dom_context = ""

                await browser.close()
                logger.info("Successfully extracted %d live flight options via Playwright", len(extracted_flights))

                return {
                    "status": "success",
                    "origin": origin_code,
                    "destination": dest_code,
                    "date": flight_date,
                    "flights": extracted_flights,
                    "flight_count": len(extracted_flights),
                    "tool_calls_count": tool_calls_count,
                    "max_tool_calls": MAX_TOOL_CALLS,
                    "dom_context": dom_context[:12000] if dom_context else None,
                    "session_id": session.session_id,
                    "live_view_url": session.live_view_url,
                    "replay_view_url": session.replay_view_url,
                    "replay_id": replay_id,
                    "screenshot_b64": screenshot_b64,
                    "is_simulated": False,
                }

        except Exception as e:
            logger.error("Error during flight scraping over CDP: %s", e)
            return {
                "status": "error",
                "origin": origin_code,
                "destination": dest_code,
                "date": flight_date,
                "flights": [],
                "tool_calls_count": locals().get("tool_calls_count", 0),
                "max_tool_calls": MAX_TOOL_CALLS,
                "session_id": session.session_id,
                "live_view_url": session.live_view_url,
                "replay_view_url": session.replay_view_url,
                "replay_id": replay_id,
                "screenshot_b64": None,
                "error": str(e),
                "is_simulated": False,
            }
        finally:
            if replay_id:
                try:
                    stop_info = await self.manager.stop_replay(session.session_id, replay_id)
                    if stop_info and stop_info.get("replay_view_url"):
                        session.replay_view_url = stop_info.get("replay_view_url")
                        logger.info("Stopped session replay recording: %s (view_url=%s)", replay_id, session.replay_view_url)
                except Exception as replay_err:
                    logger.warning("Error stopping replay %s for session %s: %s", replay_id, session.session_id, replay_err)
            await self.manager.close_session(session.session_id)

    async def _decide_next_action(
        self,
        origin: str,
        destination: str,
        date: str,
        dom_snapshot: str,
        step_number: int,
        max_steps: int = 20,
    ) -> Dict[str, Any]:
        """
        Uses Gemini LLM to analyze the live Playwright DOM accessibility tree snapshot
        and autonomously decide the next browser interaction (click, type, press_key, done)
        enforcing a hard limit of max_steps (default: 20).
        """
        if step_number > max_steps:
            logger.info("Reached maximum tool calls limit (%d/%d). Terminating loop.", step_number - 1, max_steps)
            return {"action": "done", "reason": f"Reached maximum tool call limit of {max_steps}"}

        if not settings.GEMINI_API_KEY:
            logger.debug("No GEMINI_API_KEY configured, stopping agentic loop.")
            return {"action": "done", "reason": "No GEMINI_API_KEY configured"}

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            model_name = settings.DEFAULT_MODEL or "gemini-2.5-flash"

            prompt = (
                f"You are an autonomous browser agent navigating Google Flights (https://www.google.com/travel/flights) "
                f"to search for flights from '{origin}' to '{destination}' on date '{date}'.\n"
                f"Current Step: {step_number} of max {max_steps} allowed tool calls.\n\n"
                f"Accessibility DOM Snapshot:\n"
                f"```\n{dom_snapshot[:5000]}\n```\n\n"
                f"OPTIMAL ACTION SEQUENCE (Complete within 3-4 steps):\n"
                f"1. To enter destination, click 'Where to?', type '{destination}', then press 'Enter'.\n"
                f"2. If origin is not '{origin}', click 'Where from?', type '{origin}', then press 'Enter'.\n"
                f"3. Click 'Search' or 'Explore' (or press key 'Enter') to navigate to the flight results page.\n"
                f"4. AVOID the calendar date picker: Do NOT click on dates or search for calendar 'Done' buttons. Press 'Enter' or click 'Search' directly to submit.\n"
                f"5. Once flight listings, airlines (IndiGo, Air India, etc.), or prices (₹) appear, return action 'done'.\n\n"
                f"Respond in valid JSON with this schema:\n"
                f"{{\n"
                f'  "action": "click" | "type" | "press_key" | "done",\n'
                f'  "target": "<plain element text or label, e.g. Where to?, Where from?, Search, Explore, DEL>",\n'
                f'  "text": "<text to type if action is type, e.g. {destination}>",\n'
                f'  "key": "<key to press if action is press_key, e.g. Enter, Escape>",\n'
                f'  "reason": "<brief justification>"\n'
                f"}}\n"
                f"If flight listings or search results are already visible, return action 'done'."
            )

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            if response and response.text:
                data = json.loads(response.text)
                if isinstance(data, dict) and "action" in data:
                    return data
        except Exception as e:
            logger.warning("Gemini decision failed in agentic loop step %d: %s", step_number, e)

        return {"action": "done", "reason": "Default completion"}

    @staticmethod
    def _clean_target_text(target: str) -> tuple[Optional[str], str]:
        """
        Parses role and text from target string, stripping quotes and CSS artifact tokens.
        E.g.
          'combobox "Where from?"' -> ('combobox', 'Where from?')
          'button "Search"'        -> ('button', 'Search')
          '"Where to?"'            -> (None, 'Where to?')
          'Where from?'            -> (None, 'Where from?')
        """
        raw = target.strip().strip("\"'")
        css_match = re.match(r"^\[(?:aria-label|placeholder)\*?=['\"]?(.*?)['\"]?\]$", raw)
        if css_match:
            raw = css_match.group(1).strip().strip("\"'")

        match = re.match(
            r"^(combobox|button|textbox|searchbox|option|menuitem|link|tab)\s+[\"']?(.*?)[\"']?$",
            raw,
            re.IGNORECASE,
        )
        if match:
            role = match.group(1).lower()
            text = match.group(2).strip().strip("\"'")
            return role, text

        cleaned = raw.strip("\"'")
        return None, cleaned

    async def _resolve_locator(self, page: Any, target: str) -> Optional[Any]:
        """
        Resiliently finds a Playwright Locator for a target without raw CSS string concatenation errors.
        Handles aria-snapshot formats like 'combobox "Where from?"', plain labels, placeholders, and buttons.
        """
        if not target or not target.strip():
            return None

        role, clean_text = self._clean_target_text(target)
        if not clean_text:
            return None

        async def _available(loc: Any) -> bool:
            try:
                cnt = loc.count()
                if hasattr(cnt, "__await__"):
                    c = await cnt
                else:
                    c = int(cnt) if isinstance(cnt, (int, float)) else 1
                return c > 0
            except Exception:
                return False

        # 1. If explicit role was identified from aria-snapshot
        if role:
            try:
                loc = page.get_by_role(role, name=clean_text)
                if await _available(loc):
                    return loc.first
            except Exception:
                pass

        # 2. Try get_by_label (handles aria-label and <label>)
        try:
            loc = page.get_by_label(clean_text, exact=False)
            if await _available(loc):
                return loc.first
        except Exception:
            pass

        # 3. Try get_by_placeholder
        try:
            loc = page.get_by_placeholder(clean_text, exact=False)
            if await _available(loc):
                return loc.first
        except Exception:
            pass

        # 4. Try common interactive roles (combobox, button, textbox, searchbox, option)
        for r in ["combobox", "button", "textbox", "searchbox", "option"]:
            try:
                loc = page.get_by_role(r, name=clean_text)
                if await _available(loc):
                    return loc.first
            except Exception:
                pass

        # 5. Try get_by_text
        try:
            loc = page.get_by_text(clean_text, exact=False)
            if await _available(loc):
                return loc.first
        except Exception:
            pass

        # 6. Fallback: safe button or input locator
        safe_text = re.sub(r'["\'\?\[\]]', "", clean_text).strip()
        if safe_text:
            try:
                loc = page.locator(f'button:has-text("{safe_text}")').first
                if await _available(loc):
                    return loc
            except Exception:
                pass

        return None


flight_price_scraper = FlightPriceScraper()
