import click

from . import __version__


@click.command("s3upload")
@click.option("-p", "--profile", default=None, help="Profile to use to authenticate an AWS account.")
@click.option(
    "-r", "--region", default="ca-central-1", show_default=True, help="AWS region the bucket is in."
)
@click.version_option(__version__, "-v", "--version")
def main(profile: str | None, region: str) -> None:
    """Upload or list files in an S3 bucket."""
    from .app import S3UploadApp

    S3UploadApp(profile=profile, region=region).run()
