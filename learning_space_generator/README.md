# Learning Space Generator - MIRT-VAE

Knowledge space generation using **MIRT-VAE** (Multidimensional Item Response Theory - Variational Autoencoder).

## Overview

This package implements a two-phase pipeline for discovering knowledge structures from educational assessment data:

1. **Phase 1: MIRT-VAE Training** - Learn latent representations of student knowledge from response patterns
2. **Phase 2: Lattice Construction** - Infer prerequisite relationships and generate knowledge space lattice

## Architecture

```
learning_space_generator/
├── infrastructure/      # Technical implementations
│   ├── mirt_vae.py     # VAE neural network architecture
│   ├── model_trainer.py # Training loop and optimization
│   ├── data_loader.py  # CSV data preprocessing
│   └── visualization.py # Graph plotting utilities
├── domain/             # Business logic
│   └── services/
│       ├── prerequisite_builder.py  # Prerequisite inference
│       ├── lattice_builder.py      # Knowledge state generation
│       └── analyzer.py             # Lattice statistics
├── application/        # Orchestration layer
│   └── orchestrator.py # Two-phase pipeline coordinator
└── cli/               # Command-line interface
    ├── train.py       # Phase 1: MIRT-VAE training
    └── build.py       # Phase 2: Lattice construction
```

## Installation

```bash
cd learning_space_generator
pip install -r requirements.txt
```

Requires Python 3.10+ and PyTorch 2.0+.

## Usage

### CLI - Two-Phase Pipeline

**Phase 1: Train MIRT-VAE**
```bash
python -m learning_space_generator.cli.main train \
  --csv data/ResponsePatterns.csv \
  --out_dir output \
  --epochs 8 \
  --latent_dim 10
```

Outputs:
- `output/pred_probs.npy` - Predicted probabilities (N_students × N_items)
- `output/item_cols.npy` - Item names/IDs

**Phase 2: Build Knowledge Space**
```bash
python -m learning_space_generator.cli.main build \
  --pred_probs output/pred_probs.npy \
  --item_cols output/item_cols.npy \
  --select_k 30 \
  --min_support 7 \
  --pred_threshold 0.6 \
  --implication_threshold 0.85 \
  --out_dir output
```

Outputs:
- `prereq_graph.json` - Prerequisite relationships (DAG)
- `knowledge_space_lattice_k30.json` - Final knowledge space with states
- `knowledge_space_k30_summary.json` - Statistics (num_states, num_edges, etc.)
- PNG visualizations

### Python API

```python
from learning_space_generator.application.orchestrator import LearningSpaceBuilder, BuilderConfig

# Configure pipeline
config = BuilderConfig(
    csv_path='data/ResponsePatterns.csv',
    out_dir='output',
    epochs=8,
    latent_dim=10,
    pred_threshold=0.6,
    implication_threshold=0.85,
    min_known=10,
    select_k=30,
    min_support=7
)

# Run full pipeline
builder = LearningSpaceBuilder(config)
results = builder.run_all(run_train=True)

print(f"Knowledge space: {results['num_states']} states, {results['num_edges']} edges")
```

## Parameters

### MIRT-VAE Training
- `--epochs`: Number of training epochs (default: 8)
- `--latent_dim`: Latent dimensionality (number of knowledge domains, default: 10)
- `--batch_size`: Training batch size (default: 1024)
- `--learning_rate`: Adam optimizer learning rate (default: 1e-3)

### Prerequisite Inference
- `--pred_threshold`: Binarization threshold for predictions (default: 0.6)
- `--implication_threshold`: Minimum implication rate for A→B (default: 0.85)
- `--min_known`: Minimum students knowing item B to infer A→B (default: 10)

### Lattice Construction
- `--select_k`: Number of items to select for lattice (default: 30)
- `--min_support`: Minimum frequency for empirical states (default: 7)
- `--force_k`: Expand selection to include ancestor items (default: True)

## Algorithm Details

### MIRT-VAE Architecture
- **Encoder**: Response patterns → 128 hidden units → latent_dim (mean, variance)
- **Decoder**: Latent vector → discrimination matrix (items × latent_dim) + item bias
- **Loss**: BCE(reconstruction) + 0.001 × KL(latent || N(0,1))

### Prerequisite Inference
For each item pair (A, B):
```
implication_rate = P(knows A | knows B) = (knows_A ∩ knows_B) / knows_B

If implication_rate ≥ threshold:
    Add edge A → B (A is prerequisite for B)
```

### Lattice Construction
1. Select top-k items by degree (in+out)
2. Generate all valid knowledge states (ideals respecting prerequisite DAG)
3. For empirical mode: binarize predictions, count state frequencies, filter by min_support
4. Build Hasse diagram (cover relations) from final states

## Output Format

**knowledge_space_lattice_k30.json**:
```json
{
  "states": [
    {"id": 0, "items": [], "label": "{}"},
    {"id": 1, "items": ["M001"], "label": "{M001}"},
    {"id": 2, "items": ["M001", "M002"], "label": "{M001, M002}"}
  ],
  "edges": [
    {"from": 0, "to": 1, "label": "M001"},
    {"from": 1, "to": 2, "label": "M002"}
  ]
}
```

## Data Format

Input CSV: N rows (students) × M columns (items)
- Values: 0 (incorrect), 1 (correct), - or empty (missing)
- Header: Item IDs (e.g., M178832, Q001, etc.)

Example:
```csv
M001,M002,M003
1,0,1
-,1,0
1,1,1
```

## References

- Doignon, J.-P., & Falmagne, J.-C. (1999). *Knowledge Spaces*. Springer.
- Kingma, D. P., & Welling, M. (2014). *Auto-Encoding Variational Bayes*. ICLR.
- Reckase, M. D. (2009). *Multidimensional Item Response Theory*. Springer.
