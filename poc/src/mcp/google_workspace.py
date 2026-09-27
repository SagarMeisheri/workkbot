"""
Workkbot Local PoC: Google Workspace MCP Provider
Implements Google Workspace tools with strict Live REST APIs via OAuth Bearer tokens.
Tools are dynamically discovered only when authenticated via OAuth.
"""
import base64
import datetime
import json
from typing import Any, Dict, List, Optional
import httpx
from src.mcp.client_vault import ClientVault
from src.mcp.models import McpTool, McpCallResult


class GoogleWorkspaceMcpProvider:
    """
    Google Workspace MCP Server client.
    Supports Gmail, Drive, and Calendar tools.
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
        return self._manual_enabled and self.vault.is_google_authenticated()

    @is_connected.setter
    def is_connected(self, value: bool):
        self._manual_enabled = value
        if not value:
            self._discovered_tools = []

    def discover_tools(self) -> List[McpTool]:
        """
        Dynamically discovers tools from the connected Google Workspace MCP Server or
        authenticated OAuth session after client connects.
        """
        if not self.is_connected:
            self._discovered_tools = []
            return []

        token = self.vault.get_google_access_token()
        mcp_server_url = getattr(self.vault.google, "server_url", None)

        # 1. If remote MCP server URL is configured, query tools/list via MCP protocol
        if mcp_server_url:
            try:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{mcp_server_url}/tools/list",
                        headers=headers,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        tools_data = payload.get("result", {}).get("tools", [])
                        parsed = []
                        for t in tools_data:
                            name = t.get("name", "")
                            is_mut = any(act in name.lower() for act in ["send", "create", "update", "delete", "write"])
                            parsed.append(
                                McpTool(
                                    name=name,
                                    description=t.get("description", ""),
                                    input_schema=t.get("inputSchema", {}),
                                    server="google_workspace",
                                    category="Google Workspace",
                                    is_mutating=is_mut,
                                )
                            )
                        if parsed:
                            self._discovered_tools = parsed
                            return self._discovered_tools
            except Exception:
                pass

        # 2. Dynamic tool discovery based on authorized client scopes
        tools: List[McpTool] = []
        scopes = self.vault.google.scopes

        # Dynamically discover Gmail tools if gmail scopes authorized
        if any("gmail" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="gmail.search_threads",
                    description="Searches email threads matching query in user's Gmail mailbox.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query matching standard Gmail syntax"},
                            "max_results": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                    server="google_workspace",
                    category="Gmail",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="gmail.get_thread",
                    description="Retrieves full email thread contents and messages.",
                    input_schema={
                        "type": "object",
                        "properties": {"thread_id": {"type": "string", "description": "Unique Gmail thread ID"}},
                        "required": ["thread_id"],
                    },
                    server="google_workspace",
                    category="Gmail",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="gmail.create_draft",
                    description="Creates an email draft in Gmail Drafts folder without sending.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject line"},
                            "body": {"type": "string", "description": "Email body content"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                    server="google_workspace",
                    category="Gmail",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="gmail.send_message",
                    description="Sends an email message via Gmail. (State-changing: requires Human-In-The-Loop approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject line"},
                            "body": {"type": "string", "description": "Email body text"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                    server="google_workspace",
                    category="Gmail",
                    is_mutating=True,
                )
            )

        # Dynamically discover Google Drive tools if drive scopes authorized
        if any("drive" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="drive.search_files",
                    description="Searches Google Drive for documents, PDFs, and folders matching query.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Drive search query"},
                            "page_size": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                    server="google_workspace",
                    category="Google Drive",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="drive.read_file_content",
                    description="Reads the text or document content of a Google Drive file.",
                    input_schema={
                        "type": "object",
                        "properties": {"file_id": {"type": "string", "description": "Drive File ID"}},
                        "required": ["file_id"],
                    },
                    server="google_workspace",
                    category="Google Drive",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="drive.create_file",
                    description="Uploads or creates a document/file in Google Drive. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Filename with extension"},
                            "content": {"type": "string", "description": "Document content"},
                            "mime_type": {"type": "string", "default": "text/plain"},
                        },
                        "required": ["name", "content"],
                    },
                    server="google_workspace",
                    category="Google Drive",
                    is_mutating=True,
                )
            )

        # Dynamically discover Google Calendar tools if calendar scopes authorized
        if any("calendar" in s.lower() for s in scopes):
            tools.append(
                McpTool(
                    name="calendar.list_events",
                    description="Lists upcoming events on Google Calendar within a specified time range.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "time_min": {"type": "string", "description": "ISO start datetime string"},
                            "time_max": {"type": "string", "description": "ISO end datetime string"},
                        },
                    },
                    server="google_workspace",
                    category="Google Calendar",
                    is_mutating=False,
                )
            )
            tools.append(
                McpTool(
                    name="calendar.create_event",
                    description="Schedules a new meeting on Google Calendar. (State-changing: requires HITL approval)",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Meeting title"},
                            "start_time": {"type": "string", "description": "ISO start datetime"},
                            "end_time": {"type": "string", "description": "ISO end datetime"},
                            "attendees": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["summary", "start_time", "end_time"],
                    },
                    server="google_workspace",
                    category="Google Calendar",
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
        Executes Google Workspace tool strictly against Google REST APIs using the live OAuth access token.
        Fails cleanly if not authenticated or token is missing.
        """
        if not self.is_connected:
            return McpCallResult(
                tool_name=name,
                server="google_workspace",
                success=False,
                data=None,
                error=(
                    "Google Workspace is not connected. "
                    "Please navigate to Tab 3 ('Client OAuth & MCP Connectors') and complete the Google OAuth authorization flow."
                ),
            )

        token = self.vault.get_google_access_token()
        if not token:
            return McpCallResult(
                tool_name=name,
                server="google_workspace",
                success=False,
                data=None,
                error=(
                    "Missing valid Google Workspace OAuth 2.0 Access Token. "
                    "Please navigate to Tab 3 ('Client OAuth & MCP Connectors') and complete the Google OAuth authorization flow."
                ),
            )

        return self._call_live_api(name, arguments, token)

    def _call_live_api(self, name: str, arguments: Dict[str, Any], token: str) -> McpCallResult:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=20.0) as client:
                if name == "gmail.search_threads":
                    q = arguments.get("query", "")
                    max_res = arguments.get("max_results", 5)
                    url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads?q={httpx.URL(q)}&maxResults={max_res}"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json().get("threads", []))

                elif name == "gmail.get_thread":
                    tid = arguments.get("thread_id", "")
                    url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{tid}"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json())

                elif name == "gmail.create_draft":
                    raw_msg = f"To: {arguments.get('to')}\r\nSubject: {arguments.get('subject')}\r\n\r\n{arguments.get('body')}"
                    encoded = base64.urlsafe_b64encode(raw_msg.encode("utf-8")).decode("utf-8")
                    url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
                    resp = client.post(url, headers=headers, json={"message": {"raw": encoded}})
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json())

                elif name == "gmail.send_message":
                    raw_msg = f"To: {arguments.get('to')}\r\nSubject: {arguments.get('subject')}\r\n\r\n{arguments.get('body')}"
                    encoded = base64.urlsafe_b64encode(raw_msg.encode("utf-8")).decode("utf-8")
                    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                    resp = client.post(url, headers=headers, json={"raw": encoded})
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json())

                elif name == "drive.search_files":
                    q = arguments.get("query", "")
                    page_size = arguments.get("page_size", 5)
                    url = f"https://www.googleapis.com/drive/v3/files?pageSize={page_size}&fields=files(id,name,mimeType)"
                    if q:
                        url += f"&q=name contains '{q}'"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json().get("files", []))

                elif name == "drive.read_file_content":
                    fid = arguments.get("file_id", "")
                    url = f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data={"file_id": fid, "content": resp.text})

                elif name == "drive.create_file":
                    url = "https://www.googleapis.com/drive/v3/files"
                    meta = {"name": arguments.get("name", "Document.txt"), "mimeType": arguments.get("mime_type", "text/plain")}
                    resp = client.post(url, headers=headers, json=meta)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json())

                elif name == "calendar.list_events":
                    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=10&singleEvents=true&orderBy=startTime"
                    resp = client.get(url, headers=headers)
                    if resp.status_code != 200:
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json().get("items", []))

                elif name == "calendar.create_event":
                    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                    body = {
                        "summary": arguments.get("summary", "New Event"),
                        "start": {"dateTime": arguments.get("start_time")},
                        "end": {"dateTime": arguments.get("end_time")},
                        "attendees": [{"email": e} for e in arguments.get("attendees", [])],
                    }
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code not in (200, 201):
                        return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Google API Error {resp.status_code}: {resp.text}")
                    return McpCallResult(tool_name=name, server="google_workspace", success=True, data=resp.json())

                return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Tool '{name}' not found.")
        except Exception as e:
            return McpCallResult(tool_name=name, server="google_workspace", success=False, data=None, error=f"Live Google API Exception: {str(e)}")

