import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from learning_space_generator import build_knowledge_space

args = [
    '--csv', 'learning_space_generator/data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv',
    '--out', 'learning_space_generator/output',
    '--pred', 'learning_space_generator/output/pred_probs.npy',
    '--item_cols', 'learning_space_generator/output/item_cols.npy',
    '--select_k', '30',
    '--force_k',
    '--pred_threshold', '0.6'
]

if __name__ == '__main__':
    build_knowledge_space.main(args)
