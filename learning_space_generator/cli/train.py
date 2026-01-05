"""CLI command for training the MIRT-VAE model.

Usage: python -m learning_space_generator.cli.train --csv PATH --out PATH [--epochs N] [--latent D] [--device cpu]
"""
import argparse
import logging
from ..infrastructure import model_trainer


def main(argv=None):
    parser = argparse.ArgumentParser(prog='lsg-train')
    parser.add_argument('--csv', required=True, help='Input CSV with response patterns')
    parser.add_argument('--out', default='learning_space_generator/output', help='Output directory')
    parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--latent', type=int, default=10)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    model_trainer.main(args.csv, args.out, epochs=args.epochs, latent_dim=args.latent, device=args.device)


if __name__ == '__main__':
    main()
