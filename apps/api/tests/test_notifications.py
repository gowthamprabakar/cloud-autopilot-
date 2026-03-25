"""
Sprint 8 — Notification tests.

Covers: list, mark read, mark all read, unread count, filters, workspace isolation, auth.
"""

import pytest
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────

_BASE_REGISTER = {
    "tenant_name": "Notif Corp",
    "tenant_slug": "notif-corp",
    "workspace_name": "Notif Workspace",
    "email": "notifadmin@notif-corp.com",
    "password": "notifadminpw1",
    "full_name": "Notif Admin",
    "plan": "baseline",
}

_OTHER_REGISTER = {
    "tenant_name": "Other Notif Corp",
    "tenant_slug": "other-notif-corp",
    "workspace_name": "Other Notif Workspace",
    "email": "otheradmin@other-notif-corp.com",
    "password": "otheradminpw1",
    "full_name": "Other Notif Admin",
    "plan": "baseline",
}


async def _register_and_login(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or _BASE_REGISTER
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient):
    """GET /notifications on a fresh account returns empty list with 0 unread."""
    token = await _register_and_login(client)

    res = await client.get("/api/v1/notifications", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "unread_count" in data
    assert data["items"] == []
    assert data["unread_count"] == 0


@pytest.mark.asyncio
async def test_create_notification_directly(client: AsyncClient, db_session):
    """Create a notification via service layer, then list via API."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.repositories.user_repository import UserRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.notification_service import NotificationService

    token = await _register_and_login(client)

    # Get the user's workspace_id and user_id from the DB
    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row = result.fetchone()
    assert row is not None, "User not found"
    user_id = uuid.UUID(str(row[0]))
    workspace_id = uuid.UUID(str(row[1]))

    # Create a notification directly via service
    notif_repo = NotificationRepository(db_session)
    notif_svc = NotificationService(notif_repo)
    notif = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="critical_finding",
        title="Critical finding detected",
        body="A new CRITICAL finding was detected in your account.",
        metadata_={"severity": "critical"},
        link_path="/findings/123",
    )
    await db_session.commit()

    # Now list via API
    res = await client.get("/api/v1/notifications", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["items"]) >= 1
    assert data["unread_count"] >= 1

    found = next((n for n in data["items"] if n["title"] == "Critical finding detected"), None)
    assert found is not None
    assert found["type"] == "critical_finding"
    assert found["is_read"] is False
    assert found["link_path"] == "/findings/123"


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, db_session):
    """PATCH /notifications/{id}/read marks a notification as read."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.services.notification_service import NotificationService

    token = await _register_and_login(client)

    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row = result.fetchone()
    user_id = uuid.UUID(str(row[0]))
    workspace_id = uuid.UUID(str(row[1]))

    notif_svc = NotificationService(NotificationRepository(db_session))
    notif = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="sync_failed",
        title="Sync failed",
        body="The sync job failed.",
    )
    await db_session.commit()

    notif_id = str(notif.id)

    res = await client.patch(
        f"/api/v1/notifications/{notif_id}/read",
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["is_read"] is True
    assert data["id"] == notif_id


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client: AsyncClient, db_session):
    """POST /notifications/read-all marks all unread notifications as read."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.services.notification_service import NotificationService

    token = await _register_and_login(client)

    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row = result.fetchone()
    user_id = uuid.UUID(str(row[0]))
    workspace_id = uuid.UUID(str(row[1]))

    notif_svc = NotificationService(NotificationRepository(db_session))
    for i in range(3):
        await notif_svc.create(
            workspace_id=workspace_id,
            user_id=user_id,
            type="user_invited",
            title=f"User invited {i}",
            body=f"A user was invited {i}.",
        )
    await db_session.commit()

    # Verify unread before
    list_res = await client.get("/api/v1/notifications", headers=_auth(token))
    assert list_res.json()["unread_count"] >= 3

    # Mark all read
    res = await client.post("/api/v1/notifications/read-all", headers=_auth(token))
    assert res.status_code == 200, res.text
    assert res.json()["marked_read"] >= 3

    # Verify unread after
    list_res2 = await client.get("/api/v1/notifications", headers=_auth(token))
    assert list_res2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_unread_count_in_response(client: AsyncClient, db_session):
    """unread_count in response correctly reflects unread notifications."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.services.notification_service import NotificationService

    token = await _register_and_login(client)

    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row = result.fetchone()
    user_id = uuid.UUID(str(row[0]))
    workspace_id = uuid.UUID(str(row[1]))

    notif_svc = NotificationService(NotificationRepository(db_session))

    # Create 2 notifications
    n1 = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="critical_finding",
        title="Critical 1",
        body="Body 1",
    )
    n2 = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="critical_finding",
        title="Critical 2",
        body="Body 2",
    )
    await db_session.commit()

    res = await client.get("/api/v1/notifications", headers=_auth(token))
    assert res.json()["unread_count"] == 2

    # Mark one as read
    await client.patch(
        f"/api/v1/notifications/{n1.id}/read",
        headers=_auth(token),
    )

    res2 = await client.get("/api/v1/notifications", headers=_auth(token))
    assert res2.json()["unread_count"] == 1


@pytest.mark.asyncio
async def test_unread_only_filter(client: AsyncClient, db_session):
    """GET /notifications?unread_only=true returns only unread notifications."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.services.notification_service import NotificationService

    token = await _register_and_login(client)

    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row = result.fetchone()
    user_id = uuid.UUID(str(row[0]))
    workspace_id = uuid.UUID(str(row[1]))

    notif_svc = NotificationService(NotificationRepository(db_session))
    n1 = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="sync_failed",
        title="Unread notif",
        body="Body unread",
    )
    n2 = await notif_svc.create(
        workspace_id=workspace_id,
        user_id=user_id,
        type="sync_failed",
        title="Read notif",
        body="Body read",
    )
    await db_session.commit()

    # Mark n2 as read
    await client.patch(
        f"/api/v1/notifications/{n2.id}/read",
        headers=_auth(token),
    )

    # Unread only should return only n1
    res = await client.get(
        "/api/v1/notifications",
        params={"unread_only": True},
        headers=_auth(token),
    )
    assert res.status_code == 200
    items = res.json()["items"]
    titles = [item["title"] for item in items]
    assert "Unread notif" in titles
    assert "Read notif" not in titles


@pytest.mark.asyncio
async def test_notification_workspace_isolation(client: AsyncClient, db_session):
    """User B cannot see User A's notifications."""
    import uuid

    from sqlalchemy import text

    from app.repositories.notification_repository import NotificationRepository
    from app.services.notification_service import NotificationService

    token_a = await _register_and_login(client, _BASE_REGISTER)
    token_b = await _register_and_login(client, _OTHER_REGISTER)

    # Get user A's info
    result = await db_session.execute(
        text("SELECT id, workspace_id FROM users WHERE email = 'notifadmin@notif-corp.com'")
    )
    row_a = result.fetchone()
    user_a_id = uuid.UUID(str(row_a[0]))
    workspace_a_id = uuid.UUID(str(row_a[1]))

    # Create notification for user A
    notif_svc = NotificationService(NotificationRepository(db_session))
    await notif_svc.create(
        workspace_id=workspace_a_id,
        user_id=user_a_id,
        type="critical_finding",
        title="User A secret notification",
        body="This should not be visible to user B.",
    )
    await db_session.commit()

    # User B should not see user A's notifications
    res_b = await client.get("/api/v1/notifications", headers=_auth(token_b))
    assert res_b.status_code == 200
    titles_b = [item["title"] for item in res_b.json()["items"]]
    assert "User A secret notification" not in titles_b


@pytest.mark.asyncio
async def test_notifications_requires_auth(client: AsyncClient):
    """GET /notifications without a token returns 401."""
    res = await client.get("/api/v1/notifications")
    assert res.status_code == 401
