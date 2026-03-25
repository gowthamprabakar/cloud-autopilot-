"""
Tests for StsClient.

NOTE: moto 5.0.x's MockRawResponse is incompatible with aiobotocore 2.15.x
(missing raw_headers attribute). Tests mock at the aiobotocore client level
using AsyncMock to test our mapping/error-handling logic directly.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.integrations.aws.sts_client import AssumedRoleCredentials, StsAssumeRoleError, StsClient

_FAKE_ASSUME_ROLE_RESPONSE = {
    "Credentials": {
        "AccessKeyId": "ASIATESTING12345",
        "SecretAccessKey": "fakeSecretKey",
        "SessionToken": "fakeSessionToken",
        "Expiration": datetime(2099, 1, 1, tzinfo=timezone.utc),
    },
    "AssumedRoleUser": {
        "AssumedRoleId": "AROA123:session",
        "Arn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
    },
}

_FAKE_IDENTITY_RESPONSE = {
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
    "UserId": "AROA123:session",
    "ResponseMetadata": {},
}


def _make_mock_sts_client():
    """Return an AsyncMock that looks like an aiobotocore STS client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.assume_role = AsyncMock(return_value=_FAKE_ASSUME_ROLE_RESPONSE)
    client.get_caller_identity = AsyncMock(return_value=_FAKE_IDENTITY_RESPONSE)
    return client


@pytest.mark.asyncio
async def test_sts_assume_role_returns_credentials():
    """assume_role maps STS response to AssumedRoleCredentials."""
    mock_client = _make_mock_sts_client()
    sts = StsClient(access_key_id="key", secret_access_key="secret", region="us-east-1")

    with patch.object(sts._session, "create_client", return_value=mock_client):
        creds = await sts.assume_role(
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            session_name="test-session",
        )

    assert isinstance(creds, AssumedRoleCredentials)
    assert creds.access_key_id == "ASIATESTING12345"
    assert creds.secret_access_key == "fakeSecretKey"
    assert creds.session_token == "fakeSessionToken"
    assert "TestRole" in creds.assumed_role_arn
    assert creds.expiration


@pytest.mark.asyncio
async def test_sts_assume_role_with_external_id_passes_param():
    """external_id is included in the assume_role call when provided."""
    mock_client = _make_mock_sts_client()
    sts = StsClient(access_key_id="key", secret_access_key="secret", region="us-east-1")

    with patch.object(sts._session, "create_client", return_value=mock_client):
        creds = await sts.assume_role(
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            session_name="test-session",
            external_id="ext-abc-123",
        )

    # Verify external_id was passed to the underlying call
    call_kwargs = mock_client.assume_role.call_args.kwargs
    assert call_kwargs.get("ExternalId") == "ext-abc-123"
    assert creds.access_key_id


@pytest.mark.asyncio
async def test_sts_get_caller_identity_returns_account():
    """get_caller_identity maps response to identity dict."""
    mock_client = _make_mock_sts_client()
    sts = StsClient(access_key_id="key", secret_access_key="secret", region="us-east-1")
    creds = AssumedRoleCredentials(
        access_key_id="ASIA",
        secret_access_key="sec",
        session_token="tok",
        assumed_role_arn="arn:...",
        expiration="2099-01-01",
    )

    with patch.object(sts._session, "create_client", return_value=mock_client):
        identity = await sts.get_caller_identity(creds)

    assert identity["Account"] == "123456789012"
    assert "Arn" in identity
    assert "UserId" in identity


@pytest.mark.asyncio
async def test_sts_assume_role_client_error_raises_sts_error():
    """ClientError during assume_role is re-raised as StsAssumeRoleError."""
    mock_client = _make_mock_sts_client()
    mock_client.assume_role.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Not allowed"}},
        "AssumeRole",
    )
    sts = StsClient(access_key_id="key", secret_access_key="secret", region="us-east-1")

    with patch.object(sts._session, "create_client", return_value=mock_client):
        with pytest.raises(StsAssumeRoleError) as exc_info:
            await sts.assume_role(
                role_arn="arn:aws:iam::123456789012:role/NoAccess",
                session_name="test-session",
            )

    assert exc_info.value.error_code == "AccessDenied"
    assert "AccessDenied" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sts_get_caller_identity_error_raises_sts_error():
    """ClientError during get_caller_identity is re-raised as StsAssumeRoleError."""
    mock_client = _make_mock_sts_client()
    mock_client.get_caller_identity.side_effect = ClientError(
        {"Error": {"Code": "InvalidClientTokenId", "Message": "Token invalid"}},
        "GetCallerIdentity",
    )
    sts = StsClient(access_key_id="key", secret_access_key="secret", region="us-east-1")
    creds = AssumedRoleCredentials(
        access_key_id="ASIA",
        secret_access_key="sec",
        session_token="tok",
        assumed_role_arn="arn:...",
        expiration="2099-01-01",
    )

    with patch.object(sts._session, "create_client", return_value=mock_client):
        with pytest.raises(StsAssumeRoleError) as exc_info:
            await sts.get_caller_identity(creds)

    assert exc_info.value.error_code == "InvalidClientTokenId"


def test_sts_client_from_settings_constructs_client():
    """from_settings() creates a StsClient with region from settings."""
    client = StsClient.from_settings()
    assert client is not None
    assert client._region == "us-east-1"  # default in settings
