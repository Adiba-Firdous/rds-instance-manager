# AWS RDS MySQL Instance Manager

A Python automation project using **boto3** to provision a MySQL Amazon RDS
instance and manage RDS instances on demand.

## Features

- Provision a new MySQL RDS instance
- Start an existing RDS instance
- Stop an existing RDS instance
- Create a manual RDS snapshot
- Wait for create/start/stop/snapshot operations to finish
- CLI with `argparse`
- Configurable region, log file, and log level
- BotoCoreError/ClientError handling
- Type hints and function docstrings
- AWS credentials are never stored in source code

## Project structure

```text
rds-instance-manager/
├── rds_manager.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 1. Configure AWS

Configure the AWS CLI:

```bash
aws configure
aws sts get-caller-identity
```

Use an IAM identity with permissions appropriate for the RDS operations.

Never commit AWS access keys, secret keys, or database passwords to GitHub.

## 2. Install dependencies

```bash
python -m venv .venv
```

Windows Git Bash:

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
```

## 3. Verify the CLI

```bash
python rds_manager.py --help
```

## 4. Provision a new MySQL RDS instance

Set the master password through an environment variable so it is not stored
in the source code or shell history:

```bash
export RDS_MASTER_PASSWORD='YourStrongPassword123!'
```

Then:

```bash
python rds_manager.py create \
  --db-instance mysql-demo-rds \
  --master-username admin \
  --db-class db.t3.micro \
  --storage 20 \
  --region ap-south-1 \
  --wait
```

On Windows Command Prompt, use:

```cmd
set RDS_MASTER_PASSWORD=YourStrongPassword123!
```

The default configuration uses MySQL, 20 GiB of storage, `db.t3.micro`,
7-day backup retention, gp3 storage, and `PubliclyAccessible=False`.

**AWS costs may apply.** Delete resources when you are finished with testing.

## 5. Start an existing RDS instance

```bash
python rds_manager.py start \
  --db-instance mysql-demo-rds \
  --region ap-south-1 \
  --wait
```

## 6. Stop an RDS instance

```bash
python rds_manager.py stop \
  --db-instance mysql-demo-rds \
  --region ap-south-1 \
  --wait
```

## 7. Create a snapshot

```bash
python rds_manager.py snapshot \
  --db-instance mysql-demo-rds \
  --region ap-south-1 \
  --wait
```

The script generates a timestamped snapshot identifier.

## Logging

Actions are logged to `rds_manager.log` by default.

You can change the log location and level:

```bash
python rds_manager.py start \
  --db-instance mysql-demo-rds \
  --log-file logs/rds.log \
  --log-level DEBUG
```

## Important AWS notes

- RDS creation and state changes are asynchronous.
- `--wait` uses boto3 waiters to wait for completion.
- `db.t3.micro` availability depends on the selected region/account.
- The example creates a standard RDS MySQL instance, not an Aurora cluster.
- RDS instances and snapshots can incur AWS charges.
- Review AWS pricing and delete test resources when finished.
