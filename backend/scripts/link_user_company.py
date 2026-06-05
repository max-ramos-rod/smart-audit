import argparse
import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.models.companies import Company
from app.db.models.memberships import Membership
from app.db.models.users import User


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a company and link a user to it.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--role", default="OWNER")
    args = parser.parse_args()

    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with AsyncSession(engine, expire_on_commit=False) as db:
        user = await db.scalar(select(User).where(User.email == args.email))
        if user is None:
            print("User not found.")
            return

        company = await db.scalar(select(Company).where(Company.slug == args.company_slug))
        if company is None:
            company = Company(name=args.company_name, slug=args.company_slug, plan="starter", is_active=True)
            db.add(company)
            await db.flush()

        membership = await db.scalar(
            select(Membership).where(Membership.user_id == user.id, Membership.company_id == company.id)
        )
        if membership is None:
            membership = Membership(company_id=company.id, user_id=user.id, role=args.role)
            db.add(membership)

        await db.commit()
        print(f"Company ready: {company.id} | {company.slug}")


if __name__ == "__main__":
    asyncio.run(main())
