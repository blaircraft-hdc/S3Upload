# S3Upload

A GUI for browsing and uploading files to AWS S3.

<img width="600" height="512" alt="image" src="https://github.com/user-attachments/assets/cd857ab7-a435-4c8c-837f-83bd30b600ef" />

## Features

- Browse S3 buckets and navigate folders
- Upload individual files or entire folders
- Delete objects, with optional confirmation prompt
- View or edit objects (downloads and opens in your default app or `$EDITOR`)
- Authenticate via AWS named profiles, pasted temporary credentials, or the default credential chain

## Installation

Requires Python 3.11+.

**With `uv` (recommended):**
```bash
uv pip install s3upload
```

**With `pip`:**
```bash
pip install s3upload
```

**As a standalone tool with `pipx`:**
```bash
pipx install s3upload
```

## Usage

```
Usage: s3upload [OPTIONS]

  Upload or list files in an S3 bucket.

Options:
  -p, --profile TEXT        Profile to use to authenticate an AWS account.
  -r, --region TEXT         AWS region the bucket is in.  [default: ca-central-1]
  -b, --bucket TEXT         Name of S3 bucket to open on launch.
  -n, --no-confirm-delete   Do not confirm before deleting an object.
  -v, --version             Show the version and exit.
  --help                    Show this message and exit.
```

### Authentication

S3Upload resolves credentials in this order:

1. **Named profile** — pass `-p <profile>` to use a profile from `~/.aws/config`
2. **Pasted credentials** — click "Paste Credentials" and paste temporary credentials from the AWS console
3. **Environment variables** — if `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set they are used automatically
4. **Default credential chain** — instance profiles, SSO, etc.

### Examples

```bash
# Use a named AWS profile
s3upload --profile my-profile

# Specify a region and open a specific bucket on launch
s3upload --profile my-profile --region us-east-1 --bucket my-bucket

# Skip delete confirmation prompts
s3upload --profile my-profile --no-confirm-delete

# Use pasted temporary credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
s3upload
```

## Development

```bash
git clone <repo>
cd S3Upload

uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Lint and format:
```bash
ruff check .
ruff format .
```
