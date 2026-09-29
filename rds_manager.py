#!/usr/bin/env python3
"""
AWS RDS Instance Manager.

Provision a new MySQL RDS instance and manage an existing RDS instance by
starting it, stopping it, or creating a snapshot.

AWS credentials are never stored in this file. boto3 uses the normal AWS
credential chain (AWS CLI profile, environment variables, IAM role, etc.).
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
DEFAULT_LOG_FILE = "rds_manager.log"
DEFAULT_LOG_LEVEL = "INFO"


def configure_logging(log_file: str, log_level: str) -> None:
    """Configure console and local-file logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def get_rds_client(region: str):
    """Return a boto3 RDS client for the requested AWS region."""
    return boto3.client("rds", region_name=region)


def check_instance(rds: Any, db_instance_identifier: str) -> dict:
    """Return an existing RDS instance or raise a clear error."""
    try:
        response = rds.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )
    except (ClientError, BotoCoreError) as exc:
        logging.error("Unable to inspect RDS instance '%s': %s",
                      db_instance_identifier, exc)
        raise

    instances = response.get("DBInstances", [])
    if not instances:
        raise ValueError(f"RDS instance not found: {db_instance_identifier}")
    return instances[0]


def create_db_instance(
    rds: Any,
    db_instance_identifier: str,
    master_username: str,
    master_password: str,
    db_instance_class: str,
    allocated_storage: int,
) -> str:
    """Provision a new MySQL RDS DB instance."""
    if len(master_password) < 8:
        raise ValueError("Master password must contain at least 8 characters.")

    logging.info(
        "Provisioning MySQL RDS instance '%s' (%s, %d GiB)...",
        db_instance_identifier,
        db_instance_class,
        allocated_storage,
    )

    try:
        response = rds.create_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=allocated_storage,
            DBInstanceClass=db_instance_class,
            Engine="mysql",
            MasterUsername=master_username,
            MasterUserPassword=master_password,
            BackupRetentionPeriod=7,
            StorageType="gp3",
            PubliclyAccessible=False,
        )
    except (ClientError, BotoCoreError) as exc:
        logging.error("Failed to create RDS instance '%s': %s",
                      db_instance_identifier, exc)
        raise

    created_id = response["DBInstance"]["DBInstanceIdentifier"]
    logging.info("RDS create request submitted successfully: %s", created_id)
    return created_id


def start_db_instance(rds: Any, db_instance_identifier: str) -> None:
    """Start the specified RDS instance if it is not already available."""
    instance = check_instance(rds, db_instance_identifier)
    status = instance["DBInstanceStatus"]

    if status == "available":
        logging.info("RDS instance '%s' is already running.",
                     db_instance_identifier)
        return

    logging.info("Starting RDS instance '%s' (current status: %s)...",
                 db_instance_identifier, status)
    try:
        rds.start_db_instance(DBInstanceIdentifier=db_instance_identifier)
    except (ClientError, BotoCoreError) as exc:
        logging.error("Failed to start instance '%s': %s",
                      db_instance_identifier, exc)
        raise
    logging.info("Start request submitted successfully.")


def stop_db_instance(rds: Any, db_instance_identifier: str) -> None:
    """Stop the specified RDS instance if it is not already stopped."""
    instance = check_instance(rds, db_instance_identifier)
    status = instance["DBInstanceStatus"]

    if status == "stopped":
        logging.info("RDS instance '%s' is already stopped.",
                     db_instance_identifier)
        return

    logging.info("Stopping RDS instance '%s' (current status: %s)...",
                 db_instance_identifier, status)
    try:
        rds.stop_db_instance(DBInstanceIdentifier=db_instance_identifier)
    except (ClientError, BotoCoreError) as exc:
        logging.error("Failed to stop instance '%s': %s",
                      db_instance_identifier, exc)
        raise
    logging.info("Stop request submitted successfully.")


def create_snapshot(rds: Any, db_instance_identifier: str) -> str:
    """Create a timestamped manual snapshot of an RDS instance."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot_id = f"{db_instance_identifier}-snapshot-{timestamp}".lower()

    logging.info("Creating snapshot '%s'...", snapshot_id)
    try:
        response = rds.create_db_snapshot(
            DBInstanceIdentifier=db_instance_identifier,
            DBSnapshotIdentifier=snapshot_id,
        )
    except (ClientError, BotoCoreError) as exc:
        logging.error("Failed to create snapshot for '%s': %s",
                      db_instance_identifier, exc)
        raise

    created_id = response["DBSnapshot"]["DBSnapshotIdentifier"]
    logging.info("Snapshot request submitted successfully: %s", created_id)
    return created_id


def wait_for_instance_available(rds: Any, db_instance_identifier: str) -> None:
    """Wait until an RDS instance reaches the available state."""
    logging.info("Waiting for RDS instance '%s' to become available...",
                 db_instance_identifier)
    try:
        waiter = rds.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)
    except (ClientError, BotoCoreError) as exc:
        logging.error("Error while waiting for instance '%s': %s",
                      db_instance_identifier, exc)
        raise
    logging.info("RDS instance '%s' is now available.",
                 db_instance_identifier)


def wait_for_instance_stopped(rds: Any, db_instance_identifier: str) -> None:
    """Wait until an RDS instance reaches the stopped state."""
    logging.info("Waiting for RDS instance '%s' to stop...",
                 db_instance_identifier)
    try:
        waiter = rds.get_waiter("db_instance_stopped")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)
    except (ClientError, BotoCoreError) as exc:
        logging.error("Error while waiting for instance '%s': %s",
                      db_instance_identifier, exc)
        raise
    logging.info("RDS instance '%s' is now stopped.", db_instance_identifier)


def wait_for_snapshot(rds: Any, snapshot_id: str) -> None:
    """Wait until a manual RDS snapshot becomes available."""
    logging.info("Waiting for snapshot '%s' to become available...", snapshot_id)
    try:
        waiter = rds.get_waiter("db_snapshot_available")
        waiter.wait(DBSnapshotIdentifier=snapshot_id)
    except (ClientError, BotoCoreError) as exc:
        logging.error("Error while waiting for snapshot '%s': %s",
                      snapshot_id, exc)
        raise
    logging.info("Snapshot '%s' is now available.", snapshot_id)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Provision and manage an AWS RDS MySQL instance."
    )
    parser.add_argument(
        "action",
        choices=["create", "start", "stop", "snapshot"],
        help="RDS action to perform.",
    )
    parser.add_argument(
        "--db-instance",
        required=True,
        help="RDS DB instance identifier.",
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=f"AWS region (default: {DEFAULT_REGION}).",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until the requested operation completes.",
    )
    parser.add_argument(
        "--master-username",
        default="admin",
        help="Master username for a new MySQL instance (create only).",
    )
    parser.add_argument(
        "--master-password",
        default=None,
        help="Master password for create. Prefer RDS_MASTER_PASSWORD env var.",
    )
    parser.add_argument(
        "--db-class",
        default="db.t3.micro",
        help="RDS instance class for create (default: db.t3.micro).",
    )
    parser.add_argument(
        "--storage",
        type=int,
        default=20,
        help="Allocated storage in GiB for create (default: 20).",
    )
    parser.add_argument(
        "--log-file",
        default=DEFAULT_LOG_FILE,
        help=f"Local log path (default: {DEFAULT_LOG_FILE}).",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=DEFAULT_LOG_LEVEL,
        help="Logging level.",
    )
    return parser


def main() -> int:
    """Parse arguments, execute the requested RDS operation, and return a status."""
    args = build_parser().parse_args()
    configure_logging(args.log_file, args.log_level)

    try:
        rds = get_rds_client(args.region)

        if args.action == "create":
            password = args.master_password or os.getenv("RDS_MASTER_PASSWORD")
            if not password:
                raise ValueError(
                    "For create, set RDS_MASTER_PASSWORD or pass --master-password."
                )

            created_id = create_db_instance(
                rds=rds,
                db_instance_identifier=args.db_instance,
                master_username=args.master_username,
                master_password=password,
                db_instance_class=args.db_class,
                allocated_storage=args.storage,
            )
            if args.wait:
                wait_for_instance_available(rds, created_id)

        elif args.action == "start":
            start_db_instance(rds, args.db_instance)
            if args.wait:
                wait_for_instance_available(rds, args.db_instance)

        elif args.action == "stop":
            stop_db_instance(rds, args.db_instance)
            if args.wait:
                wait_for_instance_stopped(rds, args.db_instance)

        elif args.action == "snapshot":
            check_instance(rds, args.db_instance)
            snapshot_id = create_snapshot(rds, args.db_instance)
            if args.wait:
                wait_for_snapshot(rds, snapshot_id)

        return 0

    except (ClientError, BotoCoreError, ValueError) as exc:
        logging.error("Operation failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
