"""Approve an assisted first-app request after human review of customer authorization."""

import argparse
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.models.pool import AppIntake
from app.services.intake import approve_intake

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--database-path", type=Path, required=True)
parser.add_argument(
    "--list-pending",
    action="store_true",
    help="Inspect the private operator queue without changing requests",
)
parser.add_argument("--request-id")
parser.add_argument("--reviewer")
parser.add_argument(
    "--proof-file",
    type=Path,
    help="Private evidence of customer package authorization, reviewed by operator",
)
parser.add_argument("--note", help="Redacted review conclusion; never credentials")
args = parser.parse_args()
if not args.database_path.is_absolute() or not args.database_path.is_file():
    parser.error("Select an existing absolute SQLite database; this command never creates one")
if args.list_pending:
    with Session(create_engine("sqlite:///" + str(args.database_path))) as db:
        for row in db.scalars(
            select(AppIntake)
            .where(AppIntake.status == "PENDING")
            .order_by(AppIntake.submitted_at)
            .limit(100)
        ):
            print(row.id, row.package_name, row.submitted_at.isoformat())
    raise SystemExit(0)
if not all((args.request_id, args.reviewer, args.proof_file, args.note)):
    parser.error("Approval requires request-id, reviewer, proof-file and note")
if not args.proof_file.is_file() or not 0 < args.proof_file.stat().st_size <= 10 * 1024 * 1024:
    parser.error("Provide a reviewed ownership/authorization evidence file up to 10 MiB")
if args.proof_file.stat().st_mode & 0o077:
    parser.error("Ownership evidence must be private (chmod 600)")
engine = create_engine("sqlite:///" + str(args.database_path))


@event.listens_for(engine, "connect")
def configure(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")


with Session(engine) as db:
    row = approve_intake(
        db,
        args.request_id,
        reviewer=args.reviewer,
        proof_sha256=hashlib.sha256(args.proof_file.read_bytes()).hexdigest(),
        note=args.note,
        now=datetime.now(UTC),
    )
    db.commit()
    print("APPROVED", row.id, row.app_id)
