# gemini_app.py - Streamlit frontend for Gemini-powered minutes generation
import os
import streamlit as st
from dotenv import load_dotenv, find_dotenv

# Import the new GeminiClient and file processing functions
from gemini_node import GeminiClient, extract_text_from_pdf, extract_text_from_docx

# --- Page Configuration ---
st.set_page_config(
    page_title="Gemini Minutes Generator",
    page_icon="✨",
    layout="centered"
)

# Load environment variables from .env file (e.g., GOOGLE_API_KEY)
load_dotenv(find_dotenv())

# --- Caching and Client Initialization ---
@st.cache_resource
def get_gemini_client():
    """Cached function to initialize the GeminiClient."""
    return GeminiClient()

# --- Helper Functions ---
def format_minutes_as_markdown(minutes: dict) -> str:
    """Converts the structured minutes dictionary into a markdown string."""
    sections = [
        ("## ✨ Summary", minutes.get("summary", "")),
        ("## 👥 Participants", "\n".join(f"- {p}" for p in minutes.get("participants", []))),
        ("## 🗣️ Discussion Points", "\n".join(f"- {t}" for t in minutes.get("discussion_points", []))),
        ("## ✅ Outcomes or Decisions", "\n".join(f"- {d}" for d in minutes.get("outcomes_or_decisions", []))),
        ("## 🚀 Next Steps", "\n".join(f"- {s}" for s in minutes.get("next_steps", [])))
    ]
    # Join sections into a single string, skipping any that are empty.
    return "\n\n".join(f"{header}\n{content}" for header, content in sections if content)

# --- Main Application UI ---
def main():
    st.title("✨ Gemini Minutes Generator")
    st.caption("Powered by Google's Gemini API")

    # --- 1. API Key Handling & Connection Test ---
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("🔴 Missing GOOGLE_API_KEY. Please create a .env file with your key.")
        st.info("Example .env file:\n\n`GOOGLE_API_KEY=\"your_api_key_here\"`")
        st.stop()

    client = get_gemini_client()
    ok, msg = client.test_connection()
    if not ok:
        st.error(f"🔴 Gemini client failed to initialize: {msg}")
        st.stop()

    # --- 2. File Input & Transcript Handling ---
    st.subheader("1. Provide Your Transcript")
    uploaded_file = st.file_uploader(
        "Upload a transcript file (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"]
    )
    transcript_text = st.text_area(
        "Or paste the transcript text here:",
        height=200,
        placeholder="Your meeting transcript goes here..."
    )

    final_transcript = ""
    if uploaded_file:
        with st.spinner(f"Reading {uploaded_file.name}..."):
            if uploaded_file.type == "text/plain":
                final_transcript = uploaded_file.read().decode("utf-8", errors="ignore")
            elif uploaded_file.type == "application/pdf":
                final_transcript = extract_text_from_pdf(uploaded_file)
            elif "wordprocessingml" in uploaded_file.type:
                final_transcript = extract_text_from_docx(uploaded_file)

        if final_transcript:
            st.success(f"✅ Loaded {len(final_transcript):,} characters from {uploaded_file.name}")
        else:
            st.warning("⚠️ Could not extract text from the uploaded file.")
    elif transcript_text.strip():
        final_transcript = transcript_text.strip()

    # --- 3. Generation Button & Logic ---
    st.subheader("2. Generate the Minutes")
    if st.button("🚀 Generate Minutes", type="primary", disabled=not final_transcript, use_container_width=True):
        with st.spinner("🧠 Gemini is thinking... This may take a moment."):
            minutes = client.generate_meeting_minutes(final_transcript)

        if "Could not automatically generate minutes" in minutes.get("summary", ""):
            st.error(f"🔴 Failed to generate minutes. Error: {client.last_error or 'The AI could not process this transcript.'}")
        else:
            st.success("✅ Minutes generated successfully!")
            # Save to session state to persist results across reruns
            st.session_state.minutes = minutes

    # --- 4. Display Results ---
    if 'minutes' in st.session_state:
        st.subheader("3. Review Your Results")
        minutes = st.session_state.minutes
        tab1, tab2 = st.tabs(["📊 Structured View", "📄 Markdown & Export"])

        with tab1:
            # Use expanders for a clean, organized layout
            with st.expander("✨ **Summary**", expanded=True):
                st.write(minutes.get("summary", "Not available."))

            with st.expander("👥 **Participants**"):
                if participants := minutes.get("participants"):
                    st.markdown("\n".join(f"- {p}" for p in participants))
                else:
                    st.caption("No participants were identified.")

            with st.expander("🗣️ **Discussion Points**"):
                if points := minutes.get("discussion_points"):
                    st.markdown("\n".join(f"- {p}" for p in points))
                else:
                    st.caption("No key topics were identified.")

            with st.expander("✅ **Outcomes or Decisions**"):
                if decisions := minutes.get("outcomes_or_decisions"):
                    st.markdown("\n".join(f"- {d}" for d in decisions))
                else:
                    st.caption("No outcomes or decisions were identified.")

            with st.expander("🚀 **Next Steps**"):
                if steps := minutes.get("next_steps"):
                    st.markdown("\n".join(f"- {s}" for s in steps))
                else:
                    st.caption("No next steps were identified.")

        with tab2:
            markdown_content = format_minutes_as_markdown(minutes)
            st.code(markdown_content, language='markdown')
            st.download_button(
                "⬇️ Download as Markdown (.md)",
                markdown_content,
                "gemini_minutes.md",
                "text/markdown",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
