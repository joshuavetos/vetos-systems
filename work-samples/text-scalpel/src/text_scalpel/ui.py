import ipywidgets as widgets
from IPython.display import display, clear_output
import os
import difflib
from .core import ScalpelEngine

class ScalpelDashboard:
    def __init__(self):
        self.engine = ScalpelEngine()
        self.current_file_path = None
        
        # 1. File Selector (Scans /content for existing repo files)
        files = [f for f in os.listdir('/content') if os.path.isfile(os.path.join('/content', f))]
        self.file_selector = widgets.Select(
            options=files,
            description='Files:',
            layout={'height': '100px', 'width': '95%'}
        )
        self.file_selector.observe(self.load_file, names='value')

        # 2. Inputs
        self.source_input = widgets.Textarea(description='Source:', layout={'height': '200px', 'width': '95%'})
        self.anchor_input = widgets.Text(value='# ANCHOR', description='Anchor:')
        self.ln_input = widgets.IntText(value=0, description='Line (0=off):')
        self.insert_input = widgets.Textarea(value='print("Injected!")', description='Payload:', layout={'height': '80px', 'width': '95%'})
        self.pos_toggle = widgets.Dropdown(options=['after', 'before'], value='after', description='Position:')

        # 3. Actions
        self.run_btn = widgets.Button(description='Run Transformation', button_style='info', layout={'width': '47%'})
        self.save_btn = widgets.Button(description='Save to File', button_style='success', layout={'width': '47%'})
        self.run_btn.on_click(self.execute)
        self.save_btn.on_click(self.save_file)
        
        self.diff_area = widgets.HTML()
        self.output_area = widgets.Output()

    def load_file(self, change):
        path = os.path.join('/content', change['new'])
        self.current_file_path = path
        with open(path, 'r') as f:
            self.source_input.value = f.read()

    def save_file(self, _):
        if not self.current_file_path:
            return
        with open(self.current_file_path, 'w') as f:
            f.write(self.source_input.value)
        with self.output_area:
            print(f"Saved to {self.current_file_path}")

    def execute(self, _):
        with self.output_area:
            clear_output()
            try:
                ln = self.ln_input.value if self.ln_input.value > 0 else None
                result = self.engine.insert(
                    self.source_input.value,
                    anchor_text=self.anchor_input.value if not ln else None,
                    new_code=self.insert_input.value,
                    position=self.pos_toggle.value,
                    line_number=ln
                )
                # Generate visual diff
                diff = difflib.HtmlDiff().make_table(self.source_input.value.splitlines(), result.splitlines(), context=True)
                self.diff_area.value = f"<div style='overflow-x:auto;'>{diff}</div>"
                self.source_input.value = result
                print("--- TRANSFORMATION SUCCESSFUL ---")
            except Exception as e:
                print(f"ERROR: {str(e)}")

    def render(self):
        display(widgets.VBox([
            widgets.HTML("<h1>Text Scalpel Pro v3.1</h1>"),
            self.file_selector, self.source_input, self.anchor_input, self.ln_input, 
            self.insert_input, self.pos_toggle, widgets.HBox([self.run_btn, self.save_btn]), 
            self.diff_area, self.output_area
        ]))
