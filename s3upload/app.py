from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import boto3
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, DirectoryTree, Header, Input, Label, Select


class FilePickerModal(ModalScreen[str | None]):
    CSS = """
    FilePickerModal {
        align: center middle;
    }

    #picker-dialog {
        padding: 1 2;
        background: $surface;
        border: solid $primary;
        width: 72;
        height: 32;
    }

    #picker-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #file-tree {
        height: 1fr;
        border: solid $primary-darken-2;
        margin-bottom: 1;
    }

    #selected-path {
        margin-bottom: 1;
        color: $text-muted;
    }

    #picker-buttons {
        height: auto;
    }

    #select-btn {
        margin-right: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Container(id="picker-dialog"):
            yield Label("Select a file to upload", id="picker-title")
            yield DirectoryTree(str(Path.home()), id="file-tree")
            yield Label("No file selected", id="selected-path")
            with Horizontal(id="picker-buttons"):
                yield Button("Select", id="select-btn", variant="primary", disabled=True)
                yield Button("Cancel", id="cancel-btn")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self._selected = str(event.path)
        self.query_one("#selected-path", Label).update(self._selected)
        self.query_one("#select-btn", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "select-btn":
            self.dismiss(self._selected)


class S3UploadApp(App):
    TITLE = "S3Upload"
    CSS = """
    Screen {
        background: $surface-darken-1;
    }

    #main {
        padding: 1 2;
        height: 1fr;
    }

    #credentials-row {
        height: auto;
        margin-bottom: 1;
    }

    #profile-col {
        width: 1fr;
        padding-right: 2;
        height: auto;
    }

    #region-col {
        width: 1fr;
        height: auto;
    }

    .field-label {
        text-style: bold;
    }

    #bucket-row {
        height: auto;
        margin-bottom: 1;
    }

    #bucket-select {
        width: 36;
    }

    #refresh-btn {
        margin-top: 1;
        width: auto;
    }

    #contents-label {
        text-style: bold;
        margin-top: 1;
    }

    #contents-table {
        height: 1fr;
    }

    #action-row {
        height: auto;
        margin-top: 1;
        align: left middle;
    }

    #upload-btn {
        width: auto;
        margin-right: 1;
    }

    #close-btn {
        width: auto;
        dock: right;
    }
    """

    def __init__(self, profile: Optional[str] = None, region: str = "ca-central-1") -> None:
        super().__init__()
        self._initial_profile = profile or ""
        self._initial_region = region
        self._session: Optional[boto3.Session] = None
        self._current_bucket: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            with Horizontal(id="credentials-row"):
                with Vertical(id="profile-col"):
                    yield Label("AWS Profile", classes="field-label")
                    yield Input(
                        placeholder="Profile",
                        value=self._initial_profile,
                        id="profile-input",
                    )
                with Vertical(id="region-col"):
                    yield Label("Region", classes="field-label")
                    yield Input(
                        placeholder="ca-central-1",
                        value=self._initial_region,
                        id="region-input",
                    )
            with Vertical(id="bucket-row"):
                yield Label("S3 Bucket", classes="field-label")
                yield Select([], prompt="Select", id="bucket-select")
                yield Button("Refresh", id="refresh-btn", variant="default")
            yield Label("Bucket Contents", id="contents-label")
            yield DataTable(id="contents-table", cursor_type="row")
            with Horizontal(id="action-row"):
                yield Button("Upload", id="upload-btn", variant="primary")
                yield Button("Close", id="close-btn", variant="error")

    def on_mount(self) -> None:
        self.query_one("#contents-table", DataTable).add_columns("Name", "Size")
        self._refresh_buckets()

    def _refresh_buckets(self) -> None:
        profile = self.query_one("#profile-input", Input).value.strip() or None
        region = self.query_one("#region-input", Input).value.strip() or "ca-central-1"
        self._fetch_buckets(profile, region)

    @work(thread=True)
    def _fetch_buckets(self, profile: Optional[str], region: str) -> None:
        from .s3 import get_session, list_buckets

        try:
            session = get_session(profile=profile, region=region)
            self._session = session
            buckets = list_buckets(session)
            self.call_from_thread(self._update_bucket_select, buckets)
        except Exception as e:
            self.call_from_thread(self.notify, f"AWS error: {e}", severity="error")

    def _update_bucket_select(self, buckets: list[str]) -> None:
        self.query_one("#bucket-select", Select).set_options((b, b) for b in buckets)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "bucket-select" and event.value is not Select.BLANK:
            self._current_bucket = str(event.value)
            self._fetch_objects(self._current_bucket)

    @work(thread=True)
    def _fetch_objects(self, bucket: str) -> None:
        from .s3 import list_objects

        try:
            objects = list_objects(self._session, bucket)
            self.call_from_thread(self._update_contents_table, objects)
        except Exception as e:
            self.call_from_thread(self.notify, f"AWS error: {e}", severity="error")

    def _update_contents_table(self, objects: list[dict]) -> None:
        table = self.query_one("#contents-table", DataTable)
        table.clear()
        for obj in objects:
            table.add_row(obj["key"], _format_size(obj["size"]))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("profile-input", "region-input"):
            self._refresh_buckets()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            self._refresh_buckets()
            return
        if event.button.id == "close-btn":
            self.exit()
            return
        if event.button.id != "upload-btn":
            return
        if not self._session:
            self.notify("Not connected to AWS", severity="warning")
            return
        if not self._current_bucket:
            self.notify("Please select a bucket first", severity="warning")
            return
        bucket = self._current_bucket
        self.push_screen(FilePickerModal(), callback=lambda path: self._upload_file(path, bucket) if path else None)

    @work(thread=True)
    def _upload_file(self, file_path: str, bucket: str) -> None:
        from .s3 import upload_file

        try:
            upload_file(self._session, bucket, file_path)
            name = os.path.basename(file_path)
            self.call_from_thread(self.notify, f"Uploaded {name!r} successfully")
            self.call_from_thread(self._fetch_objects, bucket)
        except Exception as e:
            self.call_from_thread(self.notify, f"Upload failed: {e}", severity="error")


def _format_size(size: int) -> str:
    value: float = size
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"
