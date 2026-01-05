import numpy as np
import os
os.makedirs('learning_space_generator/output', exist_ok=True)
np.random.seed(0)
probs = np.random.rand(200,30)
np.save('learning_space_generator/output/pred_probs.npy', probs)
cols = np.array([f'item{i}' for i in range(30)], dtype=object)
np.save('learning_space_generator/output/item_cols.npy', cols)
print('Synthetic pred_probs and item_cols saved to learning_space_generator/output')
