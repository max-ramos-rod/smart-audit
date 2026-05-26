import argparse

from sqlalchemy import select

from app.db.models import Company, Membership, User
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a company and link a user to it.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--role", default="OWNER")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email))
        if user is None:
            print("User not found.")
            return

        company = db.scalar(select(Company).where(Company.slug == args.company_slug))
        if company is None:
            company = Company(name=args.company_name, slug=args.company_slug, plan="starter", is_active=True)
            db.add(company)
            db.flush()

        membership = db.scalar(
            select(Membership).where(Membership.user_id == user.id, Membership.company_id == company.id)
        )
        if membership is None:
            membership = Membership(company_id=company.id, user_id=user.id, role=args.role)
            db.add(membership)
            db.flush()

        db.commit()
        print(f"Company ready: {company.id} | {company.slug}")


if __name__ == "__main__":
    main()