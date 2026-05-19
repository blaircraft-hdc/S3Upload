# S3Upload

A terminal UI for browsing and uploading files to AWS S3.

## Features

- Browse S3 buckets and their contents in a TUI
- Upload files via an interactive file picker
- Authenticate via AWS named profiles or pasted access keys

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
  -p, --profile TEXT  Profile to use to authenticate an AWS account.
  -r, --region TEXT   AWS region the bucket is in.  [default: ca-central-1]
  -v, --version       Show the version and exit.
  --help              Show this message and exit.
```

### Authentication

S3Upload resolves credentials in this order:

1. **Named profile** — pass `-p <profile>` to use a profile from `~/.aws/config`
2. **Environment variables** — if `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set (e.g. pasted into the terminal), they are used automatically
3. **Default credential chain** — instance profiles, SSO, etc.

### Examples

```bash
# Use a named AWS profile
s3upload --profile my-profile

# Specify a region
s3upload --profile my-profile --region us-east-1

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
