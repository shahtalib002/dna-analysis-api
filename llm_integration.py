# llm_integration.py

import google.generativeai as genai
import config # To get the API key from config.py
import os

# --- Configuration & Initialization ---

# Flag to check if configuration succeeded
llm_configured = False
llm_client = None
# Define model name here for easy change
# Let's try gemini-1.5-flash-latest
MODEL_NAME = "gemini-1.5-flash-latest"


try:
    # Get the API key loaded by config.py
    api_key = config.GOOGLE_API_KEY
    if api_key:
        genai.configure(api_key=api_key)
        # *** Use the updated model name here ***
        llm_client = genai.GenerativeModel(MODEL_NAME)
        llm_configured = True
        # Updated print message to reflect the model name change
        print(f"Google Generative AI configured successfully with '{MODEL_NAME}' model.")
    else:
        # This message is important for debugging if the key isn't loading
        print("Warning: GOOGLE_API_KEY not found in environment variables or .env file. "
              "The /ask-me-anything endpoint will be disabled.")

except Exception as e:
    print(f"Error configuring Google Generative AI: {e}. LLM features may be disabled.")
    # Handle specific exceptions if needed, e.g., authentication errors


# --- System Prompt / Context ---
# This tells the LLM how to behave and what the API does.
API_CONTEXT = """
You are a helpful assistant embedded within a FastAPI server designed for forensic researchers studying ancient DNA.
Your purpose is to answer questions about the capabilities and usage of this specific API server based ONLY on the information provided below. Do not invent features.

API Summary:
1.  GET / : Root endpoint. Returns a simple welcome message.
2.  POST /upload-csv/ : Uploads a CSV file with ancient remains data (columns: id, region, age, seed). Cleans data, stores it, and clears any cached DNA sequences. Overwrites previous data.
3.  GET /generate-sequence/?id={sample_id} : Gets the DNA sequence for a sample ID. Uses cached data if available, otherwise generates it (can be slow first time). Requires CSV upload first. Fails if ID not found or data invalid.
4.  GET /compare-sequences/?id1={sample_id1}&id2={sample_id2} : Compares the DNA sequences of two IDs using 4-character motif similarity (Jaccard Index). Returns score (0.0-1.0). Requires CSV upload. Can be slow first time for uncached IDs.
5.  POST /ask-me-anything/ : (This endpoint). Ask natural language questions about this API.

Be concise and stick to describing the API functionality as listed above.
"""

# --- LLM Interaction Function ---

def ask_llm(query: str) -> str:
    """
    Sends a query to the configured Gemini model with API context.

    Args:
        query: The user's natural language question.

    Returns:
        The LLM's text response, or an informative error message.
    """
    if not llm_configured or not llm_client:
        # Return a clear message if setup failed
        return "LLM integration is not configured. Please ensure the GOOGLE_API_KEY is set correctly in the .env file and the server was restarted."

    try:
        # Construct the full prompt including context and the user's question
        full_prompt = f"{API_CONTEXT}\n\nUser Question: {query}\n\nAssistant Response:"

        # Generate content using the pre-initialized client
        print(f"Sending query to LLM ('{MODEL_NAME}'): '{query}'")
        response = llm_client.generate_content(full_prompt)

        # --- Response Handling ---
        # Check for blocking first
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason
            print(f"LLM response blocked due to: {block_reason}")
            return f"Sorry, the response was blocked due to safety settings ({block_reason}). Please rephrase your question."

        # Check if response has parts and text
        if hasattr(response, 'text'):
             response_text = response.text
             print("Received response from LLM.")
             return response_text
        elif response.parts:
            response_text = "".join(part.text for part in response.parts)
            print("Received response from LLM (joined parts).")
            return response_text
        else:
            print("LLM returned an empty response (no parts/text).")
            return "Sorry, I received an empty response from the LLM for that query."

    except Exception as e:
        # Catch potential API call errors, network issues, etc.
        print(f"Error interacting with LLM API: {e}")
        # Provide a user-friendly error message including the exception text
        return f"Sorry, an error occurred while communicating with the LLM: {e}"