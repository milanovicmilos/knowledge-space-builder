import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from learning_space_generator.app.core.config import settings
from learning_space_generator.app.models.dae import DenoisingAutoencoder
import logging

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

        # Identify item columns (start with 's', heuristic from original script)
        # Note: Original script logic was: [col for col in df.columns if col.startswith('s')]
        # But 'standort' starts with 's'. The original script might have filtered it later or relied on len > ?
        # In 01_data_preprocessing.py, it just did `col.startswith('s')`.
        # However, checking the output from previous turns, 'standort' was present in the cleaned data.
        # It's safer to exclude 'standort' explicitly if it exists.
        
        item_cols = [col for col in df.columns if col.startswith('s') and col.lower() != 'standort']
        logger.info(f"Found {len(item_cols)} items.")

        data = df[item_cols].copy()

        # Cleaning missing/invalid codes
        data.replace({9999: 0, 666: 0}, inplace=True)
        # Binarize
        # Using map instead of applymap (future warning fix)
        data = data.map(lambda x: 1 if x == 1 else 0)
        
        return data, item_cols

    def train_dae(self, data_matrix: pd.DataFrame) -> DenoisingAutoencoder:
        input_dim = data_matrix.shape[1]
        hidden_dim = max(input_dim // 2, 1) # Ensure at least 1
        
        model = DenoisingAutoencoder(input_dim, hidden_dim)
        optimizer = optim.Adam(model.parameters(), lr=settings.DAE_LEARNING_RATE)
        criterion = nn.BCELoss()

        tensor_data = torch.FloatTensor(data_matrix.values)
        dataset = TensorDataset(tensor_data, tensor_data)
        dataloader = DataLoader(dataset, batch_size=settings.DAE_BATCH_SIZE, shuffle=True)

        logger.info(f"Training DAE for {settings.DAE_EPOCHS} epochs...")
        model.train()
        
        for epoch in range(settings.DAE_EPOCHS):
            total_loss = 0
            for batch_features, _ in dataloader:
                # Add noise
                mask = (torch.rand_like(batch_features) > settings.DAE_NOISE_FACTOR).float()
                noisy_inputs = batch_features * mask
                
                optimizer.zero_grad()
                outputs = model(noisy_inputs)
                loss = criterion(outputs, batch_features)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(dataloader)
                logger.info(f"Epoch {epoch+1}/{settings.DAE_EPOCHS}, Loss: {avg_loss:.4f}")

        return model

    def denoise_data(self, model: DenoisingAutoencoder, data: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
        logger.info("Denoising data...")
        model.eval()
        with torch.no_grad():
            tensor_data = torch.FloatTensor(data.values)
            reconstructed = model(tensor_data)
            cleaned_vals = (reconstructed > threshold).int().numpy()
            
        return pd.DataFrame(cleaned_vals, columns=data.columns, index=data.index)

    def run_preprocessing(self):
        # High level orchestration
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
        # Since logic was data.map, types are consistent. 
        # But data might have been float in torch steps? No, pandas int -> float tensor -> numpy int.
        
        diff = (data != cleaned_data).sum().sum()
        logger.info(f"Changed {diff} entries out of {total_elements} ({diff/total_elements:.2%})")

    def load_cleaned_data(self) -> pd.DataFrame:
        """Load already-cleaned data from output directory."""
        if not settings.CLEANED_DATA_FILE.exists():
            raise FileNotFoundError(f"{settings.CLEANED_DATA_FILE} not found. Run preprocessing first.")
        return pd.read_csv(settings.CLEANED_DATA_FILE)

preprocessing_service = PreprocessingService()
