# Learning Space Generator

Evolutionary algorithm for constructing optimal [learning spaces](https://arxiv.org/abs/1511.06757) from response patterns using NEAT with automatic item clustering.

## Features

- **NEAT Algorithm**: Evolutionary search for optimal learning spaces
- **Item Clustering**: Automatic partitioning for datasets with 50+ items
- **Missing Value Handling**: Native support for incomplete response data
- **Automatic K Selection**: Silhouette-based cluster count determination
- **Original Item IDs**: Preserves question codes (M178832, M178357...) in output

## Installation

Requires Python 3.10+

```bash
cd learning-space-generator
pip install -r requirements.txt
```

Use virtual environment for dependency isolation.

## Usage

### Basic Usage (No Clustering)

```bash
python -m lsg.run --data-path data/ResponsePatterns.csv --generations 50 --parallel --json output.json
```

### With Item Clustering (Recommended for 50+ Items)

```bash
python -m lsg.run \
  --data-path data/ResponsePatterns.csv \
  --cluster \
  --row-coverage-thresh 0.8 \
  --min-pairs 500 \
  --generations 50 \
  --patience 20 \
  --parallel \
  --json output.json
```

### Parameters

**Item Clustering Options:**
- `--cluster`: Enable automatic item clustering
- `--row-coverage-thresh`: Minimum row coverage per cluster (default: 0.8)
- `--min-pairs`: Minimum item pairs per cluster (default: 500)
- `--max-item-clusters`: Maximum clusters (auto if omitted)

**NEAT Options:**
- `--generations`: Maximum evolution iterations (default: 50)
- `--patience`: Early stopping patience (default: 20)
- `--parallel`: Enable parallel genome evaluation
- `--greedy`: Stop at first valid solution

**Missing Value Options:**
- `--missing-match-reward`: Reward for matching missing values (default: 0.5)
- `--missing-mismatch-penalty`: Penalty for mismatched missing (default: 1.0)

**Output:**
- `--json <path>`: Save learning space as JSON
- `--png <path>`: Export graph visualization

Run `python -m lsg.run --help` for full options.

## Input Format

CSV matrix (NxM): N response patterns × M knowledge items

Example:
```csv
M178832,M178357,M176963,...
1,0,1,...
-,1,0,...
1,1,1,...
```

- `1` = correct answer
- `0` = incorrect answer  
- `-` or empty = missing value

## Output Format

JSON with original item IDs:

```json
{
  "∅": ["{M178832}", "{M178357}"],
  "{M178832}": ["{M178832, M178357}"],
  "{M178357}": ["{M178832, M178357}"],
  "{M178832, M178357}": []
}
```

Keys = knowledge states, Values = successor states

## Algorithm Details

NEAT (NeuroEvolution of Augmenting Topologies) adapted for learning space construction:

- **Genome**: Represents learning space as directed acyclic graph (DAG)
- **Constraints**: Enforces closure under union, empty state presence
- **Fitness**: Measures correspondence to observed response patterns
- **Missing-Aware**: Evaluates fitness with mask arrays for incomplete data

### Item Clustering

For datasets with 50+ items:
1. Computes pairwise item distance from response patterns
2. Agglomerative hierarchical clustering with Ward linkage
3. Silhouette analysis selects optimal K
4. NEAT runs independently on each cluster
5. Results merged into unified learning space

## Configuration

NEAT parameters in [config/default.ini](config/default.ini):
- Genome structure settings
- Mutation/crossover probabilities
- Fitness evaluation thresholds

## License

MIT License - see [LICENSE](LICENSE)

### Gene

Knowledge state is used as gene in NEAT genomes. Each knowledge state is
represented as bit array where _i-th_ bit is `1` if _i-th_ assessment question
is answered correctly or `0` otherwise. Bit array representation is useful for
fast operations related to knowledge items such as comparison, mutation etc.

### Genome

Learning space is genome in NEAT algorithm. It is represented as set of genes
(knowledge states).  Mutation of learning space ensures that closure under
union is satisfied. At the beginning of evolution, random population of
learning spaces with two knowledge items (empty state and one random single
item state) is created and evolved over provided number of generations.

Result of NEAT evolution is genome (learning space) with the best fitness score.

### Fitness

Fitness is defined as sum of genome size and discrepancy between given learning space and
observed response patterns. This way, genomes with lower number of knowledge states is favored.

`fitness = -(discrepancy + size)`

Negative fitness is used because
[neat-python](https://neat-python.readthedocs.io/en/latest/) library maximizes
fitness value.

Discrepancy is computational heavy and it is cached to provide significant speed-up.

### Mutation

During mutation, a random knowledge state (gene) from learning space (genome)
is selected for mutation.  Mutation consists of flipping a random bit in
knowledge state. If mutated knowledge state is not present in learning space,
it is added with any additional knowledge states to preserve closure under
union.

Different gene selection strategies are implemented, where selecting random
gene from uniform distribution provides the best results (it converges faster
than other strategies).

### Parallel Evaluation

Parallel evaluation uses all available CPU cores and it should be omitted for
small learning spaces when number of knowledge items is less than 8 and number
of genomes in population is under 500. In those situations, parallel evaluation
introduces additional overhead for process creation and single global cache
synchronization.

When number of knowledge items is greater than 8 and population size is in
thousands, parallel evaluation provides significant speed-up.

### Termination Condition

The termination condition of a genetic algorithm (GA) is important in
determining when a GA run will end. It has been observed that initially, the GA
progresses very fast with better solutions coming in every few iterations, but
this tends to saturate in the later stages where the improvements are very
small.

Evolution process stops when:

- genome with perfect fitness (0 fitness) is found, or
- global best fitness score doesn't improve for _t_ generations.

Parameter _t_ indicates `patience` for fitness improvement and it can be set with
`--patience` or `-t` parameter when starting algorithm in `lsg.run`.

## License

This project is available as open source under the terms of the [MIT License](http://opensource.org/licenses/MIT).
