import streamlit as st
import fitz 
from groq import Groq
import json
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Legal Prompt Gen", page_icon="", layout="wide")


load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("API Key Missing: Please add your GROQ_API_KEY to the .env file.")
    st.stop()

client = Groq(api_key=api_key)

#logic
def extract_pdf_text(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        return "".join([page.get_text() for page in doc])
    except Exception:
        return ""

def generate_custom_prompt(extracted_text, user_input):
    text_sample = extracted_text[:8000] if extracted_text else ""
    

    target_material = f"Document Excerpt:\n{text_sample}" if text_sample else "No document provided. Rely entirely on the user context below."
    user_context_instruction = f'User Context: "{user_input}"' if user_input.strip() else ""

    meta_prompt = f"""
    Analyze the following Italian legal scenario. 
    
    {user_context_instruction}
    {target_material}
    
    1. Identify the specific document type (if a document is provided) OR the general legal domain (e.g., Diritto del Lavoro, Diritto Civile).
    2. Identify the 3 most critical legal risks or questions to investigate based on the context provided.
    
    Output ONLY valid JSON:
    {{"document_type": "type_or_domain", "key_questions": ["q1", "q2", "q3"]}}
    """
    
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b", 
        messages=[{"role": "user", "content": meta_prompt}],
        temperature=0.1
    )
    
    raw_output = completion.choices[0].message.content
    cleaned_output = raw_output.strip().strip("```json").strip("```")
    
    try:
        analysis = json.loads(cleaned_output)
    except json.JSONDecodeError:
        st.error("Error: Failed to parse structural data from the model. Please try again.")
        return None
    
   #final prompt
    user_query_section = f"**User Context:** {user_input}\n" if user_input.strip() else ""
    document_section = f"**Case File Text:**\n{extracted_text}\n" if extracted_text else ""
    intro_line = "I am providing you with a case file document" if extracted_text else "I have a legal scenario"

    final_prompt = f"""Act as an expert Italian Legal Advisor and Strategist. 

{intro_line} identified as related to: **{analysis.get('document_type', 'Materia Legale')}**.

{user_query_section}
CRITICAL INSTRUCTION FOR GEMINI: You MUST use your Google Search capabilities to query official Italian legal databases (such as Normattiva.it, Brocardi.it, Altalex, or Corte di Cassazione) to verify the most up-to-date legislation and recent case law before generating your response. Do not rely solely on your training data.

Please analyze the provided context and generate a structured legal report. You MUST conduct web searches to answer these 3 key legal questions derived from the situation:
1. {analysis['key_questions'][0]}
2. {analysis['key_questions'][1]}
3. {analysis['key_questions'][2]}

Format your response exactly with these sections (in Italian):
1. **Analisi dei Fatti (Case Summary)**
2. **Risultati della Ricerca Normativa (Statutory/Case Law Search Results)**
3. **Argomentazioni Legali (Legal Arguments)**
4. **Azioni Consigliate (Actionable Steps)**

{document_section}
"""
    return final_prompt

#UI
st.title("Italian Legal Prompt Generator")
st.markdown("Create highly structured, search-optimized prompts for Gemini using context, documents, or both.")
st.divider()

# Input 
st.subheader("1. Input Scenario")
user_context = st.text_area(
    "Describe your legal issue or ask a question:", 
    placeholder="E.g., Can I terminate my commercial lease early without paying a penalty?",
    height=100
)

uploaded_file = st.file_uploader("Upload a supporting document (.pdf) [Optional]:", type=["pdf"])

#Execution
st.write("") 
if st.button("Generate Prompt", type="primary", use_container_width=True):
    
    if not uploaded_file and not user_context.strip():
        st.warning("Please provide either a text description or upload a PDF document to generate a prompt.")
    else:
        with st.spinner("Analyzing context and building prompt..."):
            raw_text = ""
            
            if uploaded_file:
                raw_text = extract_pdf_text(uploaded_file)
                if not raw_text.strip():
                    st.info("Note: No text could be extracted from the PDF (it may be an image). Falling back to text context.")
            
            final_custom_prompt = generate_custom_prompt(raw_text, user_context)
            
            if final_custom_prompt:
                st.divider()
                st.subheader("2. Generated Output")
                
                if raw_text.strip():
                    #Spilt view
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Copilot Prompt** (Paste into Gemini)")
                        st.code(final_custom_prompt, language="markdown")
                    with col2:
                        st.markdown("**Extracted PDF Text** (For reference)")
                        st.code(raw_text, language="text")
                else:
                    #single view output
                    st.markdown("**Copilot Prompt** (Paste into Gemini)")
                    st.code(final_custom_prompt, language="markdown")