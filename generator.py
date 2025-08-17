import os
import uuid
import logging
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
        # Get the absolute path of the directory containing this script (resume_bot/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # The templates directory is a subdirectory of the script's directory
        templates_dir = os.path.join(script_dir, 'templates')

        # 1. Set up Jinja2 environment with a reliable path to the templates directory
        env = Environment(loader=FileSystemLoader(templates_dir))

        # 2. Get the correct template path from the config
        template_name = user_data.get("template", "modern") # Default to modern
        template_path = TEMPLATES.get(template_name)
        if not template_path:
            raise FileNotFoundError(f"Template '{template_name}' not found in config.")

        # The loader's search path is now the templates dir, so we just need the filename
        template_filename = os.path.basename(template_path)
        template = env.get_template(template_filename)

        # 3. Render the HTML template with user data
        # Ensure photo_path is a file URI for local access, which is required by WeasyPrint
        if 'photo_path' in user_data and user_data.get('photo_path') and os.path.exists(user_data['photo_path']):
            user_data['photo_path'] = f"file://{os.path.abspath(user_data['photo_path'])}"

        html_out = template.render(user_data)

        # 4. Create a temporary output file path
        output_dir = "/tmp/resume_bot/pdfs"
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"resume_{uuid.uuid4()}.pdf")

        # 5. Call WeasyPrint to convert HTML to PDF
        # The base_url should be the templates directory to resolve any relative asset paths
        HTML(string=html_out, base_url=templates_dir).write_pdf(pdf_path)

        return pdf_path

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return None
