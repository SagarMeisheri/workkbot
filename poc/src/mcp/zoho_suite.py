"""
Workkbot Local PoC: Zoho MCP Server Provider
Implements Zoho tools with strict Live REST APIs via OAuth Bearer tokens.
Tools are dynamically discovered only when authenticated via OAuth.
"""
import datetime
import json
from typing import Any, Dict, List, Optional
import httpx
from src.mcp.client_vault import ClientVault
from src.mcp.models import McpTool, McpCallResult


class ZohoMcpProvider:
    """
    Zoho Suite MCP Server client.
    Supports Zoho CRM, Zoho Books, and Zoho Desk tools.
    """

    def __init__(self, vault: ClientVault):
        self.vault = vault
        self._manual_enabled = True
        self._discovered_tools: List[McpTool] = []

    @property
    def is_connected(self) -> bool:
        """
        Dynamically connected only when user has enabled it AND authenticated via OAuth.
        """
        return self._manual_enabled and self.vault.is_zoho_authenticated()

    @is_connected.setter
    def is_connected(self, value: bool):
        self._manual_enabled = value
        if not value:
            self._discovered_tools = []

    def discover_tools(self) -> List[McpTool]:
        """
        Dynamically discovers tools from the connected Zoho MCP Server Gateway or
        authenticated OAuth session after client connects.
        """
        if not self.is_connected:
            self._discovered_tools = []
            return []

        token = self.vault.get_zoho_access_token()
        server_url = getattr(self.vault.zoho, "server_url", "https://mcp.zoho.com")

        # 1. Query remote Zoho MCP Server via tools/list protocol
        if server_url:
            try:
                headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{server_url}/tools/list",
                        headers=headers,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        tools_data = payload.get("result", {}).get("tools", [])
                        parsed = []
                        for t in tools_data:
                            name = t.get("name", "")
                            is_mut = any(act in name.lower() for act in ["create", "update", "record", "delete", "post"])
                            parsed.append(
                                McpTool(
                                    name=name,
                                    description=t.get("description", ""),
                                    input_schema=t.get("inputSchema", {}),
                                    server="zoho_mcp",
                                    category="Zoho Suite",
                                    is_mutating=is_mut,
                                )
                            )
                        if parsed:
                            self._discovered_tools = parsed
                            return self._discovered_tools
            except Exception:
                pass

        # 2. Dynamic discovery based on active OAuth scopes granted by the connected client
        tools: List[McpTool] = []
        scopes = self.vault.zoho.scopes

        # Dynamically discover CRM tools if CRM scopes authorized
        if any("crm" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="zoho_crm.search_records",
                    description="Searches records (Leads, Deals, Accounts, Contacts) across Zoho CRM.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "module": {"type": "string", "enum": ["Leads", "Deals", "Accounts", "Contacts"]},
                            "query": {"type": "string", "description": "Search criteria or entity name"},
                        },
                        "required": ["module", "query"],
                    },
                    server="zoho_mcp",
                    category="Zoho CRM",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_crm.create_lead",
                    description="Creates a new qualified lead in Zoho CRM. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "company": {"type": "string"},
                            "email": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["first_name", "last_name", "company", "email"],
                    },
                    server="zoho_mcp",
                    category="Zoho CRM",
                    is_mutating=True,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_crm.update_deal",
                    description="Updates a Deal's stage, closing amount, or notes in Zoho CRM. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string"},
                            "stage": {"type": "string"},
                            "amount": {"type": "number"},
                            "notes": {"type": "string"},
                        },
                        "required": ["deal_id", "stage"],
                    },
                    server="zoho_mcp",
                    category="Zoho CRM",
                    is_mutating=True,
                )
            )

        # Dynamically discover Books tools if Books scopes authorized
        if any("books" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="zoho_books.get_unpaid_invoices",
                    description="Retrieves overdue or unpaid customer invoices from Zoho Books.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "min_days_overdue": {"type": "integer", "default": 0},
                        },
                    },
                    server="zoho_mcp",
                    category="Zoho Books",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_books.get_customer_balance",
                    description="Retrieves ledger balance, total receivables, and aging summary for a customer.",
                    input_schema={
                        "type": "object",
                        "properties": {"customer_name": {"type": "string"}},
                        "required": ["customer_name"],
                    },
                    server="zoho_mcp",
                    category="Zoho Books",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_books.create_invoice",
                    description="Creates an invoice draft in Zoho Books. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "due_date": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["customer_name", "amount", "due_date"],
                    },
                    server="zoho_mcp",
                    category="Zoho Books",
                    is_mutating=True,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_books.record_expense",
                    description="Records an audited expense bill in Zoho Books with GST details. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "vendor_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "gstin": {"type": "string"},
                            "category": {"type": "string", "default": "Office & Advisory"},
                        },
                        "required": ["vendor_name", "amount"],
                    },
                    server="zoho_mcp",
                    category="Zoho Books",
                    is_mutating=True,
                )
            )

        # Dynamically discover Desk tools if Desk scopes authorized
        if any("desk" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="zoho_desk.list_tickets",
                    description="Lists open or high-priority support tickets in Zoho Desk.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                            "status": {"type": "string", "default": "Open"},
                        },
                    },
                    server="zoho_mcp",
                    category="Zoho Desk",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="zoho_desk.create_ticket",
                    description="Files a support ticket in Zoho Desk. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "description": {"type": "string"},
                            "contact_email": {"type": "string"},
                            "priority": {"type": "string", "default": "High"},
                        },
                        "required": ["subject", "description", "contact_email"],
                    },
                    server="zoho_mcp",
                    category="Zoho Desk",
                    is_mutating=True,
                )
            )

        self._discovered_tools = tools
        return self._discovered_tools

    def list_tools(self) -> List[McpTool]:
        """
        Returns dynamically discovered tools.
        Returns empty list if not connected.
        """
        if not self.is_connected:
            self._discovered_tools = []
            return []
        if not self._discovered_tools:
            return self.discover_tools()
        return self._discovered_tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> McpCallResult:
        """
        Executes Zoho Suite tool strictly against domain-specific Zoho APIs using OAuth access token.
        Fails cleanly if not authenticated or token is missing.
        """
        if not self.is_connected:
            return McpCallResult(
                tool_name=name,
                server="zoho_mcp",
                success=False,
                data=None,
                error=(
                    "Zoho Suite is not connected. "
                    "Please navigate to Tab 3 ('Client OAuth & MCP Connectors') and complete the Zoho OAuth authorization flow."
                ),
            )

        token = self.vault.get_zoho_access_token()
        if not token:
            return McpCallResult(
                tool_name=name,
                server="zoho_mcp",
                success=False,
                data=None,
                error=(
                    "Missing valid Zoho Suite OAuth 2.0 Access Token. "
                    "Please navigate to Tab 3 ('Client OAuth & MCP Connectors') and complete the Zoho OAuth authorization flow."
                ),
            )

        return self._call_live_api(name, arguments, token)

    def _call_live_api(self, name: str, arguments: Dict[str, Any], token: str) -> McpCallResult:
        domain = self.vault.zoho.domain
        headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=20.0) as client:
                if name == "zoho_crm.search_records":
                    mod = arguments.get("module", "Deals")
                    query = arguments.get("query", "")
                    url = f"https://www.zohoapis.{domain}/crm/v3/{mod}/search?word={httpx.URL(query)}"
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 204:
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=[])
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho CRM API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("data", []))

                elif name == "zoho_crm.create_lead":
                    url = f"https://www.zohoapis.{domain}/crm/v3/Leads"
                    body = {
                        "data": [
                            {
                                "First_Name": arguments.get("first_name"),
                                "Last_Name": arguments.get("last_name"),
                                "Company": arguments.get("company"),
                                "Email": arguments.get("email"),
                                "Description": arguments.get("notes", ""),
                            }
                        ]
                    }
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho CRM API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("data", [{}])[0])

                elif name == "zoho_crm.update_deal":
                    did = arguments.get("deal_id")
                    url = f"https://www.zohoapis.{domain}/crm/v3/Deals/{did}"
                    body = {
                        "data": [
                            {
                                "Stage": arguments.get("stage"),
                                "Amount": arguments.get("amount"),
                                "Description": arguments.get("notes", ""),
                            }
                        ]
                    }
                    resp = client.put(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho CRM API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("data", [{}])[0])

                elif name == "zoho_books.get_unpaid_invoices":
                    url = f"https://books.zoho.{domain}/api/v3/invoices?status=unpaid"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Books API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("invoices", []))

                elif name == "zoho_books.get_customer_balance":
                    cname = arguments.get("customer_name", "")
                    url = f"https://books.zoho.{domain}/api/v3/contacts?contact_name={httpx.URL(cname)}"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Books API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("contacts", []))

                elif name == "zoho_books.create_invoice":
                    url = f"https://books.zoho.{domain}/api/v3/invoices"
                    body = {
                        "customer_name": arguments.get("customer_name"),
                        "due_date": arguments.get("due_date"),
                        "line_items": [{"rate": arguments.get("amount"), "description": arguments.get("description", "Professional Services")}],
                    }
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Books API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("invoice", {}))

                elif name == "zoho_books.record_expense":
                    url = f"https://books.zoho.{domain}/api/v3/expenses"
                    body = {
                        "vendor_name": arguments.get("vendor_name"),
                        "amount": arguments.get("amount"),
                        "description": f"GSTIN: {arguments.get('gstin', '')}",
                    }
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Books API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("expense", {}))

                elif name == "zoho_desk.list_tickets":
                    url = f"https://desk.zoho.{domain}/api/v1/tickets"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Desk API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json().get("data", []))

                elif name == "zoho_desk.create_ticket":
                    url = f"https://desk.zoho.{domain}/api/v1/tickets"
                    body = {
                        "subject": arguments.get("subject"),
                        "description": arguments.get("description"),
                        "email": arguments.get("contact_email"),
                        "priority": arguments.get("priority", "High"),
                    }
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Zoho Desk API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="zoho_mcp", success=True, data=resp.json())

                return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Tool '{name}' not found.")
        except Exception as e:
            return McpCallResult(tool_name=name, server="zoho_mcp", success=False, data=None, error=f"Live Zoho API Exception: {str(e)}")

