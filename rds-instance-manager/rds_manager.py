#!/usr/bin/env python3
"""
AWS RDS Instance Manager

Start, stop, or create a snapshot of an Amazon RDS DB instance.

AWS credentials are NOT stored in this script. boto3 uses the standard
AWS credential chain (AWS CLI profile, environment variables, IAM role, etc.).
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError


LOG_FILE = "rds_manager.log"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_rds_client(region: str):
    return boto3.client("rds", region_name=region)


def check_instance(rds, db_instance_identifier: str) -> dict:
    response = rds.describe_db_instances(
        DBInstanceIdentifier=db_instance_identifier
    )
    instances = response.get("DBInstances", [])

    if not instances:
        raise ValueError(f"RDS instance not found: {db_instance_identifier}")

    return instances[0]


def start_db_instance(rds, db_instance_identifier: str) -> None:
    instance = check_instance(rds, db_instance_identifier)
    status = instance["DBInstanceStatus"]

    if status == "available":
        logging.info("RDS instance '%s' is already running.", db_instance_identifier)
        return

    logging.info("Starting RDS instance '%s' (current status: %s)...",
                 db_instance_identifier, status)
    rds.start_db_instance(DBInstanceIdentifier=db_instance_identifier)
    logging.info("Start request submitted successfully.")


def stop_db_instance(rds, db_instance_identifier: str) -> None:
    instance = check_instance(rds, db_instance_identifier)
    status = instance["DBInstanceStatus"]

    if status == "stopped":
        logging.info("RDS instance '%s' is already stopped.", db_instance_identifier)
        return

    logging.info("Stopping RDS instance '%s' (current status: %s)...",
                 db_instance_identifier, status)
    rds.stop_db_instance(DBInstanceIdentifier=db_instance_identifier)
    logging.info("Stop request submitted successfully.")


def create_snapshot(rds, db_instance_identifier: str) -> str:
    # Snapshot identifiers must be lowercase, start with a letter, and
    # contain only letters, numbers, and hyphens.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot_id = f"{db_instance_identifier}-snapshot-{timestamp}".lower()

    logging.info("Creating snapshot '%s'...", snapshot_id)

    response = rds.create_db_snapshot(
        DBInstanceIdentifier=db_instance_identifier,
        DBSnapshotIdentifier=snapshot_id,
    )

    created_id = response["DBSnapshot"]["DBSnapshotIdentifier"]
    logging.info("Snapshot request submitted successfully: %s", created_id)
    return created_id


def wait_for_action(rds, action: str, db_instance_identifier: str) -> None:
    if action == "start":
        logging.info("Waiting for RDS instance to become available...")
        waiter = rds.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)
        logging.info("RDS instance is now available.")

    elif action == "stop":
        logging.info("Waiting for RDS instance to stop...")
        waiter = rds.get_waiter("db_instance_stopped")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)
        logging.info("RDS instance is now stopped.")

    elif action == "snapshot":
        logging.info("Waiting for snapshot to become available...")
        # The snapshot identifier is not available here because the action
        # function intentionally returns only the created identifier.
        # Snapshot waiting is handled in main().
        return


def wait_for_snapshot(rds, snapshot_id: str) -> None:
    logging.info("Waiting for snapshot '%s' to become available...", snapshot_id)
    waiter = rds.get_waiter("db_snapshot_available")
    waiter.wait(DBSnapshotIdentifier=snapshot_id)
    logging.info("Snapshot is now available.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Start, stop, or snapshot an AWS RDS DB instance."
    )

    parser.add_argument(
        "action",
        choices=["start", "stop", "snapshot"],
        help="Action to perform.",
    )
    parser.add_argument(
        "--db-instance",
        required=True,
        help="RDS DB instance identifier.",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region, e.g. ap-south-1. Uses AWS default if omitted.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until the requested operation completes.",
    )

    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()

    try:
        rds = get_rds_client(args.region)

        # This also verifies that the instance exists before changing it.
        instance = check_instance(rds, args.db_instance)
        logging.info(
            "Connected to RDS instance '%s' | engine=%s | status=%s",
            args.db_instance,
            instance.get("Engine", "unknown"),
            instance.get("DBInstanceStatus", "unknown"),
        )

        if args.action == "start":
            start_db_instance(rds, args.db_instance)
            if args.wait:
                wait_for_action(rds, "start", args.db_instance)

        elif args.action == "stop":
            stop_db_instance(rds, args.db_instance)
            if args.wait:
                wait_for_action(rds, "stop", args.db_instance)

        elif args.action == "snapshot":
            snapshot_id = create_snapshot(rds, args.db_instance)
            if args.wait:
                wait_for_snapshot(rds, snapshot_id)

        return 0

    except (ClientError, BotoCoreError, ValueError) as exc:
        logging.error("Operation failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
