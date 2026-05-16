import unicodedata
from typing import Literal

MAX_INSERTION_BYTES = 100_000
MAX_RESULT_BYTES = 1_000_000
MAX_SOURCE_BYTES = 1_000_000


class ScalpelEngine:
    @staticmethod
    def _normalize_text(value: object, name: str) -> str:
        if isinstance(value, bytes):
            raise ValueError(f"{name} must be UTF-8 text, not bytes.")
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string.")
        if "\x00" in value:
            raise ValueError(f"{name} contains binary NUL input.")
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{name} must be valid UTF-8 text.") from exc
        return unicodedata.normalize("NFC", value)

    @staticmethod
    def insert(
        source_code: object,
        anchor_text: object | None = None,
        new_code: object = "",
        position: Literal["before", "after"] | str = "after",
        line_number: object | None = None,
    ) -> str:
        """
        Performs surgical code insertion with indentation preservation.
        Supports both anchor-text and line-number based targeting.
        """
        source_code = ScalpelEngine._normalize_text(source_code, "source_code")
        new_code = ScalpelEngine._normalize_text(new_code, "new_code")
        if anchor_text is not None:
            anchor_text = ScalpelEngine._normalize_text(anchor_text, "anchor_text")

        if len(source_code.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ValueError("source_code exceeds maximum allowed size.")
        if len(new_code.encode("utf-8")) > MAX_INSERTION_BYTES:
            raise ValueError("new_code exceeds maximum insertion size.")
        if new_code and new_code in source_code:
            raise ValueError("new_code is already present; duplicate insertion rejected.")
        if source_code and source_code in new_code:
            raise ValueError("new_code recursively contains the source buffer.")

        lines = source_code.splitlines()
        target_index = -1
        indent = ""

        if position not in {"before", "after"}:
            raise ValueError("position must be either 'before' or 'after'.")

        # 1. Determine target index and indentation
        if line_number is not None:
            if not isinstance(line_number, int):
                raise ValueError("line_number must be an integer.")
            if line_number < 1:
                raise ValueError("line_number must be 1 or greater.")
            # Line number is 1-based index. Empty source buffers are valid
            # insertion targets and use column-zero indentation.
            if lines:
                if line_number > len(lines):
                    raise ValueError("line_number exceeds source buffer line count.")
                target_index = line_number - 1
                target_line = lines[target_index]
                current_indent = target_line[: len(target_line) - len(target_line.lstrip())]

                # Auto-indent logic: increase indent if inserting after a colon
                if position == "after" and target_line.rstrip().endswith(":"):
                    indent = current_indent + "    "
                else:
                    indent = current_indent
            else:
                if line_number != 1:
                    raise ValueError("empty source buffers only accept line_number=1.")
                target_index = -1 if position == "after" else 0
        elif anchor_text:
            for i, line in enumerate(lines):
                if anchor_text in line:
                    target_index = i
                    indent = line[: len(line) - len(line.lstrip())]
                    break
            if target_index == -1:
                raise ValueError(f"Anchor text '{anchor_text}' not found.")
        else:
            raise ValueError("Either anchor_text or line_number must be provided.")

        # 2. Prepare the indented payload
        indented_lines = [
            (f"{indent}{line}" if line.strip() else line) for line in new_code.splitlines()
        ]
        indented_block = "\n".join(indented_lines)

        # 3. Perform insertion
        if position == "after":
            lines.insert(target_index + 1, indented_block)
        else:
            lines.insert(target_index, indented_block)

        updated_code = "\n".join(lines)
        if len(updated_code.encode("utf-8")) > MAX_RESULT_BYTES:
            raise ValueError("resulting source exceeds maximum allowed size.")

        # 4. Syntax Validation Gate
        try:
            compile(updated_code, "<string>", "exec")
        except SyntaxError as e:
            raise SyntaxError(f"Surgical insertion failed syntax validation: {e}") from None

        return updated_code
