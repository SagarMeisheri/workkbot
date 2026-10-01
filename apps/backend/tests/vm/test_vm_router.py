"""Tests for VM FastAPI Router Endpoints (Spec 11).

Validates:
- GET /api/v1/vm/session
- POST /api/v1/vm/start
- POST /api/v1/vm/confirm-login
- POST /api/v1/vm/confirm-save
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.dependencies import get_current_user, CurrentUser


@pytest.fixture
def mock_user():
    return CurrentUser(
        id="usr_test_12345",
        email="owner@store.in",
        org_id="e0000000-0000-0000-0000-000000000001",
        role="admin",
        token="mock_valid_jwt_token",
    )


@pytest.mark.asyncio
async def test_vm_start_and_session_endpoints(mock_user):
    """Tests starting a VM session and fetching its state."""
    app.dependency_overrides[get_current_user] = lambda: mock_user

    from src.vm.sandbox_manager import desktop_manager

    mock_sandbox = MagicMock()
    mock_sandbox.stream.get_url.return_value = "https://e2b.dev/stream/test_stream_123"

    def fake_get_or_create(user_id, org_id, session_id=None, **kwargs):
        sid = session_id or "sess_vm_123"
        desktop_manager._active_sandboxes[sid] = mock_sandbox
        desktop_manager._session_states[sid] = {
            "session_id": sid,
            "user_id": user_id,
            "org_id": org_id,
            "status": "awaiting_login",
            "stream_url": "https://e2b.dev/stream/test_stream_123",
            "pending_item": None,
            "is_logged_in": False,
        }
        return mock_sandbox, sid, "https://e2b.dev/stream/test_stream_123"

    with patch.object(desktop_manager, "get_or_create_sandbox", side_effect=fake_get_or_create):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Start VM session
            resp = await client.post(
                "/api/v1/vm/start",
                json={
                    "service": "zohobooks",
                    "pending_item": {
                        "name": "Basmati Rice 5kg",
                        "selling_price": 450,
                    },
                },
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "https://e2b.dev/stream/test_stream_123" in data["stream_url"]

            # 2. Query session
            session_resp = await client.get("/api/v1/vm/session")
            assert session_resp.status_code == 200
            session_data = session_resp.json()
            assert session_data["active"] is True
            assert session_data["session_id"] == "sess_vm_123"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_vm_confirm_login_and_save(mock_user):
    """Tests confirming login in Split View and executing save."""
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_sandbox = MagicMock()
    mock_sandbox.stream.get_url.return_value = "https://e2b.dev/stream/test_stream_123"

    from src.vm.sandbox_manager import desktop_manager
    desktop_manager._active_sandboxes["sess_vm_test_confirm"] = mock_sandbox
    desktop_manager._session_states["sess_vm_test_confirm"] = {
        "session_id": "sess_vm_test_confirm",
        "user_id": mock_user.id,
        "org_id": mock_user.org_id,
        "status": "awaiting_login",
        "stream_url": "https://e2b.dev/stream/test_stream_123",
        "pending_item": {"name": "Test Rice 1kg", "selling_price": 90},
        "is_logged_in": False,
    }

    with patch("src.vm.zoho_books_operator.ZohoBooksItemOperator.navigate_to_new_item_page", new_callable=AsyncMock), \
         patch("src.vm.zoho_books_operator.ZohoBooksItemOperator.fill_new_item_form", new_callable=AsyncMock) as mock_fill, \
         patch("src.vm.zoho_books_operator.ZohoBooksItemOperator.submit_save", new_callable=AsyncMock) as mock_save:

        mock_fill.return_value = {"status": "awaiting_save_confirmation", "summary": "Form populated"}
        mock_save.return_value = {"status": "saved", "message": "Success"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Confirm login
            confirm_resp = await client.post(
                "/api/v1/vm/confirm-login",
                json={"session_id": "sess_vm_test_confirm"},
            )
            assert confirm_resp.status_code == 200
            confirm_data = confirm_resp.json()
            assert confirm_data["success"] is True
            assert confirm_data["status"] == "awaiting_save_confirmation"

            # 2. Confirm save
            save_resp = await client.post(
                "/api/v1/vm/confirm-save",
                json={"session_id": "sess_vm_test_confirm"},
            )
            assert save_resp.status_code == 200
            save_data = save_resp.json()
            assert save_data["success"] is True
            assert save_data["save_result"]["status"] == "saved"

    app.dependency_overrides.clear()
