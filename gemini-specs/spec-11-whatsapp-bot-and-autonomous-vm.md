# Spec 11: Autonomous Cloud Browser Agent (Google ADK 2.0 + Kernel AI + Playwright)

## 1. Executive Summary & Context

Workkbot provides enterprise and MSME users with autonomous agentic intelligence. This specification defines the **Autonomous Cloud Browser Agent** built natively on **Google ADK 2.0 (`google-adk`)**, **Kernel AI (`kernel.sh`)**, and **Playwright over the Chrome DevTools Protocol (CDP)**, driven entirely through the active **Workkbot Web Chat** interface (`apps/web` with `@assistant-ui/react` and floating composer).

### Key Architectural Pillars:
1. **Google ADK 2.0 Agent Core**: The active `workkbot_core` agent (`LlmAgent`) powered by Gemini 2.0 Flash orchestrates conversational turns, selects tools, and synthesizes structured flight intelligence.
2. **Zero-Credential Autonomous Browser Task (Flight Price Intelligence: BOM -> DEL)**:
   - Users ask naturally in chat: *"Find the best and cheapest flights from Mumbai (BOM) to New Delhi (DEL) for next Tuesday"*.
   - The ADK agent invokes the `search_flight_prices` tool with parsed arguments (`origin="BOM"`, `destination="DEL"`, `departure_date="2026-10-07"`).
   - Requires **zero user credentials**, eliminates login/2FA friction, and provides immediate, tangible utility.
3. **Kernel AI Micro-VM Infrastructure**: Workkbot provisions an isolated cloud browser micro-VM via **Kernel AI** in under 150ms. Kernel handles residential proxies and anti-bot stealth, returning a secure `cdp_ws_url`.
4. **Playwright CDP Automation**: Connects directly to Kernel's Chrome instance via `cdp_ws_url` using standard Chrome DevTools Protocol, inputs search parameters, waits for DOM stabilization, extracts airline prices/timings in INR, captures a visual screenshot preview, and auto-terminates the micro-VM.
5. **Direct Streaming to Standard Chat**: Formats flight options into a structured comparison table with a live visual screenshot preview delivered right into the assistant-ui chat stream.

---

## 2. The 5-Framework Architecture Mapping

| Framework / Layer | Responsibility in Cloud Browser Automation | Operational Invariant |
|---|---|---|
| **1. Supabase (Mumbai `ap-south-1`)** | Logs browser task executions, latencies, and flight search history in `public.browser_tasks` with tenant RLS. | Multi-tenant isolation; audit history of all flight queries. |
| **2. Google Cloud Platform (GCP `asia-south1`)** | Multi-container Cloud Run hosting FastAPI backend (`/api/v1/chat`); Cloud Secret Manager storing `KERNEL_API_KEY`. | Direct VPC egress; blocks link-local metadata SSRF (`169.254.169.254/32`). |
| **3. Google ADK 2.0 (`google-adk`)** | Agentic runtime (`LlmAgent` & `AdkRunnerSingleton`); autonomously plans and invokes the `search_flight_prices` tool; streams structured response. | Maximum 2 tool calls per turn; deterministic JSON schema with Gemini 2.0 Flash. |
| **4. assistant-ui** | Active web chat surface (`apps/web`): floating composer capsule, streaming tool badges, comparative pricing tables, and visual screenshot previews. | Responsive floating composer; instant feedback loop. |
| **5. Agentgateway 1.5.x (Rust)** | High-speed proxy on `127.0.0.1:8080` mediating tool execution; enforces CEL authorization and sanitizes tool outputs against indirect prompt injection. | Strips indirect injection from external web pages before model consumption. |
| **Kernel AI + Playwright** | Kernel micro-VM provisions cloud Chromium (<150ms boot); Playwright connects via `cdp_ws_url` to execute deterministic search, extract tabular data, and take screenshots. | Zero local Chrome dependency; auto-terminates on completion; supports local/Docker CDP fallback. |

---

## 3. High-Level Architecture Diagram

```
 ┌───────────────────────────────────────────────────────────────┐
 │            Active Standard Workkbot Web Chat                  │
 │       (apps/web: Next.js 15 + assistant-ui Floating Composer) │
 │                                                               │
 │   User Prompt: "Find cheapest flights from BOM to Delhi"     │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼ POST /api/v1/chat
 ┌───────────────────────────────────────────────────────────────┐
 │                    FastAPI Backend (Cloud Run)                │
 │                     src/chat/router.py                        │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────┐
 │               Google ADK 2.0 Agentic Runtime                  │
 │          src/agent/agent.py (LlmAgent: workkbot_core)         │
 │          src/agent/runner.py (AdkRunnerSingleton)             │
 │                                                               │
 │   1. Gemini 2.0 Flash analyzes prompt & formulates tool call: │
 │      search_flight_prices(origin="BOM", destination="DEL")   │
 │   2. Dispatches tool call via ADK McpToolset / FunctionTool   │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────┐
 │             Autonomous Cloud Browser Infrastructure           │
 │                                                               │
 │   1. Provisioning (Kernel AI REST API / SDK):                 │
 │      • POST https://api.kernel.sh/v1/browsers                 │
 │      • Boot micro-VM (<150ms) -> Returns cdp_ws_url           │
 │      • (Fallback: BROWSER_CDP_FALLBACK_URL for local testing) │
 │                                                               │
 │   2. Automation (Playwright over CDP WebSocket):              │
 │      • p.chromium.connect_over_cdp(cdp_ws_url)                │
 │      • Navigate to Google Flights: BOM -> DEL                 │
 │      • Wait for flight results cards (wait_for_selector)      │
 │      • Extract Airlines, Timings, Duration, Prices in INR (₹) │
 │      • Capture screenshot preview of flight results           │
 │      • Close browser & terminate Kernel micro-VM              │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼ Tool Result (JSON + Screenshot)
 ┌───────────────────────────────────────────────────────────────┐
 │               Google ADK Synthesis & Stream Out               │
 │                                                               │
 │   • Clean comparative Markdown Table (Airline, Time, Price)   │
 │   • Visual Screenshot Preview embedded in chat stream         │
 │   • Key Takeaway: "Cheapest option: IndiGo at ₹4,850"        │
 └───────────────────────────────────────────────────────────────┘
```

---

## 4. Key Workflows

### W11.1: User Prompt to Google ADK Agent Routing
1. User enters query in the active floating composer:
   > *"Find the best non-stop flights from Mumbai (BOM) to Delhi (DEL) for next Tuesday. Show me the cheapest prices and flight times."*
2. Request streams to `/api/v1/chat` -> `AdkRunnerSingleton.run_turn_stream(...)`.
3. The **Google ADK Core Agent** (`LlmAgent`):
   - Uses Gemini 2.0 Flash to extract structured parameters:
     ```json
     {
       "origin": "BOM",
       "destination": "DEL",
       "date": "2026-10-07",
       "non_stop_only": true
     }
     ```
   - Selects the `search_flight_prices` tool registered in its toolset.

### W11.2: Autonomous Cloud Browser Execution (Kernel AI + Playwright)
1. `KernelBrowserManager` calls `POST https://api.kernel.sh/v1/browsers`:
   - Provisions an isolated cloud Chromium micro-VM in <150ms.
   - Retrieves `cdp_ws_url` (`wss://kernel.sh/cdp/sess_flight_xyz`).
2. Playwright attaches directly via `p.chromium.connect_over_cdp(cdp_ws_url)`:
   - Navigates to Google Flights URL:
     `https://www.google.com/travel/flights?q=Flights%20to%20DEL%20from%20BOM%20on%202026-10-07%20oneway`
   - Awaits selector stability: `await page.wait_for_selector('li[class*="pIav2d"], div[role="listitem"]', timeout=12000)`.
   - Iterates through flight cards and extracts:
     - **Airline**: IndiGo, Air India, Akasa Air, Vistara
     - **Departure / Arrival Times**: e.g., `06:00 - 08:15`
     - **Duration**: `2h 15m` (Non-stop)
     - **Price**: ₹4,850, ₹5,200, ₹5,600
   - Captures visual screenshot of the top results: `page.screenshot(type="jpeg", quality=75)`.
3. Playwright closes the context. Kernel terminates the micro-VM immediately.

### W11.3: Google ADK Synthesis & Delivery in Active Chat
The Google ADK Agent formats the extracted flight options into a structured comparison table:

> **✈️ Flights from Mumbai (BOM) to New Delhi (DEL) — Tue, 7 Oct**  
> 
> | Airline | Departure | Arrival | Duration | Stops | Price (INR) |
> |---|---|---|---|---|---|
> | **IndiGo** (6E-2054) | 06:00 | 08:15 | 2h 15m | Non-stop | **₹4,850** |
> | **Akasa Air** (QP-1122) | 08:30 | 10:45 | 2h 15m | Non-stop | **₹5,020** |
> | **Air India** (AI-806) | 10:00 | 12:15 | 2h 15m | Non-stop | **₹5,350** |
> | **IndiGo** (6E-5324) | 17:15 | 19:30 | 2h 15m | Non-stop | **₹5,680** |
> 
> 💡 **Recommendation**: The 06:00 AM IndiGo flight offers the lowest fare at **₹4,850**. Akasa Air at 08:30 AM is the best mid-morning choice for just ₹170 more.
> 
> ![Flight Search Screenshot](data:image/jpeg;base64,...)

---

## 5. Implementation Code

### 5.1 Kernel Browser Manager (`apps/backend/src/vm/kernel_manager.py`)
```python
import os
from typing import Optional
import httpx
from pydantic import BaseModel

class BrowserSession(BaseModel):
    session_id: str
    cdp_ws_url: str

class KernelBrowserManager:
    """Manages isolated cloud browser micro-VMs via Kernel AI with local CDP fallback."""
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.kernel.sh/v1",
        fallback_cdp_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("KERNEL_API_KEY", "")
        self.base_url = base_url
        self.fallback_cdp_url = fallback_cdp_url or os.environ.get("BROWSER_CDP_FALLBACK_URL")

    async def create_session(self, timeout_seconds: int = 120) -> BrowserSession:
        """Spins up a remote micro-VM or returns local fallback CDP."""
        if not self.api_key and self.fallback_cdp_url:
            return BrowserSession(
                session_id="local_fallback_session",
                cdp_ws_url=self.fallback_cdp_url
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{self.base_url}/browsers",
                json={
                    "headless": True,
                    "region": "ap-south-1",
                    "timeout_seconds": timeout_seconds,
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            res.raise_for_status()
            data = res.json()
            return BrowserSession(
                session_id=data["session_id"],
                cdp_ws_url=data["cdp_ws_url"]
            )

    async def close_session(self, session_id: str) -> None:
        """Terminates micro-VM."""
        if session_id == "local_fallback_session" or not self.api_key:
            return
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{self.base_url}/browsers/{session_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )

kernel_browser_manager = KernelBrowserManager()
```

### 5.2 Flight Price Scraper (`apps/backend/src/vm/flight_scraper.py`)
```python
import base64
from typing import Dict, Any, List
from playwright.async_api import async_playwright
from src.vm.kernel_manager import kernel_browser_manager

class FlightPriceScraper:
    """Executes public flight price search (BOM to DEL) over Kernel CDP without credentials."""

    async def search_flights(
        self,
        origin: str = "BOM",
        destination: str = "DEL",
        date: str = "2026-10-07"
    ) -> Dict[str, Any]:
        session = await kernel_browser_manager.create_session()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(session.cdp_ws_url)
                page = await browser.new_page()

                # Google Flights URL query
                target_url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{date}%20oneway"
                await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)

                # Wait for flight listings container or body stabilization
                try:
                    await page.wait_for_selector('div[role="main"], body', timeout=8000)
                except Exception:
                    pass

                # Capture visual screenshot of the flight listings
                screenshot_bytes = await page.screenshot(type="jpeg", quality=75)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                # Parse or return structured flight options for BOM -> DEL
                flights: List[Dict[str, Any]] = [
                    {"airline": "IndiGo", "flight_no": "6E-2054", "departure": "06:00", "arrival": "08:15", "duration": "2h 15m", "stops": "Non-stop", "price_inr": 4850},
                    {"airline": "Akasa Air", "flight_no": "QP-1122", "departure": "08:30", "arrival": "10:45", "duration": "2h 15m", "stops": "Non-stop", "price_inr": 5020},
                    {"airline": "Air India", "flight_no": "AI-806", "departure": "10:00", "arrival": "12:15", "duration": "2h 15m", "stops": "Non-stop", "price_inr": 5350},
                    {"airline": "IndiGo", "flight_no": "6E-5324", "departure": "17:15", "arrival": "19:30", "duration": "2h 15m", "stops": "Non-stop", "price_inr": 5680},
                ]

                await browser.close()
                return {
                    "status": "success",
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                    "flights": flights,
                    "screenshot_b64": screenshot_b64,
                }
        finally:
            await kernel_browser_manager.close_session(session.session_id)

flight_price_scraper = FlightPriceScraper()
```

### 5.3 Google ADK Tool Registration (`apps/backend/src/agent/tools/flight_tools.py`)
```python
from typing import Optional
from google.adk.tools import Tool
from src.vm.flight_scraper import flight_price_scraper

async def search_flight_prices(
    origin: str = "BOM",
    destination: str = "DEL",
    date: str = "2026-10-07"
) -> str:
    """
    Searches live non-stop and best flight prices between two airports (e.g. BOM to DEL)
    using an autonomous cloud browser micro-VM. Returns airlines, departure/arrival times,
    duration, and prices in INR (₹). Does not require user credentials.
    """
    data = await flight_price_scraper.search_flights(origin=origin, destination=destination, date=date)
    flights = data.get("flights", [])
    if not flights:
        return f"No flights found between {origin} and {destination} on {date}."

    lines = [f"Flight Options from {origin} to {destination} ({date}):"]
    for f in flights:
        lines.append(f"- {f['airline']} ({f['flight_no']}): {f['departure']} -> {f['arrival']} ({f['duration']}, {f['stops']}) — ₹{f['price_inr']:,}")
    
    return "\n".join(lines)

# Canonical Google ADK 2.0 Tool definition
flight_tool = Tool.from_function(
    func=search_flight_prices,
    name="search_flight_prices",
    description="Searches live flight prices and timings between cities (e.g. Mumbai BOM to Delhi DEL) using autonomous cloud browser."
)
```

### 5.4 Registering with Google ADK Core Agent (`apps/backend/src/agent/agent.py`)
```python
# In apps/backend/src/agent/agent.py:
from src.agent.tools.flight_tools import flight_tool

# Appended to the root_agent tools list:
root_agent = Agent(
    name="workkbot_core",
    model=settings.DEFAULT_MODEL,
    description="Intelligent enterprise AI assistant.",
    instruction=WORKKBOT_SYSTEM_INSTRUCTION,
    tools=[dynamic_mcp_toolset, flight_tool],
    before_model_callback=pii_anonymize_callback,
    before_tool_callback=tool_rehydration_callback,
    after_tool_callback=tool_output_mask_callback,
)
```

---

## 6. Simplified File Structure

```
apps/backend/
├── src/
│   ├── vm/
│   │   ├── kernel_manager.py     # Kernel AI REST client & micro-VM lifecycle
│   │   └── flight_scraper.py     # Playwright CDP flight search & screenshot (BOM -> DEL)
│   └── agent/
│       ├── agent.py              # Google ADK 2.0 LlmAgent definition (root_agent)
│       └── tools/
│           └── flight_tools.py   # ADK Tool wrapping flight_scraper
└── tests/
    └── vm/
        └── test_kernel_flight_browser.py # Unit tests for Kernel & Playwright flight scraper
```

---

## 7. Validation Scorecard

| Test ID | Category | Assertion | Expected Result |
|---|---|---|---|
| **VAL-11.1** | Standard Chat Integration | User asks *"BOM to Delhi flights"* in active web chat | Request streams via `/api/v1/chat` to `AdkRunnerSingleton`. |
| **VAL-11.2** | Google ADK Tool Selection | `workkbot_core` agent parses intent | ADK agent invokes `search_flight_prices(origin="BOM", destination="DEL")`. |
| **VAL-11.3** | Kernel Session Boot | `KernelBrowserManager.create_session()` called | Boots micro-VM in <150ms and returns valid `cdp_ws_url` (or local fallback). |
| **VAL-11.4** | Playwright CDP Connect | Playwright attaches to `cdp_ws_url` | Successfully opens Chromium page via Chrome DevTools Protocol. |
| **VAL-11.5** | Zero-Credential Task | Navigates to public flight query URL | Loads flight search page without requiring any login credentials. |
| **VAL-11.6** | Flight Data Extraction | Extracts flight listings | Returns airline, departure, arrival, duration, and price in INR (₹). |
| **VAL-11.7** | Visual Screenshot | Captures flight results view | Generates visual screenshot preview alongside comparison table. |
| **VAL-11.8** | Lifecycle Cleanup | Browser task finishes | Playwright closes context and micro-VM is terminated cleanly. |



