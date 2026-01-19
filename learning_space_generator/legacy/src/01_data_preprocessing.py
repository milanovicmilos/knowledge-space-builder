import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import os

def load_and_clean_data(filepath):
    print(f"Loading data from {filepath}...")
    try:
        df = pd.read_csv(filepath, sep=';')
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

    # Identify item columns (start with 's')
    item_cols = [col for col in df.columns if col.startswith('s')]
    print(f"Found {len(item_cols)} items.")

    # Select only items
    data = df[item_cols].copy()

    # Basic cleaning: 9999, 666 -> 0 (Incorrect/Missing)
    # KST usually treats missing as incorrect in surmise analysis
    data.replace({9999: 0, 666: 0}, inplace=True)
    
    # Ensure binary
    data = data.applymap(lambda x: 1 if x == 1 else 0)
    
    return data, item_cols

class DenoisingAutoencoder(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super(DenoisingAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

def train_dae(data_matrix, epochs=50, batch_size=32, learning_rate=0.001):
    input_dim = data_matrix.shape[1]
    hidden_dim = input_dim // 2 # Compressed representation
    
    model = DenoisingAutoencoder(input_dim, hidden_dim)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.BCELoss() # Binary Cross Entropy

    # Convert to Tensor
    tensor_data = torch.FloatTensor(data_matrix.values)
    dataset = TensorDataset(tensor_data, tensor_data) # Target is original data
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print(f"Training DAE for {epochs} epochs...")
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_features, _ in dataloader:
            # Add noise: randomly flip bits? Or just regular dropout noise?
            # Standard DAE uses dropout on inputs
            noisy_inputs = batch_features * (torch.rand_like(batch_features) > 0.1).float() # 10% dropout noise
            
            optimizer.zero_grad()
            outputs = model(noisy_inputs)
            loss = criterion(outputs, batch_features) # Compare to clean original
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if (epoch+1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.4f}")

    return model

def denoise_data(model, data, threshold=0.5):
    model.eval()
    with torch.no_grad():
        tensor_data = torch.FloatTensor(data.values)
        reconstructed = model(tensor_data)
        # Binarize output
        cleaned_data = (reconstructed > threshold).int().numpy()
        
    return pd.DataFrame(cleaned_data, columns=data.columns, index=data.index)

if __name__ == "__main__":
    # Settings
    INPUT_FILE = "matheGesamt.csv" # Root path
    OUTPUT_FILE = "data/cleaned_responses.csv"
    
    # 1. Load
    raw_data, cols = load_and_clean_data(INPUT_FILE)
    
    if raw_data is not None:
        # 2. Train DAE
        print("Training Denoising Autoencoder...")
        dae_model = train_dae(raw_data)
        
        # 3. Denoise
        print("Denoising data...")
        cleaned_df = denoise_data(dae_model, raw_data)
        
        # 4. Save
        cleaned_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Cleaned data saved to {OUTPUT_FILE}")
        
        # Validation stats
        diffs = (raw_data != cleaned_df).sum().sum()
        total = raw_data.size
        print(f"Validation: Cleaned {diffs} entries out of {total} ({diffs/total:.2%} changed).")
        print("Sample of cleaning (First 5 rows):")
        print(cleaned_df.head())
