from __future__ import annotations

import csv
import html
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Iterable

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, X, YES


def bundled_path(name: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / name
    return Path(__file__).resolve().parent / name


def load_project_metadata() -> dict[str, str]:
    pyproject_path = bundled_path("pyproject.toml")
    metadata = {"version": "unknown", "author": "unknown", "homepage": ""}
    if not pyproject_path.exists():
        return metadata

    text = pyproject_path.read_text(encoding="utf-8")
    try:
        import tomllib

        project = tomllib.loads(text).get("project", {})
        urls = project.get("urls", {})
        authors = project.get("authors", [])
        metadata["version"] = project.get("version", metadata["version"])
        if authors:
            metadata["author"] = authors[0].get("name", metadata["author"])
        metadata["homepage"] = urls.get("Homepage", metadata["homepage"])
        return metadata
    except Exception:
        pass

    patterns = {
        "version": r'(?m)^version\s*=\s*"([^"]+)"',
        "author": r'authors\s*=\s*\[\{\s*name\s*=\s*"([^"]+)"',
        "homepage": r'(?m)^Homepage\s*=\s*"([^"]+)"',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            metadata[key] = match.group(1)
    return metadata


PROJECT_METADATA = load_project_metadata()
__version__ = PROJECT_METADATA["version"]
__author__ = PROJECT_METADATA["author"]
__homepage__ = PROJECT_METADATA["homepage"]


@dataclass(frozen=True)
class FileRecord:
    root: Path
    path: Path
    relative_path: str
    extension: str
    size: int
    modified_time: float

    @property
    def display_size(self) -> str:
        return format_bytes(self.size)


def normalize_extension(extension: str) -> str:
    value = extension.strip().lower()
    if not value or value == "[无后缀]":
        return ""
    return value if value.startswith(".") else f".{value}"


def discover_extensions(root: str | Path) -> list[str]:
    extensions: set[str] = set()
    root_path = Path(root)
    if not root_path.exists():
        return []
    for file_path in iter_files(root_path, True):
        suffix = file_path.suffix.lower()
        extensions.add(suffix if suffix else "[无后缀]")
    return sorted(extensions, key=lambda item: (item == "[无后缀]", item))


def collect_files(
    root: str | Path,
    include_subfolders: bool,
    selected_extensions: Iterable[str] | None = None,
) -> list[FileRecord]:
    root_path = Path(root)
    if not root_path.exists():
        raise ValueError(f"文件夹不存在或不可访问：{root_path}")

    extension_filter = None
    if selected_extensions:
        extension_filter = {normalize_extension(item) for item in selected_extensions}

    records: list[FileRecord] = []
    for file_path in iter_files(root_path, include_subfolders):
        extension = file_path.suffix.lower()
        if extension_filter is not None and extension not in extension_filter:
            continue
        stat = file_path.stat()
        try:
            relative_path = file_path.relative_to(root_path).as_posix()
        except ValueError:
            relative_path = str(file_path)
        record = FileRecord(
            root=root_path,
            path=file_path,
            relative_path=relative_path,
            extension=extension,
            size=stat.st_size,
            modified_time=stat.st_mtime,
        )
        records.append(record)
    return records


def iter_files(root: Path, include_subfolders: bool):
    if include_subfolders:
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                yield Path(dirpath) / filename
    else:
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.is_file():
                    yield Path(entry.path)


def write_reports(records: list[FileRecord], output_dir: str | Path) -> tuple[Path, Path]:
    target = Path(output_dir)
    clear_report_dir(target)
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = target / f"filelist_{stamp}.csv"
    html_path = target / f"filelist_{stamp}.html"
    write_csv(records, csv_path)
    write_html(records, html_path)
    return csv_path, html_path


def clear_report_dir(target: Path) -> None:
    if not target.exists():
        return
    for child in target.iterdir():
        if child.is_file() and child.name.startswith("filelist_") and child.suffix.lower() in {".csv", ".html"}:
            child.unlink()


def write_csv(records: list[FileRecord], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["序号", "文件名", "相对路径", "完整路径", "文件大小", "修改时间", "文件类型"])
        for index, record in enumerate(records, 1):
            writer.writerow(
                [
                    index,
                    record.path.stem,
                    record.relative_path,
                    str(record.path),
                    record.display_size,
                    datetime.fromtimestamp(record.modified_time).strftime("%Y-%m-%d %H:%M:%S"),
                    record.extension or "[无后缀]",
                ]
            )


def write_html(records: list[FileRecord], path: Path) -> None:
    body_rows = "\n".join(
        f"<tr>"
        f"<td>{index}</td>"
        f"<td>{html.escape(record.path.stem)}</td>"
        f"<td>{html.escape(record.relative_path)}</td>"
        f"<td>{html.escape(str(record.path))}</td>"
        f"<td>{html.escape(record.display_size)}</td>"
        f"<td>{html.escape(datetime.fromtimestamp(record.modified_time).strftime('%Y-%m-%d %H:%M:%S'))}</td>"
        f"<td>{html.escape(record.extension or '[无后缀]')}</td>"
        f"</tr>"
        for index, record in enumerate(records, 1)
    )
    total_size = sum(r.size for r in records)
    
    html_content = (
        "<!doctype html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <title>file-lister 文件清单</title>\n"
        "  <style>\n"
        "    body { font-family: \"Microsoft YaHei\", Arial, sans-serif; margin: 32px; color: #18212f; background: #f6f8fb; }\n"
        "    h1 { margin: 0 0 16px; }\n"
        "    .summary { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }\n"
        "    .summary span { border: 1px solid #d7dee8; border-radius: 8px; padding: 8px 12px; background: #fff; }\n"
        "    .summary b { margin-right: 8px; }\n"
        "    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 0 0 16px; }\n"
        "    input, select { border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; min-height: 36px; background: #fff; }\n"
        "    input { min-width: 320px; }\n"
        "    button { border: 1px solid #2563eb; border-radius: 8px; padding: 8px 12px; color: #fff; background: #2563eb; cursor: pointer; }\n"
        "    .count { color: #52616f; margin-left: auto; }\n"
        "    table { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }\n"
        "    th, td { border-bottom: 1px solid #e3e8ef; padding: 9px 10px; text-align: left; vertical-align: top; }\n"
        "    th { background: #eef3f8; position: sticky; top: 0; }\n"
        "    tr:nth-child(even) { background: #fbfcfe; }\n"
        "    tr.hidden { display: none; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>file-lister 文件清单</h1>\n"
        "  <div class=\"summary\">\n"
        f"    <span><b>文件总数</b>{len(records)}</span>\n"
        f"    <span><b>总大小</b>{format_bytes(total_size)}</span>\n"
        "  </div>\n"
        "  <div class=\"toolbar\">\n"
        "    <select id=\"extFilter\">\n"
        "      <option value=\"全部\">全部类型</option>\n"
        "      <option value=\"[无后缀]\">[无后缀]</option>\n"
        "    </select>\n"
        "    <input id=\"keywordFilter\" placeholder=\"输入关键字筛选文件名或路径\">\n"
        "    <button type=\"button\" id=\"resetFilter\">清空筛选</button>\n"
        "    <span class=\"count\" id=\"visibleCount\"></span>\n"
        "  </div>\n"
        "  <table>\n"
        "    <thead><tr><th>序号</th><th>文件名</th><th>相对路径</th><th>完整路径</th><th>文件大小</th><th>修改时间</th><th>文件类型</th></tr></thead>\n"
        f"    <tbody>{body_rows}</tbody>\n"
        "  </table>\n"
        "  <script>\n"
        "    const extFilter = document.getElementById(\"extFilter\");\n"
        "    const keywordFilter = document.getElementById(\"keywordFilter\");\n"
        "    const resetFilter = document.getElementById(\"resetFilter\");\n"
        "    const visibleCount = document.getElementById(\"visibleCount\");\n"
        "    const rows = Array.from(document.querySelectorAll(\"tbody tr\"));\n"
        "\n"
        "    const extensions = new Set();\n"
        "    rows.forEach(row => {\n"
        "      const ext = row.cells[6].textContent;\n"
        "      extensions.add(ext);\n"
        "    });\n"
        "    extensions.forEach(ext => {\n"
        "      const opt = document.createElement(\"option\");\n"
        "      opt.value = ext;\n"
        "      opt.textContent = ext;\n"
        "      extFilter.appendChild(opt);\n"
        "    });\n"
        "\n"
        "    function applyFilter() {\n"
        "      const ext = extFilter.value;\n"
        "      const keyword = keywordFilter.value.trim().toLowerCase();\n"
        "      let visible = 0;\n"
        "      rows.forEach(row => {\n"
        "        const extMatched = ext === \"全部\" || row.cells[6].textContent === ext;\n"
        "        const keywordMatched = !keyword || row.innerText.toLowerCase().includes(keyword);\n"
        "        const show = extMatched && keywordMatched;\n"
        "        row.classList.toggle(\"hidden\", !show);\n"
        "        if (show) visible += 1;\n"
        "      });\n"
        "      visibleCount.textContent = \"显示 \" + visible + \" / \" + rows.length + \" 项\";\n"
        "    }\n"
        "\n"
        "    extFilter.addEventListener(\"change\", applyFilter);\n"
        "    keywordFilter.addEventListener(\"input\", applyFilter);\n"
        "    resetFilter.addEventListener(\"click\", () => {\n"
        "      extFilter.value = \"全部\";\n"
        "      keywordFilter.value = \"\";\n"
        "      applyFilter();\n"
        "    });\n"
        "    applyFilter();\n"
        "  </script>\n"
        "</body>\n"
        "</html>"
    )
    
    path.write_text(html_content, encoding="utf-8")


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / name
    return project_root() / "assets" / name


ASSET_ICON = asset_path("app.ico")
REPORT_DIR = project_root() / "reports"


class FileListerApp(ttk.Window):
    def __init__(self) -> None:
        super().__init__(themename="yeti")
        self.title(f"file-lister V{__version__}")
        self.geometry("1240x760")
        self.minsize(980, 620)
        if ASSET_ICON.exists():
            self.iconbitmap(str(ASSET_ICON))

        self.folder_var = tk.StringVar()
        self.theme_var = tk.StringVar(value="yeti")
        self.report_var = tk.StringVar(value="尚未生成报告")
        self.summary_var = tk.StringVar(value="选择一个文件夹后开始获取文件清单")
        self.progress_var = tk.StringVar(value="")
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.latest_html_report: Path | None = None
        self.latest_csv_report: Path | None = None
        self.extension_vars: dict[str, tk.BooleanVar] = {}
        self.records: list[FileRecord] = []
        self.filtered_records: list[FileRecord] = []
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="file-lister", font=("Microsoft YaHei UI", 22, "bold"))
        title.grid(row=0, column=0, sticky="w")
        meta = ttk.Label(header, text=f"V{__version__} 文件清单工具", bootstyle="secondary")
        meta.grid(row=1, column=0, sticky="w", pady=(2, 0))

        theme_bar = ttk.Frame(header)
        theme_bar.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(theme_bar, text="主题").pack(side=LEFT, padx=(0, 8))
        theme_box = ttk.Combobox(
            theme_bar,
            textvariable=self.theme_var,
            values=sorted(self.style.theme_names()),
            width=18,
            state="readonly",
        )
        theme_box.pack(side=LEFT)
        theme_box.bind("<<ComboboxSelected>>", self._change_theme)
        ttk.Button(theme_bar, text="关于", bootstyle="secondary-outline", command=self.show_about).pack(side=LEFT, padx=(8, 0))

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))

        controls = ttk.Frame(main, padding=12)
        main.add(controls, weight=1)
        results = ttk.Frame(main, padding=(10, 12, 12, 12))
        main.add(results, weight=4)

        self._build_controls(controls)
        self._build_results(results)

        footer = ttk.Frame(self, padding=(18, 0, 18, 14))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.summary_var, bootstyle="secondary").grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.progress_var, bootstyle="info").grid(row=0, column=1, sticky="e", padx=(12, 0))

    def _build_controls(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        path_box = ttk.Labelframe(parent, text="文件夹", padding=12)
        path_box.grid(row=0, column=0, sticky="ew")
        path_box.columnconfigure(1, weight=1)

        ttk.Label(path_box, text="文件夹路径", font=("Microsoft YaHei UI", 10, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        entry = ttk.Entry(path_box, textvariable=self.folder_var)
        entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0), padx=(0, 8))
        ttk.Button(path_box, text="选择", bootstyle="secondary-outline", command=self.choose_folder).grid(row=1, column=2, sticky="e")
        ttk.Label(
            path_box,
            text="支持本地路径或网络路径",
            bootstyle="info-inverse",
            padding=(8, 10),
            wraplength=260,
            justify=LEFT,
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(6, 12),
        )

        option_box = ttk.Labelframe(parent, text="选项", padding=12)
        option_box.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Checkbutton(
            option_box,
            text="包含子文件夹",
            variable=self.include_subfolders_var,
            bootstyle="round-toggle",
        ).pack(anchor="w", pady=3)
        ttk.Label(
            option_box,
            text="取消勾选则只扫描当前文件夹，不递归子文件夹。",
            bootstyle="secondary",
            wraplength=285,
            justify=LEFT,
        ).pack(anchor="w", fill=X, pady=(0, 4))

        ext_header = ttk.Frame(option_box)
        ext_header.pack(fill=X, pady=(10, 4))
        ttk.Label(ext_header, text="动态文件格式").pack(side=LEFT)
        ttk.Button(ext_header, text="刷新", bootstyle="secondary-outline", command=self.refresh_extensions).pack(side=RIGHT)

        ext_outer = ttk.Frame(option_box)
        ext_outer.pack(fill=X)
        self.ext_canvas = tk.Canvas(ext_outer, height=126, highlightthickness=0)
        self.ext_scroll = ttk.Scrollbar(ext_outer, orient=tk.VERTICAL, command=self.ext_canvas.yview)
        self.ext_inner = ttk.Frame(self.ext_canvas)
        self.ext_inner.bind("<Configure>", lambda _: self.ext_canvas.configure(scrollregion=self.ext_canvas.bbox("all")))
        self.ext_canvas.create_window((0, 0), window=self.ext_inner, anchor="nw")
        self.ext_canvas.configure(yscrollcommand=self.ext_scroll.set)
        self.ext_canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        self.ext_scroll.pack(side=RIGHT, fill=tk.Y)

        action_box = ttk.Labelframe(parent, text="执行", padding=12)
        action_box.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        action_box.columnconfigure(0, weight=1)
        ttk.Button(action_box, text="获取文件清单", bootstyle="success", command=self.start_scan).grid(row=0, column=0, sticky="ew")
        ttk.Button(action_box, text="一键清空", bootstyle="secondary-outline", command=self.clear_all).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.progress = ttk.Progressbar(action_box, mode="indeterminate")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.refresh_extensions()

    def _build_results(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="获取文件清单", bootstyle="success", command=self.start_scan).pack(side=LEFT, padx=(0, 10))
        ttk.Label(toolbar, text="筛选").pack(side=LEFT, padx=(0, 8))
        self.ext_filter_combo = ttk.Combobox(
            toolbar,
            values=["全部"],
            width=14,
            state="readonly",
        )
        self.ext_filter_combo.pack(side=LEFT)
        self.ext_filter_combo.bind("<<ComboboxSelected>>", lambda _: self.render_records())
        self.keyword_filter = ttk.Entry(toolbar, width=20)
        self.keyword_filter.pack(side=LEFT, padx=(8, 0))
        self.keyword_filter.bind("<KeyRelease>", lambda _: self.render_records())
        ttk.Button(toolbar, text="清空筛选", bootstyle="secondary-outline", command=self.clear_filter).pack(side=LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="打开文件清单", bootstyle="secondary-outline", command=self.open_latest_csv_report).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(toolbar, text="打开生成报告", bootstyle="secondary-outline", command=self.open_latest_report).pack(side=RIGHT)

        columns = ("index", "name", "relative_path", "full_path", "size", "modified_time", "extension")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="extended")
        headings = {
            "index": "序号",
            "name": "文件名",
            "relative_path": "相对路径",
            "full_path": "完整路径",
            "size": "文件大小",
            "modified_time": "修改时间",
            "extension": "文件类型",
        }
        widths = {"index": 60, "name": 180, "relative_path": 220, "full_path": 300, "size": 90, "modified_time": 150, "extension": 90}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=70, stretch=column in {"name", "relative_path", "full_path"})
        self.tree.grid(row=1, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview)
        xscroll.grid(row=2, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            self.folder_var.set(folder)
            self.refresh_extensions()

    def refresh_extensions(self) -> None:
        for child in self.ext_inner.winfo_children():
            child.destroy()
        self.extension_vars.clear()
        folder = self.folder_var.get().strip()
        if not folder:
            ttk.Label(self.ext_inner, text="选择文件夹后显示可用格式", bootstyle="secondary").pack(anchor="w")
            return
        extensions = discover_extensions(folder)
        if not extensions:
            ttk.Label(self.ext_inner, text="未发现任何文件", bootstyle="secondary").pack(anchor="w")
            return
        for index, extension in enumerate(extensions):
            var = tk.BooleanVar(value=True)
            self.extension_vars[extension] = var
            checkbox = ttk.Checkbutton(self.ext_inner, text=extension, variable=var)
            checkbox.grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 14), pady=2)

    def start_scan(self) -> None:
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("缺少路径", "请先选择一个文件夹。")
            return
        selected_extensions = [ext for ext, var in self.extension_vars.items() if var.get()]
        if not selected_extensions:
            messagebox.showwarning("缺少筛选", "请至少选择一种文件格式，或刷新后全选。")
            return
        self.progress.start(12)
        self.progress_var.set("正在扫描文件...")
        self.summary_var.set("扫描进行中")
        thread = threading.Thread(
            target=self._scan_worker,
            args=(folder, self.include_subfolders_var.get(), selected_extensions),
            daemon=True,
        )
        thread.start()
        self.after(120, self._poll_worker)

    def _scan_worker(
        self,
        folder: str,
        include_subfolders: bool,
        selected_extensions: list[str],
    ) -> None:
        try:
            records = collect_files(folder, include_subfolders, selected_extensions)
            records.sort(key=lambda r: r.relative_path.casefold())
            reports = write_reports(records, REPORT_DIR)
            self.worker_queue.put(("done", (records, reports)))
        except Exception as exc:
            self.worker_queue.put(("error", exc))

    def _poll_worker(self) -> None:
        try:
            kind, payload = self.worker_queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_worker)
            return
        self.progress.stop()
        self.progress_var.set("")
        if kind == "error":
            messagebox.showerror("扫描失败", str(payload))
            self.summary_var.set("扫描失败")
            return
        records, reports = payload
        self.records = records
        self._update_ext_filter()
        self.render_records()
        csv_path, html_path = reports
        self.latest_csv_report = csv_path
        self.latest_html_report = html_path
        self.report_var.set(f"已生成：{csv_path.name} / {html_path.name}")
        self.summary_var.set(self._summary_text(records))

    def _update_ext_filter(self) -> None:
        extensions = set(r.extension or "[无后缀]" for r in self.records)
        self.ext_filter_combo["values"] = ["全部"] + sorted(extensions)
        self.ext_filter_combo.current(0)

    def render_records(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        ext_filter = self.ext_filter_combo.get()
        keyword = self.keyword_filter.get().strip().lower()
        self.filtered_records = []
        for record in self.records:
            ext_match = ext_filter == "全部" or (record.extension or "[无后缀]") == ext_filter
            keyword_match = not keyword or keyword in record.path.name.lower() or keyword in record.relative_path.lower()
            if ext_match and keyword_match:
                self.filtered_records.append(record)
        for index, record in enumerate(self.filtered_records):
            self.tree.insert(
                "",
                END,
                iid=str(index),
                values=(
                    index + 1,
                    record.path.stem,
                    record.relative_path,
                    str(record.path),
                    record.display_size,
                    datetime.fromtimestamp(record.modified_time).strftime("%Y-%m-%d %H:%M:%S"),
                    record.extension or "[无后缀]",
                ),
            )

    def clear_filter(self) -> None:
        self.ext_filter_combo.current(0)
        self.keyword_filter.delete(0, tk.END)
        self.render_records()

    def clear_all(self) -> None:
        self.folder_var.set("")
        self.report_var.set("尚未生成报告")
        self.summary_var.set("选择一个文件夹后开始获取文件清单")
        self.progress_var.set("")
        self.latest_html_report = None
        self.latest_csv_report = None
        self.records = []
        self.filtered_records = []
        self.ext_filter_combo["values"] = ["全部"]
        self.ext_filter_combo.current(0)
        self.keyword_filter.delete(0, tk.END)
        self.render_records()
        self.refresh_extensions()

    def open_latest_report(self) -> None:
        if not self.latest_html_report or not self.latest_html_report.exists():
            messagebox.showinfo("没有报告", "请先完成一次扫描，生成 HTML 报告。")
            return
        if sys.platform.startswith("win"):
            os.startfile(self.latest_html_report)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self.latest_html_report)], check=False)
        else:
            subprocess.run(["xdg-open", str(self.latest_html_report)], check=False)

    def open_latest_csv_report(self) -> None:
        if not self.latest_csv_report or not self.latest_csv_report.exists():
            messagebox.showinfo("没有报告", "请先完成一次扫描，生成 CSV 报告。")
            return
        if sys.platform.startswith("win"):
            os.startfile(self.latest_csv_report)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self.latest_csv_report)], check=False)
        else:
            subprocess.run(["xdg-open", str(self.latest_csv_report)], check=False)

    def open_reports(self) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(REPORT_DIR)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(REPORT_DIR)], check=False)
        else:
            subprocess.run(["xdg-open", str(REPORT_DIR)], check=False)

    def _change_theme(self, _: object = None) -> None:
        self.style.theme_use(self.theme_var.get())

    def open_homepage(self) -> None:
        webbrowser.open(__homepage__)

    def show_about(self) -> None:
        dialog = ttk.Toplevel(self)
        dialog.title("关于 file-lister")
        dialog.geometry("460x260")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        self._center_dialog(dialog, 460, 260)

        container = ttk.Frame(dialog, padding=22)
        container.pack(fill=BOTH, expand=YES)
        ttk.Label(container, text="file-lister", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w")
        ttk.Label(container, text=f"版本 V{__version__}", bootstyle="secondary").pack(anchor="w", pady=(4, 0))
        ttk.Label(container, text=f"作者：{__author__}", bootstyle="secondary").pack(anchor="w", pady=(8, 0))
        ttk.Label(container, text="开源协议：MIT", bootstyle="secondary").pack(anchor="w", pady=(4, 0))
        link = ttk.Label(container, text=__homepage__, bootstyle="primary", cursor="hand2")
        link.pack(anchor="w", pady=(14, 0))
        link.bind("<Button-1>", lambda _: self.open_homepage())
        ttk.Button(container, text="关闭", bootstyle="primary", command=dialog.destroy).pack(anchor="e", pady=(24, 0))

    def _center_dialog(self, dialog: tk.Toplevel, width: int, height: int) -> None:
        self.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _summary_text(self, records: list[FileRecord]) -> str:
        total_size = sum(r.size for r in records)
        return f"共 {len(records)} 个文件 | 总大小 {format_bytes(total_size)}"


def main() -> None:
    app = FileListerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
