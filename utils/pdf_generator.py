from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class PDFGenerator:
    def __init__(self, config):
        self.config = config
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        self.styles.add(ParagraphStyle(name='Left', alignment=0))
        self.styles.add(ParagraphStyle(name='Right', alignment=2))
    
    def generate(self, invoice_data, preview=False):
        # Move PDF generation logic here
        pass 