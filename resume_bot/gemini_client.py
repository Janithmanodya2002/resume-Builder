import google.generativeai as genai
from config import GEMINI_API_KEY
import logging

# Configure the Gemini API client
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    logging.error(f"Failed to configure Gemini: {e}")
    model = None

def enhance_summary(text: str) -> str | None:
    """
    Rewrites a user's summary into a more professional version using Gemini.
    """
    if not model:
        logging.warning("Gemini model not available. Skipping enhancement.")
        return None

    prompt = f"Rewrite the following into a professional and impactful resume summary (2-4 sentences max): '{text}'"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API call failed for summary enhancement: {e}")
        return None


def enhance_experience(duties: list[str]) -> list[str] | None:
    """
    Rewrites job duties into strong, action-oriented bullet points.
    """
    if not model:
        logging.warning("Gemini model not available. Skipping enhancement.")
        return None

    # Create a single string with bullet points for the prompt
    duties_str = "\n- ".join(duties)
    prompt = f"Rephrase these job duties into strong, action-oriented bullet points for a resume. Return only the bullet points:\n- {duties_str}"

    try:
        response = model.generate_content(prompt)
        # Process response to return a list of strings, removing empty lines and dashes
        enhanced_duties = [line.strip().lstrip('- ').capitalize() for line in response.text.strip().split('\n') if line.strip()]
        return enhanced_duties
    except Exception as e:
        logging.error(f"Gemini API call failed for experience enhancement: {e}")
        return None
