"""Bootstrap a new tenant + admin user with a local password.

Usage:
    python -m repse.scripts.create_admin \\
        --org "Constructora REPSECC SA de CV" \\
        --rfc CRP120304XYZ \\
        --email admin@repsecc.mx \\
        --display-name "Ana López" \\
        --password "supersecret123"

If the organization (by RFC) already exists, the script reuses it and just
adds the user. Idempotent on the user side too: re-running with the same email
updates the password.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from repse.auth.passwords import hash_password
from repse.config import get_settings
from repse.db.session import init_db, get_db
from repse.db.tenant_filter import with_admin_scope
from repse.organizations.models import Organization, OrgStatus
from repse.supplier_types.provisioning import provision_organization
from repse.users.models import Role, User, UserStatus

# El mapeo de SQLAlchemy sólo resuelve si TODO el metadata está registrado: sin
# esto, User.supplier_id no encuentra la tabla 'suppliers' y el script aborta.
# Mismo patrón que alembic/env.py.
import repse.alerts.models  # noqa: F401,E402
import repse.audit.models  # noqa: F401,E402
import repse.compliance.models  # noqa: F401,E402
import repse.document_types.models  # noqa: F401,E402
import repse.documents.models  # noqa: F401,E402
import repse.giros.models  # noqa: F401,E402
import repse.portal.models  # noqa: F401,E402
import repse.sectors.models  # noqa: F401,E402
import repse.supplier_types.models  # noqa: F401,E402
import repse.suppliers.models  # noqa: F401,E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user (local auth).")
    parser.add_argument("--org", required=True, help="Legal name of the organization")
    parser.add_argument("--rfc", required=True, help="Organization RFC (unique)")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--display-name", required=True, help="Admin display name")
    parser.add_argument("--password", required=True, help="Initial password (min 8)")
    args = parser.parse_args()

    init_db(get_settings())
    db_iter = get_db()
    db = next(db_iter)
    try:
        with with_admin_scope():
            org = db.execute(
                select(Organization).where(Organization.rfc == args.rfc)
            ).scalar_one_or_none()

            if org is None:
                org = Organization(
                    legal_name=args.org,
                    rfc=args.rfc,
                    contact_email=args.email,
                    status=OrgStatus.ACTIVE,
                )
                db.add(org)
                db.flush()
                print(f"Created organization {org.id} ({org.legal_name})")
            else:
                print(f"Re-using organization {org.id} ({org.legal_name})")

            user = db.execute(
                select(User).where(
                    User.organization_id == org.id, User.email == args.email.lower()
                )
            ).scalar_one_or_none()

            if user is None:
                user = User(
                    organization_id=org.id,
                    email=args.email.lower(),
                    display_name=args.display_name,
                    role=Role.ADMIN,
                    status=UserStatus.ACTIVE,
                    password_hash=hash_password(args.password),
                )
                db.add(user)
                db.flush()
                print(f"Created admin user {user.id} ({user.email})")
            else:
                user.password_hash = hash_password(args.password)
                user.display_name = args.display_name
                user.status = UserStatus.ACTIVE
                user.role = Role.ADMIN
                print(f"Reset password for existing user {user.id} ({user.email})")

            result = provision_organization(db, organization_id=org.id)
            print(
                f"Provisioned tenant: SupplierType 'Sin clasificar' id={result.sin_clasificar_id} "
                f"+ {result.requirements_created} canonical requirements"
            )
            db.commit()

        print("\nDone. You can now log in at /login with:")
        print(f"  email:    {args.email}")
        print(f"  password: {'*' * len(args.password)}  (the one you provided)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
