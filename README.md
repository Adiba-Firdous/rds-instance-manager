# AWS RDS Instance Manager

A beginner-friendly Python automation project using **boto3** to start, stop,
and create snapshots of an Amazon RDS DB instance on demand.

## Features

- Start an RDS DB instance
- Stop an RDS DB instance
- Create an RDS DB snapshot
- Optional `--wait` mode
- Command-line interface
- Local action logging in `rds_manager.log`
- No AWS credentials hard-coded in the source code

## Project structure

```text
rds-instance-manager/
├── rds_manager.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 1. Configure AWS credentials

Install and configure the AWS CLI, then verify the active identity:

```bash
aws configure
aws sts get-caller-identity
```

Use an IAM identity with only the permissions needed for this project,
such as RDS start/stop/snapshot permissions.

Do **not** commit AWS access keys or secret keys to GitHub.

## 2. Install dependencies

```bash
python -m venv .venv
```

Windows Git Bash:

```bash
source .venv/Scripts/activate
```

Then:

```bash
pip install -r requirements.txt
```

## 3. Run the script

Replace `my-rds-instance` with your actual RDS DB instance identifier.

### Start

```bash
python rds_manager.py start --db-instance my-rds-instance --region ap-south-1
```

### Stop

```bash
python rds_manager.py stop --db-instance my-rds-instance --region ap-south-1
```

### Create a snapshot

```bash
python rds_manager.py snapshot --db-instance my-rds-instance --region ap-south-1
```

### Wait for completion

Add `--wait`:

```bash
python rds_manager.py start --db-instance my-rds-instance --region ap-south-1 --wait
```

## 4. Check the CLI

```bash
python rds_manager.py --help
```

## Logging

Every action is written to:

```text
rds_manager.log
```

The log records the time, operation, status, and AWS error message if an
operation fails.

## Important AWS notes

- Starting/stopping an RDS instance can take several minutes.
- RDS snapshot creation is asynchronous.
- AWS charges can apply to RDS instances and stored snapshots.
- This script is intended for a standard RDS DB instance. Aurora uses
  cluster-level APIs and would require a separate implementation.
