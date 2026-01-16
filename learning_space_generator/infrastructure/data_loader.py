import pandas as pd
import numpy as np
import os


def load_response_csv(path, sep=';'):
    # Try with provided sep, fall back to comma
    try:
        df = pd.read_csv(path, sep=sep, dtype=str)
    except Exception:
        df = pd.read_csv(path, sep=',', dtype=str)

    # Assume first column is student id if its name indicates such
    cols = list(df.columns)
    
    # Skip metadata columns (non-item columns)
    # Metadata patterns: 'standort', 'klasser', 'idr', 'BookletT1', 'BookletT2', 'studentID', etc.
    metadata_patterns = ['standort', 'klasser', 'idr', 'booklet', 'student', 'id', 'grade', 'school']
    
    # Filter out metadata columns (case-insensitive)
    data_cols = []
    for col in cols:
        col_lower = col.lower()
        is_metadata = any(pattern in col_lower for pattern in metadata_patterns)
        # Also check if column name looks like an item code (starts with letter+number or M+number)
        is_item = (len(col) > 3 and (col[0].isalpha() and col[1:3].replace('m', '').isdigit()))
        
        if not is_metadata or is_item:
            data_cols.append(col)
    
    # If we filtered everything, fall back to skipping first column only
    if not data_cols:
        data_cols = cols[1:] if len(cols) > 1 else cols
    
    values = df[data_cols].replace({'NA': np.nan, 'NaN': np.nan, '': np.nan}).astype(object)

    # Map to numeric: 0/1 valid, everything else (9999, 666, 777, NA, etc.) → NaN
    def convert_value(x):
        if pd.isna(x):
            return np.nan
        s = str(x).strip()
        if s in ('1', 'True', 'true', 'T'):
            return 1.0
        elif s in ('0', 'False', 'false', 'F'):
            return 0.0
        else:
            # Anything else (9999, 666, 777, etc.) becomes missing
            return np.nan
    
    # Apply conversion to each column
    arr = values.map(convert_value).to_numpy(dtype=float)

    mask = ~np.isnan(arr)
    X = np.nan_to_num(arr, nan=0.0)

    item_cols = np.array(data_cols, dtype=object)

    return X, mask, item_cols


def save_output_arrays(out_dir, pred_probs, item_cols):
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, 'pred_probs.npy'), pred_probs)
    np.save(os.path.join(out_dir, 'item_cols.npy'), item_cols)
