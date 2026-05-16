import difflib
from pathlib import Path
from typing import Any

import ipywidgets as widgets  # type: ignore[import-untyped]
from IPython.display import clear_output, display

from .core import MAX_RESULT_BYTES, ScalpelEngine

ALLOWED_ROOT = Path("/content").resolve()
MAX_FILE_BYTES = MAX_RESULT_BYTES


class ScalpelDashboard:
    def __init__(self) -> None:
        self.engine = ScalpelEngine()
        self.current_file_path: Path | None = None

        files = self._list_allowed_files()
        self.file_selector = widgets.Select(
            options=files,
            description="Files:",
            layout={"height": "100px", "width": "95%"},
        )
        self.file_selector.observe(self.load_file, names="value")

        self.source_input = widgets.Textarea(
            description="Source:", layout={"height": "200px", "width": "95%"}
        )
        self.anchor_input = widgets.Text(value="# ANCHOR", description="Anchor:")
        self.ln_input = widgets.IntText(value=0, description="Line (0=off):")
        self.insert_input = widgets.Textarea(
            value='print("Injected!")',
            description="Payload:",
            layout={"height": "80px", "width": "95%"},
        )
        self.pos_toggle = widgets.Dropdown(
            options=["after", "before"], value="after", description="Position:"
        )

        self.run_btn = widgets.Button(
            description="Run Transformation", button_style="info", layout={"width": "47%"}
        )
        self.save_btn = widgets.Button(
            description="Save to File", button_style="success", layout={"width": "47%"}
        )
        self.run_btn.on_click(self.execute)
        self.save_btn.on_click(self.save_file)

        self.diff_area = widgets.HTML()
        self.output_area = widgets.Output()

    @staticmethod
    def _canonical_path(name: str) -> Path:
        candidate = (ALLOWED_ROOT / name).resolve()
        if ALLOWED_ROOT not in candidate.parents:
            raise ValueError("path escapes allowed root")
        if not candidate.is_file():
            raise ValueError("path is not an allowed file")
        if candidate.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("file exceeds maximum allowed size")
        return candidate

    @staticmethod
    def _list_allowed_files() -> list[str]:
        if not ALLOWED_ROOT.is_dir():
            return []
        return sorted(
            path.name
            for path in ALLOWED_ROOT.iterdir()
            if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES
        )

    def load_file(self, change: dict[str, Any]) -> None:
        try:
            path = self._canonical_path(change["new"])
            data = path.read_bytes()
            if b"\x00" in data:
                raise ValueError("binary input rejected")
            self.source_input.value = data.decode("utf-8", errors="strict")
            self.current_file_path = path
        except Exception as exc:
            self.current_file_path = None
            with self.output_area:
                print(f"ERROR: {str(exc)}")

    def save_file(self, _: object) -> None:
        if not self.current_file_path:
            return
        try:
            path = self._canonical_path(self.current_file_path.name)
            data = self.source_input.value.encode("utf-8", errors="strict")
            if len(data) > MAX_FILE_BYTES or b"\x00" in data:
                raise ValueError("output exceeds text/file limits")
            path.write_bytes(data)
            with self.output_area:
                print(f"Saved to {path}")
        except Exception as exc:
            with self.output_area:
                print(f"ERROR: {str(exc)}")

    def execute(self, _: object) -> None:
        with self.output_area:
            clear_output()
            try:
                ln = self.ln_input.value if self.ln_input.value > 0 else None
                result = self.engine.insert(
                    self.source_input.value,
                    anchor_text=self.anchor_input.value if not ln else None,
                    new_code=self.insert_input.value,
                    position=self.pos_toggle.value,
                    line_number=ln,
                )
                diff = difflib.HtmlDiff().make_table(
                    self.source_input.value.splitlines(), result.splitlines(), context=True
                )
                self.diff_area.value = f"<div style='overflow-x:auto;'>{diff}</div>"
                self.source_input.value = result
                print("--- TRANSFORMATION SUCCESSFUL ---")
            except Exception as e:
                print(f"ERROR: {str(e)}")

    def render(self) -> None:
        display(
            widgets.VBox(
                [
                    widgets.HTML("<h1>Text Scalpel Pro v3.1</h1>"),
                    self.file_selector,
                    self.source_input,
                    self.anchor_input,
                    self.ln_input,
                    self.insert_input,
                    self.pos_toggle,
                    widgets.HBox([self.run_btn, self.save_btn]),
                    self.diff_area,
                    self.output_area,
                ]
            )
        )
