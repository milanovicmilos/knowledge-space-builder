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
    # Convert values to 0/1/NA
    data_cols = cols[1:] if len(cols) > 1 else cols
    values = df[data_cols].replace({'NA': np.nan, 'NaN': np.nan, '': np.nan}).astype(object)

    # Map to numeric where possible (DataFrame.apply + Series.map to avoid deprecated applymap)
    mapper = lambda x: np.nan if (pd.isna(x) or str(x).strip().upper() == 'NA') else (1 if str(x).strip() in ('1', 'True', 'true', 'T') else (0 if str(x).strip() in ('0', 'False', 'false', 'F') else np.nan))
    arr = values.apply(lambda col: col.map(mapper)).to_numpy(dtype=float)

    mask = ~np.isnan(arr)
    X = np.nan_to_num(arr, nan=0.0)

    item_cols = np.array(data_cols, dtype=object)

    return X, mask, item_cols


def save_output_arrays(out_dir, pred_probs, item_cols):
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, 'pred_probs.npy'), pred_probs)
    np.save(os.path.join(out_dir, 'item_cols.npy'), item_cols)
