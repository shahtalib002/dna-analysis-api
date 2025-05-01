# main.py

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from pydantic import BaseModel # Import BaseModel for request body validation
from typing import Dict, Any

# Import your custom modules
import data_handler
import sequence_utils
import llm_integration # Import the LLM module
# import config # config is used within llm_integration, no need to import here unless needed directly

# --- Constants ---
DATA_DIR = "data"

# --- Request Body Model ---
# Defines the structure expected for the /ask-me-anything request
class QueryRequest(BaseModel):
    query: str

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Ancient DNA Analysis API",
    description="API for uploading ancient remains data, generating DNA sequences, "
                "comparing sequences, and asking questions about the API.",
    version="0.1.0",
    # You can add contact info, license info etc. here if desired
    # contact={"name": "Your Name", "email": "your.email@example.com"},
)

# --- In-Memory Storage ---
# Cache for generated sequences {id_string: sequence_string}
sequence_cache: Dict[str, str] = {}

# --- Helper Function ---

async def _get_sequence_by_id(id: str) -> str:
    """
    Internal helper function to get a sequence by ID.
    Handles data loading checks, cache, record validation, generation, and errors.
    Raises HTTPException on failure.
    """
    # 1. Check if data is loaded
    if not data_handler.is_data_loaded():
        raise HTTPException(status_code=409, detail="Conflict: No data loaded. Please upload a CSV file first via /upload-csv/.")

    # 2. Check cache first
    if id in sequence_cache:
        print(f"Cache hit for ID: {id}")
        return sequence_cache[id]

    print(f"Cache miss for ID: {id}. Attempting to retrieve/generate sequence.")
    # ... (rest of the helper function remains the same as in Step 7) ...
    # 3. Retrieve record
    record = data_handler.get_record_by_id(id)

    # 4. Handle ID not found
    if record is None:
        raise HTTPException(status_code=404, detail=f"Not Found: Sample ID '{id}' not found in the loaded data.")

    # 5. Check if record is valid for generation
    if not record.get('is_valid_for_generation', False):
        reason = "Missing or invalid original age, or missing seed."
        raise HTTPException(status_code=400, detail=f"Bad Request: Cannot generate sequence for ID '{id}'. Reason: {reason}")

    # 6. Prepare arguments
    try:
        id_int = int(record['id_int'])
        region_str = str(record['region'])
        age_int = int(record['age'])
        seed_str = str(record['seed'])
    except KeyError as e:
         raise HTTPException(status_code=500, detail=f"Internal Server Error: Missing expected data field {e} for ID '{id}'.")
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Internal Server Error: Could not prepare arguments for ID '{id}': {e}")

    # 7. Call generation function
    try:
        print(f"Generating sequence for ID: {id} (int: {id_int}, region: {region_str}, age: {age_int})")
        generated_sequence = sequence_utils.generate_dna_sequence(
            id=id_int,
            region=region_str,
            age=age_int,
            dna_seed=seed_str
        )
    except Exception as e:
        print(f"Error during sequence generation call for ID {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed during sequence generation for ID '{id}'.")

    # 8. Handle "x" return
    if generated_sequence == "x":
        raise HTTPException(status_code=400, detail=f"Bad Request: Cannot generate sequence for ID '{id}'. The provided seed value does not contain any recognizable DNA motifs.")

    # 9. Cache result
    sequence_cache[id] = generated_sequence
    print(f"Sequence generated and cached for ID: {id}")

    # 10. Return result
    return generated_sequence


# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    """ Root endpoint providing a welcome message. """
    return {"message": "Welcome to the Ancient DNA Analysis API!"}

@app.post("/upload-csv/", tags=["Data Handling"])
async def upload_csv_endpoint(file: UploadFile = File(..., description="CSV file containing ancient remains data (id, region, age, seed).")):
    """ Uploads, cleans, and stores CSV data. Overwrites previous data. """
    uploaded_file_path = os.path.join(DATA_DIR, "uploaded_data.csv")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not create data directory: {e}")
    try:
        with open(uploaded_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")
    finally:
        file.file.close()
    try:
        print(f"Calling data_handler to process: {uploaded_file_path}")
        record_count = data_handler.load_and_clean_data(uploaded_file_path)
        sequence_cache.clear()
        print("Sequence cache cleared due to new data upload.")
        return {"message": f"File '{file.filename}' uploaded and processed successfully.", "records_loaded": record_count}
    except FileNotFoundError:
        print(f"Error: data_handler couldn't find the file at {uploaded_file_path}")
        raise HTTPException(status_code=500, detail="Internal server error: Saved file could not be found by data handler.")
    except ValueError as ve:
        print(f"Data processing error: {ve}")
        raise HTTPException(status_code=400, detail=f"Error processing CSV file: {ve}")
    except Exception as e:
        print(f"Unexpected error during data processing: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during data processing: {e}")


@app.get("/generate-sequence/", tags=["DNA Analysis"])
async def generate_sequence_endpoint(id: str = Query(..., description="ID of the sample (e.g., id_0001)", example="id_0001")):
    """ Generates or retrieves cached DNA sequence for a given sample ID. """
    sequence = await _get_sequence_by_id(id)
    return {"id": id, "sequence": sequence}


@app.get("/compare-sequences/", tags=["DNA Analysis"])
async def compare_sequences_endpoint(
    id1: str = Query(..., description="ID of the first sample", example="id_0001"),
    id2: str = Query(..., description="ID of the second sample", example="id_0005")
):
    """ Compares DNA of two samples and returns similarity score (Jaccard Index on 4-mers). """
    print(f"Comparing sequences for IDs: {id1} and {id2}")
    seq1 = await _get_sequence_by_id(id1)
    seq2 = await _get_sequence_by_id(id2)
    try:
        similarity_score = sequence_utils.compare_sequences(seq1, seq2)
        print(f"Calculated similarity score for {id1} vs {id2}: {similarity_score}")
        return {"id1": id1, "id2": id2, "similarity_score": similarity_score}
    except Exception as e:
        print(f"Error during sequence comparison for IDs {id1}, {id2}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to compare sequences for IDs '{id1}' and '{id2}'.")


# Step 9: Implement the /ask-me-anything/ endpoint
@app.post("/ask-me-anything/", tags=["General"])
async def ask_me_anything_endpoint(request: QueryRequest):
    """
    Receives a natural language query (in JSON body: {"query": "Your question"})
    and uses the LLM (Gemini) to provide information about this API's capabilities.
    """
    user_query = request.query
    print(f"Received query for /ask-me-anything: '{user_query}'")

    # Make sure LLM was configured before proceeding
    if not llm_integration.llm_configured:
         # Use 503 Service Unavailable as the service isn't ready due to config
         raise HTTPException(status_code=503, detail="Service Unavailable: LLM integration is not configured. Please check the server logs and ensure the GOOGLE_API_KEY is set.")

    try:
        # Call the function in llm_integration.py that interacts with the LLM
        llm_answer = llm_integration.ask_llm(user_query)

        # The ask_llm function should return an error string if it fails,
        # so we just return whatever it gives back.
        return {"response": llm_answer}

    except Exception as e:
        # Generic fallback error handler for unexpected issues in this endpoint handler itself
        print(f"Unexpected error in /ask-me-anything endpoint handler: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while processing your query: {e}")


# --- Run Instruction (for local development) ---
# uvicorn main:app --reload
# Go to http://127.0.0.1:8000/docs