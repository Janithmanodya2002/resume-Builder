import os
import uuid
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from config import TEMPLATES

def generate_pdf(user_data: dict) -> str | None:
    """
    Generates a PDF resume from user data and a template.

    Args:
        user_data: A dictionary containing all the user's information.

    Returns:
        The file path of the generated PDF, or None if an error occurs.
    """
    try:
        # 1. Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader('.'))

        # 2. Get the correct template path from the config
        template_name = user_data.get("template", "modern") # Default to modern
        template_path = TEMPLATES.get(template_name)
        if not template_path:
            raise FileNotFoundError(f"Template '{template_name}' not found in config.")

        template = env.get_template(template_path)

        # 3. Render the HTML template with user data
        # Ensure photo_path is a file URI for local access, which is required by WeasyPrint
        if 'photo_path' in user_data and os.path.exists(user_data['photo_path']):
            user_data['photo_path'] = f"file://{os.path.abspath(user_data['photo_path'])}"

        html_out = template.render(user_data)

        # 4. Create a temporary output file path
        output_dir = "/tmp/resume_bot/pdfs"
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"resume_{uuid.uuid4()}.pdf")

        # 5. Call WeasyPrint to convert HTML to PDF
        # The base_url is crucial for resolving relative paths for images, CSS etc.
        HTML(string=html_out, base_url='.').write_pdf(pdf_path)

        return pdf_path

    except Exception as e:
        print(f"Error generating PDF: {e}") # Using print for now, logging is better
        return None
