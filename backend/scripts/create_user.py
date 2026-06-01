import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import User
from app.db.session import engine


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create an initial Smart Audit user.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    async with AsyncSession(engine, expire_on_commit=False) as db:
        existing_user = await db.scalar(select(User).where(User.email == args.email))
        if existing_user is not None:
            print("User already exists for this email.")
            return

        user = User(
            name=args.name,
            email=args.email,
            password_hash=hash_password(args.password),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"User created: {args.email}")


if __name__ == "__main__":
    asyncio.run(main())
