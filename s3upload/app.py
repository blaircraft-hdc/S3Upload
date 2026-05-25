from __future__ import annotations

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import boto3


class S3UploadApp(tk.Tk):
    def __init__(
        self,
        profile: Optional[str] = None,
        region: str = "ca-central-1",
        bucket: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.title("S3Upload")
        self.minsize(600, 480)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._session: Optional[boto3.Session] = None
        self._current_bucket: Optional[str] = None
        self._initial_bucket: Optional[str] = bucket
        self._pasted_access_key: Optional[str] = None
        self._pasted_secret_key: Optional[str] = None
        self._pasted_session_token: Optional[str] = None

        self._build_ui(profile or "", region)
        self._refresh_buckets()

    def run(self) -> None:
        self.mainloop()

    def _build_ui(self, profile: str, region: str) -> None:
        main = ttk.Frame(self, padding=10)
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.columnconfigure(2, weight=1)
        main.rowconfigure(5, weight=1)

        # Profile / Paste Credentials / Region
        ttk.Label(main, text="AWS Profile", font=("", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(main, text="Region", font=("", 10, "bold")).grid(
            row=0, column=2, sticky="w"
        )
        self._profile_var = tk.StringVar(value=profile)
        ttk.Entry(main, textvariable=self._profile_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(main, text="Paste Credentials", command=self._open_paste_dialog).grid(
            row=1, column=1, padx=6
        )
        self._region_var = tk.StringVar(value=region)
        ttk.Entry(main, textvariable=self._region_var).grid(
            row=1, column=2, sticky="ew", padx=(6, 0)
        )

        # S3 Bucket
        ttk.Label(main, text="S3 Bucket", font=("", 10, "bold")).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        bucket_frame = ttk.Frame(main)
        bucket_frame.grid(row=3, column=0, columnspan=3, sticky="w")
        self._bucket_var = tk.StringVar()
        self._bucket_combo = ttk.Combobox(
            bucket_frame, textvariable=self._bucket_var, state="readonly", width=42
        )
        self._bucket_combo.pack(side="left")
        self._bucket_combo.bind("<<ComboboxSelected>>", self._on_bucket_selected)
        ttk.Button(bucket_frame, text="Refresh", command=self._refresh_buckets).pack(
            side="left", padx=(6, 0)
        )

        # Bucket Contents
        ttk.Label(main, text="Bucket Contents", font=("", 10, "bold")).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        table_frame = ttk.Frame(main)
        table_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self._table = ttk.Treeview(
            table_frame, columns=("name", "size"), show="headings", selectmode="browse"
        )
        self._table.heading("name", text="Name")
        self._table.heading("size", text="Size")
        self._table.column("name", stretch=True)
        self._table.column("size", width=100, stretch=False)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._table.yview)
        self._table.configure(yscrollcommand=scrollbar.set)
        self._table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(btn_frame, text="Upload Files...", command=self._on_upload_files).pack(side="left")
        ttk.Button(btn_frame, text="Upload Folder...", command=self._on_upload_folder).pack(side="left", padx=(6, 0))
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right")

    def _open_paste_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Paste AWS Credentials")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Paste your AWS temporary credentials below:").pack(anchor="w")
        text = tk.Text(frame, width=70, height=6, wrap="none", font=("Courier", 10))
        text.pack(fill="both", expand=True, pady=(4, 8))
        text.focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")

        def apply() -> None:
            creds = _parse_credentials(text.get("1.0", "end"))
            if not creds.get("AWS_ACCESS_KEY_ID") or not creds.get("AWS_SECRET_ACCESS_KEY"):
                messagebox.showwarning(
                    "Invalid Credentials",
                    "Could not find AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in pasted text.",
                    parent=dialog,
                )
                return
            self._pasted_access_key = creds["AWS_ACCESS_KEY_ID"]
            self._pasted_secret_key = creds["AWS_SECRET_ACCESS_KEY"]
            self._pasted_session_token = creds.get("AWS_SESSION_TOKEN")
            dialog.destroy()
            self._refresh_buckets()

        ttk.Button(btn_frame, text="Apply", command=apply).pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=(6, 0))

    def _refresh_buckets(self) -> None:
        profile = self._profile_var.get().strip() or None
        region = self._region_var.get().strip() or "ca-central-1"
        threading.Thread(
            target=self._fetch_buckets, args=(profile, region), daemon=True
        ).start()

    def _fetch_buckets(self, profile: Optional[str], region: str) -> None:
        from .s3 import get_session, list_buckets

        try:
            session = get_session(
                profile=profile,
                region=region,
                access_key=self._pasted_access_key,
                secret_key=self._pasted_secret_key,
                session_token=self._pasted_session_token,
            )
            self._session = session
            buckets = list_buckets(session)
            self.after(0, self._update_bucket_combo, buckets)
        except Exception as e:
            self.after(0, messagebox.showerror, "AWS Error", str(e))

    def _update_bucket_combo(self, buckets: list[str]) -> None:
        self._bucket_combo["values"] = buckets
        if self._initial_bucket and self._initial_bucket in buckets:
            self._bucket_var.set(self._initial_bucket)
            self._on_bucket_selected()

    def _on_bucket_selected(self, event: object = None) -> None:
        bucket = self._bucket_var.get()
        if bucket:
            self._current_bucket = bucket
            threading.Thread(
                target=self._fetch_objects, args=(bucket,), daemon=True
            ).start()

    def _fetch_objects(self, bucket: str) -> None:
        from .s3 import list_objects

        try:
            objects = list_objects(self._session, bucket)
            self.after(0, self._update_table, objects)
        except Exception as e:
            self.after(0, messagebox.showerror, "AWS Error", str(e))

    def _update_table(self, objects: list[dict]) -> None:
        self._table.delete(*self._table.get_children())
        for obj in objects:
            self._table.insert("", "end", values=(obj["key"], _format_size(obj["size"])))

    def _check_ready(self) -> bool:
        if not self._session:
            messagebox.showwarning("Not Connected", "Not connected to AWS.")
            return False
        if not self._current_bucket:
            messagebox.showwarning("No Bucket Selected", "Please select a bucket first.")
            return False
        return True

    def _on_upload_files(self) -> None:
        if not self._check_ready():
            return
        paths = filedialog.askopenfilenames(title="Select files to upload")
        if paths:
            threading.Thread(
                target=self._upload_files, args=(list(paths), self._current_bucket), daemon=True
            ).start()

    def _on_upload_folder(self) -> None:
        if not self._check_ready():
            return
        folder = filedialog.askdirectory(title="Select folder to upload")
        if folder:
            threading.Thread(
                target=self._upload_folder_task, args=(folder, self._current_bucket), daemon=True
            ).start()

    def _upload_files(self, file_paths: list[str], bucket: str) -> None:
        from .s3 import upload_file

        failed: list[tuple[str, str]] = []
        for path in file_paths:
            try:
                upload_file(self._session, bucket, path)  # type: ignore[arg-type]
            except Exception as e:
                failed.append((os.path.basename(path), str(e)))

        succeeded = len(file_paths) - len(failed)

        def _done() -> None:
            if failed:
                errors = "\n".join(f"{n}: {e}" for n, e in failed)
                messagebox.showwarning(
                    "Upload Partial",
                    f"Uploaded {succeeded} of {len(file_paths)} file(s).\n\nFailed:\n{errors}",
                )
            else:
                messagebox.showinfo("Success", f"Uploaded {succeeded} file(s) successfully.")
            threading.Thread(target=self._fetch_objects, args=(bucket,), daemon=True).start()

        self.after(0, _done)

    def _upload_folder_task(self, folder_path: str, bucket: str) -> None:
        from .s3 import upload_folder

        succeeded, failed = upload_folder(self._session, bucket, folder_path)  # type: ignore[arg-type]

        def _done() -> None:
            if failed:
                errors = "\n".join(f"{os.path.basename(p)}: {e}" for p, e in failed)
                messagebox.showwarning(
                    "Upload Partial",
                    f"Uploaded {len(succeeded)} file(s).\n\nFailed:\n{errors}",
                )
            else:
                messagebox.showinfo("Success", f"Uploaded {len(succeeded)} file(s) successfully.")
            threading.Thread(target=self._fetch_objects, args=(bucket,), daemon=True).start()

        self.after(0, _done)


def _parse_credentials(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        match = re.search(rf'{key}\s*=\s*"?([^\s"]+)"?', text)
        if match:
            result[key] = match.group(1)
    return result


def _format_size(size: int) -> str:
    value: float = size
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"
