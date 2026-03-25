"""
AWS STS client — AssumeRole + GetCallerIdentity via aiobotocore.

Usage pattern:
    client = StsClient.from_settings()            # uses bootstrap credentials
    creds = await client.assume_role(role_arn, session_name, external_id)
    identity = await client.get_caller_identity(creds)

Phase 3: real aiobotocore calls.
Phase 4+: support IRSA (no static credentials) via empty key/secret.
"""

import logging
from dataclasses import dataclass

import aiobotocore.session
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_DEFAULT_SESSION_DURATION = 3600  # 1 hour


@dataclass
class AssumedRoleCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: str
    assumed_role_arn: str
    expiration: str  # ISO8601


class StsAssumeRoleError(Exception):
    """Raised when STS AssumeRole or GetCallerIdentity fails."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class StsClient:
    """
    Async STS wrapper. Uses aiobotocore under the hood.

    Instantiate via StsClient.from_settings() for production,
    or StsClient(key, secret, region) for explicit credentials.
    """

    def __init__(
        self,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region
        self._session = aiobotocore.session.get_session()

    @classmethod
    def from_settings(cls) -> "StsClient":
        from app.core.config import settings

        return cls(
            access_key_id=settings.aws_access_key_id or None,
            secret_access_key=settings.aws_secret_access_key or None,
            region=settings.aws_default_region,
        )

    def _client_kwargs(self) -> dict:
        kwargs: dict = {"region_name": self._region}
        if self._access_key_id:
            kwargs["aws_access_key_id"] = self._access_key_id
        if self._secret_access_key:
            kwargs["aws_secret_access_key"] = self._secret_access_key
        return kwargs

    async def assume_role(
        self,
        role_arn: str,
        session_name: str,
        external_id: str | None = None,
        duration_seconds: int = _DEFAULT_SESSION_DURATION,
    ) -> AssumedRoleCredentials:
        """
        Assume the given IAM role and return temporary credentials.
        Raises StsAssumeRoleError if the call fails.
        """
        params: dict = {
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": duration_seconds,
        }
        if external_id:
            params["ExternalId"] = external_id

        logger.info("sts.assume_role starting role_arn=%s session=%s", role_arn, session_name)

        try:
            async with self._session.create_client("sts", **self._client_kwargs()) as client:
                response = await client.assume_role(**params)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            logger.error("sts.assume_role failed code=%s msg=%s", code, msg)
            raise StsAssumeRoleError(f"AssumeRole failed ({code}): {msg}", error_code=code) from exc

        creds = response["Credentials"]
        assumed_arn = response["AssumedRoleUser"]["Arn"]
        logger.info("sts.assume_role ok assumed_arn=%s", assumed_arn)

        return AssumedRoleCredentials(
            access_key_id=creds["AccessKeyId"],
            secret_access_key=creds["SecretAccessKey"],
            session_token=creds["SessionToken"],
            assumed_role_arn=assumed_arn,
            expiration=creds["Expiration"].isoformat(),
        )

    async def get_caller_identity(
        self, credentials: AssumedRoleCredentials
    ) -> dict:
        """
        Validate temporary credentials with GetCallerIdentity.
        Returns {"Account": "...", "Arn": "...", "UserId": "..."}.
        Raises StsAssumeRoleError on failure.
        """
        logger.info("sts.get_caller_identity starting")
        try:
            async with self._session.create_client(
                "sts",
                region_name=self._region,
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key,
                aws_session_token=credentials.session_token,
            ) as client:
                response = await client.get_caller_identity()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            raise StsAssumeRoleError(
                f"GetCallerIdentity failed ({code}): {msg}", error_code=code
            ) from exc

        logger.info("sts.get_caller_identity ok account=%s", response.get("Account"))
        return {
            "Account": response["Account"],
            "Arn": response["Arn"],
            "UserId": response["UserId"],
        }
