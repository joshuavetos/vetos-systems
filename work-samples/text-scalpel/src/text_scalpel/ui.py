import ipywidgets as widgets
from IPython.display import display, clear_output
import logging
from .core import ScalpelEngine

logger = logging.getLogger("TextScalpel")

class ScalpelDashboard:
    def __init__(self):
        self.engine = ScalpelEngine()
        self.source_input = widgets.Textarea(
            value='def main():\n    # START_HERE\n    return True',
            description='Source:',
            layout={'height': '150px', 'width': '95%'}
        )
        self.anchor_input = widgets.Text(value='# START_HERE', description='Anchor:')
        self.insert_input = widgets.Textarea(
            value='print("Injected!")',
            description='Payload:',
            layout={'height': '80px', 'width': '95%'}
        )
        self.pos_toggle = widgets.Dropdown(
            options=['after', 'before'],
            value='after',
            description='Position:'
        )
        self.run_btn = widgets.Button(
            description='Run Transformation',
            button_style='info',
            layout={'width': '95%'}
        )
        self.output_area = widgets.Output()
        self.run_btn.on_click(self.execute)

    def execute(self, _):
        with self.output_area:
            clear_output()
            try:
                result = self.engine.insert(
                    self.source_input.value,
                    self.anchor_input.value,
                    self.insert_input.value,
                    self.pos_toggle.value
                )
                print("--- TRANSFORMATION SUCCESSFUL ---\n")
                print(result)
                logger.info("Transformation applied successfully.")
            except Exception as e:
                print(f"ERROR: {str(e)}")
                logger.error(f"Transformation failed: {e}")

    def render(self):
        display(widgets.VBox([
            widgets.HTML("<h1>Text Scalpel Pro v3.0</h1><p>Enterprise Code Injection Engine</p>"),
            self.source_input, self.anchor_input, self.insert_input, self.pos_toggle, self.run_btn, self.output_area
        ]))
