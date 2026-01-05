import torch
import torch.nn as nn
import torch.nn.functional as F


class MirtVAE(nn.Module):
    def __init__(self, n_items, latent_dim=10, hidden_dim=128):
        super().__init__()
        self.n_items = n_items
        self.latent_dim = latent_dim

        # encoder: input = values + mask as channels (2*n_items)
        self.enc_fc1 = nn.Linear(n_items * 2, hidden_dim)
        self.enc_fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.enc_mu = nn.Linear(hidden_dim, latent_dim)
        self.enc_logvar = nn.Linear(hidden_dim, latent_dim)

        # decoder: discrimination matrix and bias
        self.discrimination = nn.Parameter(torch.randn(n_items, latent_dim) * 0.1)
        self.item_bias = nn.Parameter(torch.zeros(n_items))

    def encode(self, x, mask):
        # x: batch x n_items, mask: batch x n_items
        inp = torch.cat([x, mask.float()], dim=1)
        h = F.relu(self.enc_fc1(inp))
        h = F.relu(self.enc_fc2(h))
        mu = self.enc_mu(h)
        logvar = self.enc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu, logvar):
        std = (0.5 * logvar).exp()
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode_logits(self, z):
        # logits: z @ W^T + b
        logits = z @ self.discrimination.t() + self.item_bias
        return logits

    def forward(self, x, mask):
        mu, logvar = self.encode(x, mask)
        z = self.reparameterize(mu, logvar)
        logits = self.decode_logits(z)
        return logits, mu, logvar
