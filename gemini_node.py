# gemini_node.py - Google Gemini Integration
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Tuple, Optional
from PyPDF2 import PdfReader
import docx

class GeminiClient:
    """
    A client for interacting with the Google Gemini API.
    """
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the Gemini client.
        - api_key: Your Google API key. If not provided, it's read from the GOOGLE_API_KEY environment variable.
        """
        self.model: Optional[genai.GenerativeModel] = None
        self.last_error: Optional[str] = None
        # Configure the client immediately if a key is available.
        try:
            # The key is read from the environment variable if not passed directly.
            key = api_key or os.getenv("GOOGLE_API_KEY")
            if not key:
                self.last_error = "GOOGLE_API_KEY is missing or not provided."
                return

            genai.configure(api_key=key)
            # Set up the model with generation config for JSON output
            self.model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
            self.last_error = None
        except Exception as e:
            self.model = None
            self.last_error = f"Failed to configure Gemini client: {e}"

    def test_connection(self) -> Tuple[bool, str]:
        """
        Tests if the client is configured correctly.
        Returns a tuple (success_boolean, message_string).
        """
        if self.model:
            return True, "Gemini client configured successfully."
        return False, self.last_error or "Client could not be initialized."

    def generate_meeting_minutes(self, transcript: str) -> Dict[str, Any]:
        """
        Generates meeting minutes from a transcript using the Gemini model.
        - transcript: The full text of the meeting conversation.
        Returns a dictionary containing the structured minutes.
        """
        if not self.model:
            return self._create_fallback_minutes()

        system_prompt = self._get_system_prompt()
        full_prompt = f"{system_prompt}\n\nAnalyze this meeting transcript and generate the JSON output:\n\n{transcript}"

        try:
            response = self.model.generate_content(full_prompt)
            # The Gemini API returns the JSON string directly in the text attribute.
            minutes = json.loads(response.text)
            return self._clean_minutes(minutes)
        except Exception as e:
            self.last_error = f"API call failed: {e}"
            # Check if the error is due to a content safety block.
            try:
                # This helps debug if the API blocked the response for safety reasons.
                _ = response.candidates[0].finish_reason
                self.last_error += f" | Finish Reason: {response.candidates[0].finish_reason.name}"
                self.last_error += f" | Safety Ratings: {response.candidates[0].safety_ratings}"
            except Exception:
                pass # Ignore if we can't get more details.
            return self._create_fallback_minutes()

    def _get_system_prompt(self) -> str:
        """Returns the system prompt with instructions for the AI model."""
        return """You are an intelligent assistant that analyzes conversations and generates a structured summary in JSON format. Your goal is to extract the most important information, focusing on clarity and factual accuracy based on the provided transcript.

Required JSON structure:
{
  "summary": "A concise, 2-4 sentence summary of the entire conversation's purpose and flow.",
  "participants": ["Name 1 (Role, if specified)", "Name 2 (Role, if specified)"],
  "discussion_points": [
    "A key topic or question that was discussed.",
    "Another significant point of discussion."
  ],
  "outcomes_or_decisions": [
    "Any final decisions, conclusions, or results from the conversation."
  ],
  "next_steps": [
    "Any explicit mentions of future actions or follow-ups(Assignee or Assigned team)."
  ]
}

Rules:
- ALWAYS output only a valid JSON object.
- If a section has no relevant information (e.g., no decisions were made), use an empty list [].
- Extract participant names and their roles if mentioned (e.g., "Cate (Material Science)").
- Keep summaries and points concise and directly from the transcript.
- Do not invent or infer information not present in the text. Focus on what was actually said."""

    def _clean_minutes(self, minutes: Dict) -> Dict[str, Any]:
        """Cleans and standardizes the dictionary returned by the AI."""
        return {
            "summary": str(minutes.get("summary", "")).strip() or "No summary available.",
            "participants": [str(p).strip() for p in minutes.get("participants", []) if str(p).strip()],
            "discussion_points": [str(t).strip() for t in minutes.get("discussion_points", []) if str(t).strip()],
            "outcomes_or_decisions": [str(d).strip() for d in minutes.get("outcomes_or_decisions", []) if str(d).strip()],
            "next_steps": [str(s).strip() for s in minutes.get("next_steps", []) if str(s).strip()]
        }

    def _create_fallback_minutes(self) -> Dict[str, Any]:
        """Returns a default dictionary structure on failure."""
        return {
            "summary": "Could not automatically generate minutes. Manual review required.",
            "participants": [], "discussion_points": [], "outcomes_or_decisions": [], "next_steps": []
        }

# --- File Processing Functions (Remain Unchanged) ---

def extract_text_from_pdf(file) -> str:
    """Extracts text from an uploaded PDF file."""
    try:
        reader = PdfReader(file)
        return "\n\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    except Exception:
        return ""

def extract_text_from_docx(file) -> str:
    """Extracts text from an uploaded DOCX file."""
    try:
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""

