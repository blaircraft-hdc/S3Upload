import click

from . import __version__


@click.command("s3upload")
@click.option("-p", "--profile", default=None, help="Profile to use to authenticate an AWS account.")
@click.option(
    "-r", "--region", default="ca-central-1", show_default=True, help="AWS region the bucket is in."
)
@click.option("-b", "--bucket", default=None, help="Name of S3 bucket to open on launch.")
@click.option("-n", "--no-confirm-delete", is_flag=True, default=False, help="Do not confirm before deleting an object.")
@click.version_option(__version__, "-v", "--version")
def main(profile: str | None, region: str, bucket: str | None, no_confirm_delete: bool) -> None:
    """Upload or list files in an S3 bucket."""
    from .app import S3UploadApp

    S3UploadApp(profile=profile, region=region, bucket=bucket, confirm_delete=not no_confirm_delete).run()
