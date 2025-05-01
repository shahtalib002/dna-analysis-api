# data_handler.py

import pandas as pd
import numpy as np # Required for checking NaN specifically

# --- Global Variable ---
# This will hold the cleaned data once loaded.
# It's None initially, indicating no data has been loaded.
cleaned_data_df: pd.DataFrame | None = None

# --- Functions ---

def load_and_clean_data(csv_path: str) -> int:
    """
    Loads data from a CSV file, performs cleaning based on expected columns
    ('id', 'region', 'age', 'seed'), and stores it in the global DataFrame.

    Args:
        csv_path: The file path to the CSV file.

    Returns:
        The number of records successfully loaded and processed.

    Raises:
        FileNotFoundError: If the csv_path does not exist.
        ValueError: If essential columns are missing or 'id' format is unexpected.
        Exception: For other potential pandas or processing errors.
    """
    global cleaned_data_df
    print(f"Attempting to load data from: {csv_path}") # Log attempt

    try:
        df = pd.read_csv(csv_path)
        print(f"Successfully read CSV. Found {len(df)} rows.") # Log success

        # --- Validate required columns ---
        required_columns = ['id', 'region', 'age', 'seed']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"CSV is missing required column: '{col}'")

        # --- Handle 'id' ---
        # Extract integer part, handle potential errors if format isn't 'id_xxxx'
        # Assumes format like 'id_0001'. Converts non-matching to -1.
        df['id_int'] = df['id'].astype(str).str.split('_').str[-1]
        df['id_int'] = pd.to_numeric(df['id_int'], errors='coerce').fillna(-1).astype(int)
        if (df['id_int'] == -1).any():
             print("Warning: Some 'id' values did not match 'id_NUMBER' format and were assigned id_int=-1.")

        # --- Handle 'region' ---
        # Fill missing values (NaN, None) and empty strings with "Unknown"
        df['region'] = df['region'].fillna("Unknown").replace('', "Unknown").astype(str)

        # --- Handle 'age' ---
        # 1. Identify rows where original age is invalid (not numeric)
        df['age_was_invalid'] = pd.to_numeric(df['age'], errors='coerce').isna()
        # 2. Convert age to numeric (errors become NaN), fill NaN with -1, cast to int
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(-1).astype(int)
        if df['age_was_invalid'].any():
            print("Warning: Some 'age' values were non-numeric and have been set to -1.")


        # --- Handle 'seed' ---
        # 1. Identify rows where seed is missing (NaN, None, or empty string)
        # Ensure seed column is treated as string first for reliable empty check
        df['seed_is_missing'] = df['seed'].isna() | (df['seed'].astype(str).str.strip() == '')
        # 2. Fill missing seeds with an empty string AFTER checking missing status
        df['seed'] = df['seed'].fillna("").astype(str)
        if df['seed_is_missing'].any():
            print("Warning: Some 'seed' values were missing.")


        # --- Final Validity Check ---
        # A record is valid for sequence generation if its original age was valid
        # AND its seed was not missing.
        df['is_valid_for_generation'] = ~df['age_was_invalid'] & ~df['seed_is_missing']

        # Optional: Drop temporary helper columns if you don't need them later
        # df = df.drop(columns=['age_was_invalid', 'seed_is_missing'])

        # --- Store Cleaned Data Globally ---
        cleaned_data_df = df
        num_records = len(df)
        print(f"Data loaded and cleaned successfully. {num_records} records stored.")
        return num_records

    except FileNotFoundError:
        print(f"Error: File not found at {csv_path}")
        cleaned_data_df = None # Ensure data is None on error
        raise # Re-raise for the API endpoint to handle
    except ValueError as ve:
        print(f"Error processing CSV: {ve}")
        cleaned_data_df = None
        raise
    except Exception as e:
        # Catch other potential errors during loading/processing
        print(f"An unexpected error occurred during data loading: {e}")
        cleaned_data_df = None
        raise


def get_record_by_id(target_id_str: str) -> pd.Series | None:
    """
    Retrieves a cleaned record (as a pandas Series) by its original string ID.

    Args:
        target_id_str: The original string ID (e.g., "id_0001").

    Returns:
        A pandas Series containing the data for the found record, or None if
        data isn't loaded or the ID is not found.
    """
    if cleaned_data_df is None:
        # Data hasn't been loaded via /upload-csv yet
        print("Error: Cannot get record, data has not been loaded.")
        return None

    # Search for the ID in the original 'id' column
    record = cleaned_data_df[cleaned_data_df['id'] == target_id_str]

    if record.empty:
        # ID was not found in the loaded data
        return None
    else:
        # Return the first match as a Series (IDs should be unique)
        return record.iloc[0]


def is_data_loaded() -> bool:
    """
    Simple check to see if the global DataFrame has been populated.

    Returns:
        True if data has been loaded, False otherwise.
    """
    return cleaned_data_df is not None