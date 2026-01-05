import os
import time
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
import torch.nn.functional as F
import logging
import random

from .data_loader import load_response_csv
from .mirt_vae import MirtVAE

logger = logging.getLogger(__name__)


def train_vae(X, mask, n_items, out_dir, epochs=8, batch_size=1024, latent_dim=10, lr=1e-3, device='cpu'):
    model = MirtVAE(n_items=n_items, latent_dim=latent_dim)
    model.to(device)

    x_t = torch.from_numpy(X).float()
    m_t = torch.from_numpy(mask.astype(float)).float()
    ds = TensorDataset(x_t, m_t)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True)

    opt = torch.optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs + 1):
        t0 = time.time()
        total_loss = 0.0
        model.train()
        for xb, mb in dl:
            xb = xb.to(device)
            mb = mb.to(device)
            opt.zero_grad()
            logits, mu, logvar = model(xb, mb)
            # BCE on observed entries only
            loss_recon = F.binary_cross_entropy_with_logits(logits, xb, reduction='none')
            loss_recon = (loss_recon * mb).sum() / (mb.sum() + 1e-8)
            # KLD
            kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1).mean()
            loss = loss_recon + 1e-3 * kld
            loss.backward()
            opt.step()
            total_loss += loss.item() * xb.size(0)
        logger.info('Epoch %d/%d loss=%.4f time=%.1fs', ep, epochs, total_loss / len(ds), time.time() - t0)

    # produce predictions for all
    model.eval()
    with torch.no_grad():
        xb = x_t.to(device)
        mb = m_t.to(device)
        logits, _, _ = model(xb, mb)
        probs = torch.sigmoid(logits).cpu().numpy()

    # predictions will be saved by caller; do not overwrite item_cols
    return probs


def main(csv_path, out_dir, epochs=8, latent_dim=10, device='cpu'):
    # make runs deterministic
    seed = 42
    np.random.seed(seed)
    torch.manual_seed(seed)
    random.seed(seed)

    X, mask, item_cols = load_response_csv(csv_path)
    n_items = X.shape[1]
    # save item cols
    os.makedirs(out_dir, exist_ok=True)
    # ensure item_cols saved as 1-D array of strings and also as plain text
    item_arr = np.asarray(item_cols, dtype=str)
    np.save(os.path.join(out_dir, 'item_cols.npy'), item_arr)
    with open(os.path.join(out_dir, 'item_cols.txt'), 'w', encoding='utf-8') as f:
        for it in item_arr:
            f.write(f"{it}\n")
    probs = train_vae(X, mask, n_items, out_dir, epochs=epochs, latent_dim=latent_dim, device=device)
    # ensure pred_probs saved
    np.save(os.path.join(out_dir, 'pred_probs.npy'), probs)
    return probs


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='learning_space_generator/data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')
    parser.add_argument('--out', default='learning_space_generator/output')
    parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--latent', type=int, default=10)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(args.csv, args.out, epochs=args.epochs, latent_dim=args.latent, device=args.device)
