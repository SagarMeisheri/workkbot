"""Google ADK 2.0 Cloud Browser Flight Search Tool (Spec 11).

Defines the search_flight_prices BaseTool for Google ADK 2.0 agents.
Enables autonomous flight pricing and schedule intelligence (BOM -> DEL)
over Kernel AI cloud browser micro-VMs via Playwright CDP.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.vm.flight_scraper import FlightPriceScraper, flight_price_scraper

logger = logging.getLogger("workkbot.flight_tools")

FLIGHT_SEARCH_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "origin": {
            "type": "string",
            "description": "3-letter IATA airport code for origin city (e.g. BOM for Mumbai, DEL for Delhi).",
        },
        "destination": {
            "type": "string",
            "description": "3-letter IATA airport code for destination city (e.g. DEL for Delhi, BOM for Mumbai).",
        },
        "date": {
            "type": "string",
            "description": "Departure date in YYYY-MM-DD format (e.g. 2026-10-07). Defaults to 7 days ahead.",
        },
        "non_stop_only": {
            "type": "boolean",
            "description": "Whether to filter for direct non-stop flights only. Defaults to true.",
        },
    },
    "required": ["origin", "destination"],
}


try:
    from google.adk.tools import BaseTool
    from google.genai import types

    class FlightSearchTool(BaseTool):
        """Google ADK 2.0 BaseTool for autonomous flight price search over Kernel CDP."""

        def __init__(self, scraper: Optional[FlightPriceScraper] = None):
            super().__init__(
                name="search_flight_prices",
                description="Searches live flight prices, airlines, and timings between cities (e.g. Mumbai BOM to Delhi DEL) using autonomous cloud browser."
            )
            self.scraper = scraper or flight_price_scraper

        def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema=FLIGHT_SEARCH_SCHEMA,
            )

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            """Executes flight price search via Kernel AI micro-VM."""
            origin = args.get("origin", "BOM")
            destination = args.get("destination", "DEL")
            date = args.get("date")
            non_stop = args.get("non_stop_only", True)

            logger.info("Executing search_flight_prices: origin=%s, destination=%s, date=%s", origin, destination, date)
            result = await self.scraper.search_flights(
                origin=origin,
                destination=destination,
                date=date,
                non_stop_only=non_stop,
            )

            flights = result.get("flights", [])
            lines = [
                f"Flight Search Results: {result.get('origin', origin)} -> {result.get('destination', destination)} on {result.get('date', 'selected date')}:"
            ]
            if not flights:
                lines.append("No flights found or automated search returned no live options.")
            for f in flights:
                flight_no_str = f" ({f['flight_no']})" if f.get("flight_no") else ""
                lines.append(
                    f"- {f.get('airline', 'Flight')}{flight_no_str}: Departure {f.get('departure', 'N/A')} -> Arrival {f.get('arrival', 'N/A')} "
                    f"({f.get('duration', 'N/A')}, {f.get('stops', 'N/A')}) — ₹{f.get('price_inr', 0):,}"
                )

            summary_text = "\n".join(lines)
            return {
                "status": "success",
                "summary": summary_text,
                "origin": result["origin"],
                "destination": result["destination"],
                "date": result["date"],
                "flight_count": len(flights),
                "flights": flights,
                "dom_context": result.get("dom_context"),
                "live_view_url": result.get("live_view_url"),
                "has_screenshot": result.get("screenshot_b64") is not None,
                "screenshot_b64": result.get("screenshot_b64"),
                "is_simulated": result.get("is_simulated", False),
            }

except ImportError:
    # Fallback for environments without google-adk
    class FlightSearchTool:  # type: ignore
        def __init__(self, scraper: Optional[FlightPriceScraper] = None):
            self.name = "search_flight_prices"
            self.description = "Searches live flight prices between cities using autonomous cloud browser."
            self.scraper = scraper or flight_price_scraper

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            return await self.scraper.search_flights(
                origin=args.get("origin", "BOM"),
                destination=args.get("destination", "DEL"),
                date=args.get("date"),
            )


flight_tool = FlightSearchTool()
