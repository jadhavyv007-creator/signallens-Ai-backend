"""
Database repositories with ownership enforcement and IDOR prevention.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from api.database.models import (
    UserModel,
    FileModel,
    AnalysisModel,
    SubscriptionModel,
    BillingEventModel,
    UsageMeterModel,
    PaymentModel,
)
from api.schemas.common import APIException


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        tier: str = "base",
    ) -> UserModel:
        kwargs = {
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "name": name,
            "role": "user",
            "tier": tier,
        }
        if id:
            kwargs["id"] = id
        user = UserModel(**kwargs)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        # Create default usage meter
        meter = UsageMeterModel(user_id=user.id)
        self.session.add(meter)
        await self.session.commit()

        return user

    async def update_refresh_token(self, user_id: str, refresh_token_hash: Optional[str]) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(refresh_token_hash=refresh_token_hash, updated_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def record_failed_attempt(self, user: UserModel) -> None:
        attempts = user.failed_login_attempts + 1
        lockout_until = None
        if attempts >= 5:
            # 15 minutes lockout
            lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        user.failed_login_attempts = attempts
        user.lockout_until = lockout_until
        await self.session.commit()

    async def reset_failed_attempts(self, user: UserModel) -> None:
        user.failed_login_attempts = 0
        user.lockout_until = None
        await self.session.commit()

    async def update_tier(self, user_id: str, tier: str) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(tier=tier, updated_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        file_name: str,
        predicted_class: str,
        confidence: float,
        is_anomaly: bool,
        anomaly_score: float,
        report_text: str,
        metrics_json: dict,
        advanced_json: dict,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> AnalysisModel:
        analysis = AnalysisModel(
            user_id=user_id,
            file_id=file_id,
            file_name=file_name,
            predicted_class=predicted_class,
            confidence=confidence,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            report_text=report_text,
            metrics_json=metrics_json,
            advanced_json=advanced_json,
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get_by_id_and_owner(self, analysis_id: str, user_id: str) -> AnalysisModel:
        """Enforces ownership. Returns 404 NOT_FOUND if missing or foreign."""
        stmt = select(AnalysisModel).where(
            AnalysisModel.id == analysis_id,
            AnalysisModel.user_id == user_id,
            AnalysisModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise APIException(status_code=404, code="NOT_FOUND", message="Analysis not found")
        return doc

    async def list_by_user(
        self, user_id: str, page: int = 1, limit: int = 20
    ) -> Tuple[List[AnalysisModel], int]:
        offset = (page - 1) * limit
        count_stmt = select(func.count(AnalysisModel.id)).where(
            AnalysisModel.user_id == user_id,
            AnalysisModel.is_deleted == False,
        )
        total_count = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(AnalysisModel)
            .where(AnalysisModel.user_id == user_id, AnalysisModel.is_deleted == False)
            .order_by(AnalysisModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        records = (await self.session.execute(stmt)).scalars().all()
        return list(records), total_count


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: str) -> SubscriptionModel:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
        sub = (await self.session.execute(stmt)).scalar_one_or_none()
        if not sub:
            sub = SubscriptionModel(
                user_id=user_id,
                tier="base",
                billing_cycle="monthly",
                status="active",
                current_period_end=datetime.now(timezone.utc) + timedelta(days=3650),
                payment_provider="system",
            )
            self.session.add(sub)
            await self.session.commit()
            await self.session.refresh(sub)
        return sub

    async def update_subscription(
        self,
        user_id: str,
        tier: str,
        billing_cycle: str,
        status: str,
        period_end: datetime,
        payment_provider: str,
        provider_sub_id: Optional[str] = None,
    ) -> SubscriptionModel:
        sub = await self.get_or_create(user_id)
        sub.tier = tier
        sub.billing_cycle = billing_cycle
        sub.status = status
        sub.current_period_end = period_end
        sub.payment_provider = payment_provider
        sub.provider_subscription_id = provider_sub_id
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def log_billing_event(
        self, user_id: str, event_type: str, amount: float, currency: str, raw_payload: dict
    ) -> None:
        event = BillingEventModel(
            user_id=user_id,
            event_type=event_type,
            amount=amount,
            currency=currency,
            raw_payload=raw_payload,
        )
        self.session.add(event)
        await self.session.commit()


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_payment(
        self,
        order_id: str,
        plan: str,
        currency: str,
        billing_cycle: str,
        base_amount: float,
        tax_amount: float,
        total_amount: float,
        payment_method: str = "upi",
        gateway: str = "mock",
        status: str = "pending",
        user_id: Optional[str] = None,
        raw_metadata: Optional[dict] = None,
    ) -> PaymentModel:
        clean_order_id = str(order_id).strip()
        payment = PaymentModel(
            user_id=user_id,
            order_id=clean_order_id,
            plan=plan,
            currency=currency,
            billing_cycle=billing_cycle,
            base_amount=base_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_method=payment_method,
            gateway=gateway,
            status=status,
            raw_metadata=raw_metadata,
        )
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_by_order_id(self, order_id: str) -> Optional[PaymentModel]:
        if not order_id:
            return None
        clean_id = str(order_id).strip()
        stmt = select(PaymentModel).where(func.lower(PaymentModel.order_id) == clean_id.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        order_id: str,
        status: str,
        payment_method: Optional[str] = None,
        raw_metadata: Optional[dict] = None,
    ) -> Optional[PaymentModel]:
        payment = await self.get_by_order_id(order_id)
        if not payment:
            return None
        payment.status = status
        if payment_method:
            payment.payment_method = payment_method
        if raw_metadata:
            payment.raw_metadata = raw_metadata
        payment.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def list_by_user(self, user_id: str, limit: int = 50) -> List[PaymentModel]:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.user_id == user_id)
            .order_by(PaymentModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
