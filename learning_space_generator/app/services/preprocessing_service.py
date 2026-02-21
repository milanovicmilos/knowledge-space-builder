import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from learning_space_generator.app.core.config import settings
from learning_space_generator.app.models.dae import DenoisingAutoencoder
import logging
import os
import random

# Force CPU-only mode (no CUDA)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
torch.cuda.is_available = lambda: False

# Set deterministic seeds for reproducibility
DETERMINISTIC_SEED = settings.RANDOM_SEED
random.seed(DETERMINISTIC_SEED)
np.random.seed(DETERMINISTIC_SEED)
torch.manual_seed(DETERMINISTIC_SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreprocessingService:
    def load_data(self, filepath: str) -> tuple[pd.DataFrame, list]:
        logger.info(f"Loading data from {filepath}...")
        try:
            df = pd.read_csv(filepath, sep=';', encoding='utf-8')
        except Exception as e:
            # Try different encoding or delimiter if simple fail, but user said sep=;
            logger.error(f"Error loading CSV: {e}")
            raise e

        # Identify item columns (heuristic: columns starting with 's').
        # Exclude 'standort' explicitly if present to avoid false positives.
        
        item_cols = [col for col in df.columns if col.startswith('s') and col.lower() != 'standort']
        logger.info(f"Found {len(item_cols)} items.")

        data = df[item_cols].copy()

        # Handle missing/invalid codes properly
        # 9999 = question not in student's test booklet (missing by design)
        # 666 = invalid/unclear response
        # Both should be NaN, NOT 0 (zero means "answered incorrectly")
        data.replace({9999: np.nan, 666: np.nan}, inplace=True)
        
        # Binarize: keep only 1 (correct) and 0 (incorrect)
        # NaN values will remain as NaN
        data = data.map(lambda x: 1 if x == 1 else (0 if x == 0 else np.nan))
        
        logger.info(f"Data shape: {data.shape}")
        coverage = data.notna().sum().sum() / data.size
        logger.info(f"Coverage: {coverage:.1%} of responses observed (rest are missing by design)")
        
        return data, item_cols

    def train_dae(self, data_matrix: pd.DataFrame) -> DenoisingAutoencoder:
        input_dim = data_matrix.shape[1]
        hidden_dim = max(input_dim // 2, 1) # Ensure at least 1
        
        # Fill NaN with 0 for DAE training (will use mask to ignore them in loss)
        data_filled = data_matrix.fillna(0)
        mask = data_matrix.notna().astype(float)  # 1 where observed, 0 where NaN
        
        device = torch.device('cpu')  # Explicitly use CPU
        model = DenoisingAutoencoder(input_dim, hidden_dim).to(device)
        optimizer = optim.Adam(model.parameters(), lr=settings.DAE_LEARNING_RATE)
        criterion = nn.BCELoss(reduction='none')  # Per-element loss for masking

        tensor_data = torch.FloatTensor(data_filled.values).to(device)
        tensor_mask = torch.FloatTensor(mask.values).to(device)
        dataset = TensorDataset(tensor_data, tensor_data, tensor_mask)
        # Use generator with fixed seed for deterministic shuffling
        g = torch.Generator()
        g.manual_seed(DETERMINISTIC_SEED)
        dataloader = DataLoader(dataset, batch_size=settings.DAE_BATCH_SIZE, shuffle=True, generator=g, worker_init_fn=lambda id: np.random.seed(DETERMINISTIC_SEED + id))

        logger.info(f"Training DAE for {settings.DAE_EPOCHS} epochs...")
        logger.info(f"Using masking to handle missing data (NaN values)")
        model.train()
        
        for epoch in range(settings.DAE_EPOCHS):
            total_loss = 0
            for batch_features, batch_targets, batch_mask in dataloader:
                # Add noise (only to observed values)
                noise_mask = (torch.rand_like(batch_features) > settings.DAE_NOISE_FACTOR).float()
                noisy_inputs = batch_features * noise_mask
                
                optimizer.zero_grad()
                outputs = model(noisy_inputs)
                
                # Calculate loss only on observed values
                element_loss = criterion(outputs, batch_targets)
                masked_loss = element_loss * batch_mask
                loss = masked_loss.sum() / batch_mask.sum()  # Average over observed values
                
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(dataloader)
                logger.info(f"Epoch {epoch+1}/{settings.DAE_EPOCHS}, Loss: {avg_loss:.4f}")

        return model

    def denoise_data(self, model: DenoisingAutoencoder, data: pd.DataFrame, threshold: float = None) -> pd.DataFrame:
        logger.info("Denoising data...")
        device = torch.device('cpu')  # Explicitly use CPU
        model.to(device)
        model.eval()
        
        # Fill NaN with 0 for forward pass
        data_filled = data.fillna(0)
        original_mask = data.notna()
        
        # Use threshold from settings if not provided
        if threshold is None:
            threshold = settings.DAE_DENOISE_THRESHOLD
        
        with torch.no_grad():
            tensor_data = torch.FloatTensor(data_filled.values).to(device)
            reconstructed = model(tensor_data)
            cleaned_vals = (reconstructed > threshold).int().cpu().numpy()
        
        # Restore NaN values where they were originally
        cleaned_df = pd.DataFrame(cleaned_vals, columns=data.columns, index=data.index, dtype=float)
        cleaned_df[~original_mask] = np.nan
        
        return cleaned_df

    def run_preprocessing(self):
        # High-level orchestration
        data, cols = self.load_data(settings.INPUT_FILE)
        model = self.train_dae(data)
        cleaned_data = self.denoise_data(model, data)
        
        # Save
        if not settings.OUTPUT_DIR.exists():
            settings.OUTPUT_DIR.mkdir(parents=True)
            
        cleaned_data.to_csv(settings.CLEANED_DATA_FILE, index=False)
        logger.info(f"Cleaned data saved to {settings.CLEANED_DATA_FILE}")
        
        # Validation stats
        total_elements = data.size
        # Data types are handled consistently through map and tensor conversions.
        
        diff = (data != cleaned_data).sum().sum()
        logger.info(f"Changed {diff} entries out of {total_elements} ({diff/total_elements:.2%})")

    def load_cleaned_data(self) -> pd.DataFrame:
        """Load already-cleaned data from output directory."""
        if not settings.CLEANED_DATA_FILE.exists():
            raise FileNotFoundError(f"{settings.CLEANED_DATA_FILE} not found. Run preprocessing first.")
        return pd.read_csv(settings.CLEANED_DATA_FILE)

preprocessing_service = PreprocessingService()
