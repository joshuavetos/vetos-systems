class ScalpelEngine:
    @staticmethod
    def insert(source_code, anchor_text=None, new_code="", position='after', line_number=None):
        """
        Performs surgical code insertion with indentation preservation.
        Supports both anchor-text and line-number based targeting.
        """
        lines = source_code.splitlines()
        target_index = -1
        indent = ""

        if position not in {"before", "after"}:
            raise ValueError("position must be either 'before' or 'after'.")

        # 1. Determine target index and indentation
        if line_number is not None:
            # Line number is 1-based index. Empty source buffers are valid
            # insertion targets and use column-zero indentation.
            if lines:
                target_index = max(0, min(line_number - 1, len(lines) - 1))
                target_line = lines[target_index]
                current_indent = target_line[:len(target_line) - len(target_line.lstrip())]

                # Auto-indent logic: increase indent if inserting after a colon
                if position == 'after' and target_line.rstrip().endswith(':'):
                    indent = current_indent + "    "
                else:
                    indent = current_indent
            else:
                target_index = -1 if position == 'after' else 0
        elif anchor_text:
            for i, line in enumerate(lines):
                if anchor_text in line:
                    target_index = i
                    indent = line[:len(line) - len(line.lstrip())]
                    break
            if target_index == -1:
                raise ValueError(f"Anchor text '{anchor_text}' not found.")
        else:
            raise ValueError("Either anchor_text or line_number must be provided.")

        # 2. Prepare the indented payload
        indented_lines = [(f"{indent}{line}" if line.strip() else line) for line in new_code.splitlines()]
        indented_block = "\n".join(indented_lines)

        # 3. Perform insertion
        if position == 'after':
            lines.insert(target_index + 1, indented_block)
        else:
            lines.insert(target_index, indented_block)
        
        updated_code = "\n".join(lines)

        # 4. Syntax Validation Gate
        try:
            compile(updated_code, '<string>', 'exec')
        except SyntaxError as e:
            raise SyntaxError(f"Surgical insertion failed syntax validation: {e}") from None
            
        return updated_code
