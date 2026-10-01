"""Universal Ref-Based Browser CDP Automation Engine (Spec 11).

Operates on ANY website (Zoho Books, Vyapar, Shopify, Amazon, GST Portal, Stripe)
over Kernel Cloud Browser via Chrome DevTools Protocol (CDP).
Zero hardcoded website scripts. Zero expensive screenshots.

Implements the official Microsoft @playwright/mcp accessibility snapshot architecture:
1. `snapshot()` stamps temporary `[data-workkbot-ref="e1"]` attributes on all interactive DOM nodes
   and returns a compact, semantic accessibility tree with refs (~150-300 tokens).
2. `click(ref)` / `fill(ref, value)` targets elements directly by their ref or semantic label.
3. `auto_fill_form(data)` semantically maps key-value payloads to visible form fields on ANY site.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("workkbot.vm.universal_browser")


class UniversalBrowserSession:
    """Universal CDP browser controller providing ref-based accessibility automation."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox
        self._last_snapshot: List[Dict[str, Any]] = []

    async def get_page(self):
        """Retrieves the active Playwright Page connected over Kernel CDP."""
        if hasattr(self.sandbox, "get_page"):
            return await self.sandbox.get_page()
        elif hasattr(self.sandbox, "ensure_connected"):
            return await self.sandbox.ensure_connected()
        return None

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigates browser to any URL over CDP."""
        logger.info("Universal browser navigating to: %s", url)
        page = await self.get_page()
        if page:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                if hasattr(page, "wait_for_selector"):
                    await page.wait_for_selector("body", state="visible", timeout=10000)
            except Exception:
                pass
            return {"status": "success", "url": getattr(page, "url", url)}
        elif hasattr(self.sandbox, "async_goto"):
            await self.sandbox.async_goto(url)
        elif hasattr(self.sandbox, "goto"):
            self.sandbox.goto(url)
        return {"status": "simulated", "url": url}

    async def snapshot(self) -> Dict[str, Any]:
        """
        Interrogates the browser over CDP, stamps unique `data-workkbot-ref` IDs
        on all visible interactive elements, and returns a pruned semantic tree.
        """
        page = await self.get_page()
        if not page:
            return {"status": "error", "message": "No active browser page", "elements": [], "snapshot_text": ""}

        js_stamp_script = """
        () => {
            const selectors = 'button, a, input, select, textarea, [role="button"], [role="radio"], [role="checkbox"], [role="combobox"], [role="link"], [role="tab"], [contenteditable="true"]';
            const nodes = Array.from(document.querySelectorAll(selectors));
            const elements = [];
            let counter = 1;

            for (const el of nodes) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                const style = window.getComputedStyle(el);
                if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') continue;

                const refId = `e${counter++}`;
                el.setAttribute('data-workkbot-ref', refId);

                let label = '';
                if (el.labels && el.labels.length > 0) {
                    label = el.labels[0].innerText;
                } else if (el.id) {
                    const lbl = document.querySelector(`label[for="${el.id}"]`);
                    if (lbl) label = lbl.innerText;
                }
                if (!label) {
                    const container = el.closest('.form-group, .row, tr, [class*="form-group"], [class*="field"], [class*="input-wrap"]');
                    if (container) {
                        const lbl = container.querySelector('label, [class*="label"], [class*="title"], [class*="header"]');
                        if (lbl && lbl !== el) label = lbl.innerText;
                    }
                }
                if (!label) {
                    const parentLabel = el.closest('label');
                    if (parentLabel) label = parentLabel.innerText;
                }
                if (!label) {
                    label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.innerText || el.name || '';
                }

                elements.push({
                    ref: refId,
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    role: el.getAttribute('role') || el.type || el.tagName.toLowerCase(),
                    label: label.replace(/[\\r\\n\\t]+/g, ' ').trim().slice(0, 100),
                    placeholder: el.getAttribute('placeholder') || '',
                    value: el.value || '',
                    checked: el.checked || false,
                    disabled: el.disabled || false
                });
            }
            return elements;
        }
        """
        try:
            elements = await page.evaluate(js_stamp_script)
            self._last_snapshot = elements

            # Build formatted markdown snapshot text
            lines = []
            for el in elements:
                desc = f"[ref={el['ref']}] {el['role']} \"{el['label']}\""
                if el.get("checked"):
                    desc += " (checked: true)"
                elif el.get("value"):
                    desc += f" (value: \"{el['value']}\")"
                elif el.get("placeholder"):
                    desc += f" (placeholder: \"{el['placeholder']}\")"
                lines.append(desc)

            snapshot_text = "\n".join(lines)
            logger.info("Universal browser snapshot stamped %d interactive elements", len(elements))
            return {
                "status": "success",
                "count": len(elements),
                "elements": elements,
                "snapshot_text": snapshot_text,
            }
        except Exception as e:
            logger.error("Snapshot evaluation failed: %s", e)
            return {"status": "error", "message": str(e), "elements": [], "snapshot_text": ""}

    async def click(self, ref_or_label: str) -> Dict[str, Any]:
        """Clicks an element by its [ref=eX] identifier or fuzzy semantic label."""
        page = await self.get_page()
        if not page:
            return {"status": "error", "message": "No browser page"}

        logger.info("Universal browser click: '%s'", ref_or_label)
        target = ref_or_label.strip()

        # 1. Direct stamped ref lookup
        if target.startswith("e") and target[1:].isdigit():
            loc = page.locator(f'[data-workkbot-ref="{target}"]').first
            if await loc.count() > 0:
                await loc.click()
                return {"status": "clicked", "ref": target, "method": "ref"}

        # 2. Semantic label / role lookup
        try:
            loc = page.get_by_role("button", name=target, exact=False).first
            if await loc.count() > 0:
                await loc.click()
                return {"status": "clicked", "target": target, "method": "role_button"}
        except Exception:
            pass

        # 3. Text / label container lookup
        loc = page.locator(
            f'button:has-text("{target}"), [role="button"]:has-text("{target}"), label:has-text("{target}")'
        ).first
        if await loc.count() > 0:
            await loc.click()
            return {"status": "clicked", "target": target, "method": "text"}

        return {"status": "not_found", "target": target}

    async def fill(self, ref_or_label: str, value: str) -> Dict[str, Any]:
        """Fills an input or textarea by its [ref=eX] identifier or fuzzy label."""
        page = await self.get_page()
        if not page:
            return {"status": "error", "message": "No browser page"}

        logger.info("Universal browser fill: '%s' with '%s'", ref_or_label, value)
        target = ref_or_label.strip()

        loc = None
        method = "unknown"

        # 1. Direct stamped ref lookup
        if target.startswith("e") and target[1:].isdigit():
            ref_loc = page.locator(f'[data-workkbot-ref="{target}"]').first
            if await ref_loc.count() > 0:
                loc = ref_loc
                method = "ref"

        # 2. Semantic label lookup
        if not loc:
            try:
                label_loc = page.get_by_label(target, exact=False).first
                if await label_loc.count() > 0:
                    loc = label_loc
                    method = "label"
            except Exception:
                pass

        # 3. Container / placeholder fallback
        if not loc:
            clean = target.rstrip("*").strip()
            cont_loc = page.locator(
                f'.form-group:has-text("{clean}") input, .form-group:has-text("{clean}") textarea, '
                f'input[placeholder*="{clean}"], textarea[placeholder*="{clean}"]'
            ).first
            if await cont_loc.count() > 0:
                loc = cont_loc
                method = "container_label"

        if loc:
            try:
                await loc.click()
            except Exception:
                pass
            await loc.fill(str(value))
            try:
                await loc.dispatch_event("input")
                await loc.dispatch_event("change")
                await loc.dispatch_event("blur")
            except Exception:
                pass
            return {"status": "filled", "target": target, "value": value, "method": method}

        return {"status": "not_found", "target": target}

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Presses a keyboard key (e.g. 'Enter', 'Tab', 'Escape')."""
        page = await self.get_page()
        if page and hasattr(page, "keyboard"):
            await page.keyboard.press(key)
            return {"status": "pressed", "key": key}
        return {"status": "unsupported"}

    async def auto_fill_form(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal semantic form filler for ANY website.
        Takes an arbitrary dict (e.g. {"name": "Basmati Rice", "selling_price": 450, ...}),
        snapshots the active page, maps the keys to the best matching refs, and fills them.
        """
        # 1. Stamp and snapshot elements
        snap = await self.snapshot()
        elements = snap.get("elements", [])
        if not elements:
            logger.warning("Auto-fill found 0 interactive elements on page")
            return {"status": "no_fields_found", "actions": []}

        actions_taken = []
        for key, raw_val in data.items():
            if raw_val is None or raw_val == "":
                continue
            val_str = str(raw_val)
            key_clean = key.lower().replace("_", " ").strip()

            # Find matching element in snapshot
            matched_el = None
            for el in elements:
                lbl = el.get("label", "").lower()
                role = el.get("role", "").lower()

                # Semantic label match
                if key_clean in lbl or (key_clean == "name" and "name" in lbl and "user" not in lbl):
                    matched_el = el
                    break
                elif key_clean in ("selling price", "rate", "price") and ("selling" in lbl or "rate" in lbl or "price" in lbl):
                    matched_el = el
                    break
                elif key_clean in ("cost price", "purchase rate", "cost") and ("cost" in lbl or "purchase" in lbl):
                    matched_el = el
                    break
                elif key_clean in ("unit", "uom") and "unit" in lbl:
                    matched_el = el
                    break
                elif key_clean in ("description", "desc", "notes") and "desc" in lbl:
                    matched_el = el
                    break
                elif key_clean == "type" and (val_str.lower() in lbl or val_str.lower() == el.get("value", "").lower()):
                    matched_el = el
                    break

            if matched_el:
                ref = matched_el["ref"]
                role = matched_el.get("role", "")
                if role in ("radio", "checkbox", "button"):
                    res = await self.click(ref)
                else:
                    res = await self.fill(ref, val_str)
                actions_taken.append({"key": key, "ref": ref, "label": matched_el.get("label"), "result": res})

        return {
            "status": "completed",
            "actions_count": len(actions_taken),
            "actions": actions_taken,
        }
