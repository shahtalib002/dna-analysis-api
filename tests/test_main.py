# tests/test_main.py

import io
from fastapi.testclient import TestClient
from unittest.mock import patch # Import patch for mocking

# Import the 'app' instance from your main application file
import sys
import os

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    from main import app # Import the FastAPI app instance
except ImportError as e:
    print(f"Error importing 'app' from main: {e}")
    from fastapi import FastAPI
    app = FastAPI() # Placeholder

# Create a TestClient instance
client = TestClient(app)


# --- Test Functions ---

def test_read_root():
    """ Test the root endpoint (GET /) """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Ancient DNA Analysis API!"}


def test_upload_csv_success():
    """ Test successful upload of a valid CSV file via POST /upload-csv/ """
    # 1. Define sample valid CSV data
    csv_content = "id,region,age,seed\nid_test_001,TestRegion,30,agtc1234\n"
    csv_file_object = io.BytesIO(csv_content.encode('utf-8'))

    # 2. Simulate the POST request
    response = client.post(
        "/upload-csv/",
        files={"file": ("test_upload.csv", csv_file_object, "text/csv")}
    )

    # 3. Assert the response indicates success
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "File 'test_upload.csv' uploaded and processed successfully."
    assert response_data["records_loaded"] == 1


# --- New Test for Generate Sequence (using Mocking) ---
# Use the @patch decorator to replace the real function during this test
@patch('main.sequence_utils.generate_dna_sequence')
def test_generate_sequence_success(mock_generate_sequence):
    """
    Test GET /generate-sequence/ for a valid ID after upload.
    Uses mocking to avoid running the expensive generation function.
    The mock_generate_sequence argument is automatically provided by @patch.
    """
    # --- Arrange ---
    # 1. Configure the mock function: Make it return a known, simple value instantly.
    mock_return_value = "mocked_sequence_agtc"
    mock_generate_sequence.return_value = mock_return_value

    # 2. Ensure data is loaded for the test: Upload test CSV data first.
    #    This makes sure the endpoint finds the ID and validity flags.
    csv_content_for_gen = "id,region,age,seed\nid_gen_test_001,ValidRegion,50,agct\n"
    csv_file_obj_for_gen = io.BytesIO(csv_content_for_gen.encode('utf-8'))
    upload_response = client.post(
        "/upload-csv/",
        files={"file": ("test_for_gen.csv", csv_file_obj_for_gen, "text/csv")}
    )
    # Check upload was successful before proceeding
    assert upload_response.status_code == 200, "Prerequisite failed: Could not upload data for generation test."

    # ID known to be in the uploaded test data
    test_id = "id_gen_test_001"

    # --- Act ---
    # Call the endpoint we want to test
    response = client.get(f"/generate-sequence/?id={test_id}")

    # --- Assert ---
    # Check the response status code
    assert response.status_code == 200

    # Check the response content matches what the mock should have returned
    response_data = response.json()
    assert response_data["id"] == test_id
    assert response_data["sequence"] == mock_return_value

    # Check that our mock function was actually called once by the endpoint logic
    mock_generate_sequence.assert_called_once()
    # We could also assert *what* arguments it was called with, e.g.:
    # mock_generate_sequence.assert_called_once_with(id=1, region='ValidRegion', age=50, dna_seed='agct')


# --- Add more tests below ---