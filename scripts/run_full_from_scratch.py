import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from learning_space_generator.core import LearningSpaceBuilder, BuilderConfig
import logging

logging.basicConfig(level=logging.INFO)

cfg = BuilderConfig(
    csv_path='learning_space_generator/data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv',
    out_dir='learning_space_generator/output',
    epochs=8,
    latent=10,
    pred_threshold=0.6,
    implication_threshold=0.85,
    min_known=10,
    select_k=30,
    force_k=True
)

builder = LearningSpaceBuilder(cfg)

if __name__ == '__main__':
    results = builder.run_all(run_train=True)
    print('Done. Outputs:')
    for k, v in results.items():
        print(f'- {k}: {v}')
