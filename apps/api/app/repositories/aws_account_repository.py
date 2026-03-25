"""
AWS Account Repository — data access for aws_accounts table.
"""

import uuid

from sqlalchemy import select

from app.models.aws_account import AwsAccount
from app.models.enums import AwsAccountStatus
from app.repositories.base import BaseRepository


class AwsAccountRepository(BaseRepository[AwsAccount]):
    model = AwsAccount

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[AwsAccount]:
        result = await self.db.execute(
            select(AwsAccount)
            .where(AwsAccount.workspace_id == workspace_id)
            .order_by(AwsAccount.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_account_id_and_workspace(
        self, account_id: str, workspace_id: uuid.UUID
    ) -> AwsAccount | None:
        result = await self.db.execute(
            select(AwsAccount)
            .where(
                AwsAccount.account_id == account_id,
                AwsAccount.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def account_exists_in_workspace(
        self, account_id: str, workspace_id: uuid.UUID
    ) -> bool:
        return await self.get_by_account_id_and_workspace(account_id, workspace_id) is not None

    async def update_status(
        self,
        aws_account_id: uuid.UUID,
        status: AwsAccountStatus,
        last_error: str | None = None,
    ) -> AwsAccount:
        fields: dict = {"status": status}
        if last_error is not None:
            fields["last_error"] = last_error
        return await self.update_fields(aws_account_id, **fields)
