from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import boto3


class S3UploadApp(tk.Tk):
    def __init__(self, profile: Optional[str] = None, region: str = "ca-central-1") -> None:
        super().__init__()
        self.title("S3Upload")
        self.minsize(600, 480)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._session: Optional[boto3.Session] = None
        self._current_bucket: Optional[str] = None

        self._build_ui(profile or "", region)
        self._refresh_buckets()

    def run(self) -> None:
        self.mainloop()

    def _build_ui(self, profile: str, region: str) -> None:
        main = ttk.Frame(self, padding=10)
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(5, weight=1)

        # Profile / Region
        ttk.Label(main, text="AWS Profile", font=("", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(main, text="Region", font=("", 10, "bold")).grid(
            row=0, column=1, sticky="w"
        )
        self._profile_var = tk.StringVar(value=profile)
        ttk.Entry(main, textvariable=self._profile_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        self._region_var = tk.StringVar(value=region)
        ttk.Entry(main, textvariable=self._region_var).grid(
            row=1, column=1, sticky="ew"
        )

        # S3 Bucket
        ttk.Label(main, text="S3 Bucket", font=("", 10, "bold")).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        bucket_frame = ttk.Frame(main)
        bucket_frame.grid(row=3, column=0, columnspan=2, sticky="w")
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
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        table_frame = ttk.Frame(main)
        table_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
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
        btn_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(btn_frame, text="Upload", command=self._on_upload).pack(side="left")
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right")

    def _refresh_buckets(self) -> None:
        profile = self._profile_var.get().strip() or None
        region = self._region_var.get().strip() or "ca-central-1"
        threading.Thread(
            target=self._fetch_buckets, args=(profile, region), daemon=True
        ).start()

    def _fetch_buckets(self, profile: Optional[str], region: str) -> None:
        from .s3 import get_session, list_buckets

        try:
            session = get_session(profile=profile, region=region)
            self._session = session
            buckets = list_buckets(session)
            self.after(0, self._update_bucket_combo, buckets)
        except Exception as e:
            self.after(0, messagebox.showerror, "AWS Error", str(e))

    def _update_bucket_combo(self, buckets: list[str]) -> None:
        self._bucket_combo["values"] = buckets

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

    def _on_upload(self) -> None:
        if not self._session:
            messagebox.showwarning("Not Connected", "Not connected to AWS.")
            return
        if not self._current_bucket:
            messagebox.showwarning("No Bucket Selected", "Please select a bucket first.")
            return
        path = filedialog.askopenfilename(title="Select file to upload")
        if path:
            threading.Thread(
                target=self._upload_file, args=(path, self._current_bucket), daemon=True
            ).start()

    def _upload_file(self, file_path: str, bucket: str) -> None:
        from .s3 import upload_file

        try:
            upload_file(self._session, bucket, file_path)
            name = os.path.basename(file_path)
            self.after(0, messagebox.showinfo, "Success", f"Uploaded {name!r} successfully.")
            self.after(
                0,
                lambda: threading.Thread(
                    target=self._fetch_objects, args=(bucket,), daemon=True
                ).start(),
            )
        except Exception as e:
            self.after(0, messagebox.showerror, "Upload Failed", str(e))


def _format_size(size: int) -> str:
    value: float = size
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"
