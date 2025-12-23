import multiprocessing as mp
from abc import abstractmethod, ABC
from collections import defaultdict
from typing import List, Tuple, Dict
import hashlib
import logging

import numpy as np

from .genome import LearningSpaceGenome, LearningSpaceGenomeConfig
from .structure import KnowledgeState

logger = logging.getLogger(__name__)

Partitions = Dict[KnowledgeState, List[str]]


class Evaluator(ABC):

    def __init__(self,
                 response_patterns: List[str],
                 node_size_penalty: float = 50.0,  # REDUCED from 500 to allow larger structures
                 valid_learning_space_weight: float = 256.0,
                 use_vectorized: bool = True,
                 max_learning_space_size: int = 300,
                 mismatch_penalty: float = 1.0,
                 match_reward: float = 0.0,
                 missing_policy: str = "ignore"):
        self.response_patterns = response_patterns
        self.node_size_penalty = node_size_penalty
        self.valid_learning_space_weight = valid_learning_space_weight
        self.use_vectorized = use_vectorized
        self.max_learning_space_size = max_learning_space_size
        self.mismatch_penalty = float(mismatch_penalty)
        self.match_reward = float(match_reward)
        self.missing_policy = missing_policy
        
        # Konvertuj pattern stringove u numpy array za brže operacije
        # Parse response patterns into value and mask arrays to support missing-aware distance.
        # Allowed symbols per position: '0', '1', and optional '-' (missing).
        if use_vectorized:
            try:
                values = []
                masks = []
                for pattern in response_patterns:
                    v_row = []
                    m_row = []
                    for ch in pattern:
                        if ch == '0' or ch == '1':
                            v_row.append(1 if ch == '1' else 0)
                            m_row.append(1)
                        else:
                            # Missing symbol (e.g. '-') or any other non-binary
                            v_row.append(0)
                            m_row.append(0)
                    values.append(v_row)
                    masks.append(m_row)
                self.pattern_array = np.array(values, dtype=np.uint8)
                self.pattern_mask = np.array(masks, dtype=np.uint8)
                logger.info(
                    f"Vektorisano: pattern_array {self.pattern_array.shape}, mask {self.pattern_mask.shape}, "
                    f"mem {(self.pattern_array.nbytes + self.pattern_mask.nbytes) / 1024**2:.2f}MB")
            except Exception as e:
                logger.warning(f"Vektorisacija nije moguća: {e}. Koristim originalnu verziju.")
                self.use_vectorized = False
                self.pattern_array = None
                self.pattern_mask = None
        else:
            self.pattern_array = None
            self.pattern_mask = None

    @abstractmethod
    def evaluate(self,
                 genomes: List[Tuple[int, LearningSpaceGenome]],
                 config: LearningSpaceGenomeConfig = None) -> None:
        pass

    def _set_fitness(self, genome, discrepancy):
        num_nodes, _ = genome.size()
        
        # Hard limit - ogromna kazna za prevelike learning spaces
        if num_nodes > self.max_learning_space_size:
            genome.fitness = -1e9 - num_nodes * 10000
            return
        
        size_fitness = num_nodes * self.node_size_penalty
        valid_ls_fitness = int(genome.is_valid()) * self.valid_learning_space_weight

        # Larger knowledge structures are penalized, while valid learning spaces
        # have better fitness. Fitness is negative because objective is to
        # maximize fitness.
        genome.fitness = -(discrepancy + size_fitness) + valid_ls_fitness


class ParallelEvaluator(Evaluator):

    # Multiprocessing syncronized Manager dict must be 'global' variable to
    # avoid copy on fork.
    CACHE = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if ParallelEvaluator.CACHE is None:
            ParallelEvaluator.CACHE = mp.Manager().dict()
        self._pool = mp.Pool()

    def __del__(self):
        self._pool.terminate()
        self._pool.join()

    def evaluate(self,
                 genomes: List[Tuple[int, LearningSpaceGenome]],
                 config: LearningSpaceGenomeConfig = None) -> None:
        jobs = [
            self._pool.apply_async(get_discrepancy, (self.response_patterns,
                                                     genome.knowledge_states(),
                                                     self.CACHE,
                                                     self.pattern_array,
                                                     self.pattern_mask,
                                                     self.mismatch_penalty,
                                                     self.match_reward))
            for _, genome in genomes
        ]

        for job, (_, genome) in zip(jobs, genomes):
            discrepancy = job.get()
            self._set_fitness(genome, discrepancy)


class SerialEvaluator(Evaluator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = dict()

    def evaluate(self,
                 genomes: List[Tuple[int, LearningSpaceGenome]],
                 config: LearningSpaceGenomeConfig = None) -> None:
        for _, genome in genomes:
            discrepancy = get_discrepancy(response_patterns=self.response_patterns,
                                          knowledge_states=genome.knowledge_states(),
                                          cache=self._cache,
                                          pattern_array=self.pattern_array,
                                          pattern_mask=self.pattern_mask,
                                          mismatch_penalty=self.mismatch_penalty,
                                          match_reward=self.match_reward)
            self._set_fitness(genome, discrepancy)


def get_discrepancy(response_patterns: List[str],
                    knowledge_states: List[KnowledgeState],
                    cache: dict = None,
                    pattern_array: np.ndarray = None,
                    pattern_mask: np.ndarray = None,
                    mismatch_penalty: float = 1.0,
                    match_reward: float = 0.0) -> float:
    """
    Vrati diskrepanciju iz cache-a ili izračunaj.
    
    Cache ključ je MD5 hash knowledge states-a.
    Ako je pattern_array dostupan, koristi vektorisanu verziju.
    """
    if cache is None:
        return compute_discrepancy(response_patterns, knowledge_states, pattern_array, pattern_mask,
                                   mismatch_penalty, match_reward)

    # Kreiraj ključ od knowledge states
    state_str = ''.join(s.to_bitstring() for s in sorted(
        knowledge_states, 
        key=lambda x: x.to_bitstring()
    ))
    cache_key = hashlib.md5(state_str.encode()).hexdigest()
    
    if cache_key not in cache:
        cache[cache_key] = compute_discrepancy(response_patterns, knowledge_states, pattern_array, pattern_mask,
                                               mismatch_penalty, match_reward)

    return cache[cache_key]


def transform_key(knowledge_states: List[KnowledgeState]) -> Tuple:
    key = np.array([state._bitarray.tolist()
                    for state in knowledge_states], dtype=np.bool).sum(axis=0)
    return (len(knowledge_states),) + tuple(key)


def compute_discrepancy(response_patterns: List[str],
                        knowledge_states: List[KnowledgeState],
                        pattern_array: np.ndarray = None,
                        pattern_mask: np.ndarray = None,
                        mismatch_penalty: float = 1.0,
                        match_reward: float = 0.0) -> float:
    """
    Izračunaj diskrepanciju između learning space-a i observed response pattern-a.
    
    Ako je pattern_array dostupan, koristi vektorisanu verziju (50-100x brža).
    """
    if pattern_array is not None and len(knowledge_states) > 0:
        return _compute_discrepancy_vectorized(pattern_array, knowledge_states,
                                               pattern_mask=pattern_mask,
                                               mismatch_penalty=mismatch_penalty,
                                               match_reward=match_reward)
    
    # Fallback na originalnu verziju
    # Non-vectorized, missing-aware computation.
    # Build numpy arrays lazily from strings
    values = []
    masks = []
    for pattern in response_patterns:
        v_row = []
        m_row = []
        for ch in pattern:
            if ch in ('0', '1'):
                v_row.append(1 if ch == '1' else 0)
                m_row.append(1)
            else:
                v_row.append(0)
                m_row.append(0)
        values.append(v_row)
        masks.append(m_row)
    values = np.array(values, dtype=np.uint8)
    masks = np.array(masks, dtype=np.uint8)

    total = 0.0
    # Precompute state arrays
    state_array = np.array([[int(c) for c in s.to_bitstring()] for s in knowledge_states], dtype=np.uint8)
    for r in range(values.shape[0]):
        v = values[r]
        m = masks[r]
        # distances for this response to all states
        mismatches = np.sum(((state_array != v) & (m == 1)), axis=1)
        matches = np.sum(((state_array == v) & (m == 1)), axis=1)
        loss = mismatches * mismatch_penalty - matches * match_reward
        total += float(np.min(loss))
    return total


def _compute_discrepancy_vectorized(pattern_array: np.ndarray,
                                   knowledge_states: List[KnowledgeState],
                                   pattern_mask: np.ndarray = None,
                                   mismatch_penalty: float = 1.0,
                                   match_reward: float = 0.0) -> float:
    """
    Vektorisana verzija diskrepancije - procesira u batch-ovima da izbegne memory error.
    
    Koristi numpy operacije umesto Python petlji.
    Očekivani speedup: 50-100x za velike datasets.
    """
    if not knowledge_states:
        return float('inf')
    
    n_states = len(knowledge_states)
    n_items = len(knowledge_states[0].to_bitstring())
    n_patterns = len(pattern_array)
    
    # Konvertuj knowledge states u numpy array
    state_array = np.zeros((n_states, n_items), dtype=np.uint8)
    for i, state in enumerate(knowledge_states):
        state_array[i] = np.fromiter(
            (int(c) for c in state.to_bitstring()), 
            dtype=np.uint8
        )
    
    # Procesuj u batch-ovima da izbegnemo memory overflow
    # Max memory: ~100MB po batch-u
    max_memory_mb = 100
    bytes_per_elem = 1  # bool
    batch_size = max(1, int(max_memory_mb * 1024 * 1024 / (n_states * n_items * bytes_per_elem)))
    batch_size = min(batch_size, n_patterns)
    
    total_discrepancy = 0.0
    for i in range(0, n_patterns, batch_size):
        batch_end = min(i + batch_size, n_patterns)
        batch_patterns = pattern_array[i:batch_end]
        if pattern_mask is not None:
            mask_batch = pattern_mask[i:batch_end]
        else:
            mask_batch = np.ones_like(batch_patterns, dtype=np.uint8)

        # Compute mismatches and matches only on observed positions
        # Shapes: (batch, states, items)
        neq = (batch_patterns[:, np.newaxis, :] != state_array[np.newaxis, :, :]) & (mask_batch[:, np.newaxis, :] == 1)
        eq = (batch_patterns[:, np.newaxis, :] == state_array[np.newaxis, :, :]) & (mask_batch[:, np.newaxis, :] == 1)

        mismatches = np.sum(neq, axis=2)
        matches = np.sum(eq, axis=2)
        loss = mismatches * mismatch_penalty - matches * match_reward
        min_loss = np.min(loss, axis=1)
        total_discrepancy += float(np.sum(min_loss))
    
    return float(total_discrepancy)


def partition(response_patterns: List[str],
              knowledge_states: List[KnowledgeState]) -> Partitions:
    partitions = defaultdict(list)
    for response in response_patterns:
        centroid = min(knowledge_states,
                       key=lambda state: _state_distance(state, response))
        partitions[centroid].append(response)
    return partitions


def _state_distance(state: KnowledgeState, response_pattern: str) -> int:
    """Returns bit distance between knowledge state and response pattern."""
    bitarray = (state ^ KnowledgeState(response_pattern))._bitarray
    return sum(bitarray)


def get_partition_value(response_pattern: str,
                        knowledge_state: KnowledgeState,
                        partition_dict: Partitions) -> int:
    response_patterns = partition_dict.get(knowledge_state, [])
    return sum(1 for pattern in response_patterns if pattern == response_pattern)
