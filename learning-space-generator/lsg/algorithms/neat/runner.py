"""
NEAT Algorithm Runner

This module contains the main execution logic for running NEAT algorithm
to generate learning spaces.
"""

import logging
from typing import List, TYPE_CHECKING

import neat

from .genome import LearningSpaceGenome

if TYPE_CHECKING:
    from .evaluation import ParallelEvaluator, SerialEvaluator
    from .reporting import (EarlyStoppingReporter, FitnessTerminationReporter,
                            TqdmReporter, PlotReporter,
                            EarlyStoppingException, TerminationThresholdReachedException)

logger = logging.getLogger(__name__)


def run_neat(generations: int,
             config_filename: str,
             responses: List[str],
             early_stopping_patience: int,
             verbose: bool = False,
             plot_best: bool = False,
             parallel: bool = False,
             is_greedy: bool = False) -> LearningSpaceGenome:
    """
    Run NEAT algorithm to generate learning space.
    
    Args:
        generations: Number of generations to run (None for unlimited in greedy mode)
        config_filename: Path to NEAT config file
        responses: List of student response patterns (binary strings)
        early_stopping_patience: Stop if no improvement for N generations
        verbose: Enable progress reporting
        plot_best: Plot best genome evolution
        parallel: Use parallel evaluation
        is_greedy: Greedy mode (unlimited generations)
        
    Returns:
        Best LearningSpaceGenome found
    """
    # Import here to avoid circular dependency
    from .reporting import (EarlyStoppingReporter, FitnessTerminationReporter,
                            TqdmReporter, PlotReporter,
                            EarlyStoppingException, TerminationThresholdReachedException)
    from .evaluation import ParallelEvaluator, SerialEvaluator
    
    config = neat.Config(LearningSpaceGenome,
                         neat.DefaultReproduction,
                         neat.DefaultSpeciesSet,
                         neat.DefaultStagnation,
                         config_filename)

    population = neat.Population(config)

    early_stopper = EarlyStoppingReporter(patience=early_stopping_patience,
                                          is_greedy=is_greedy)
    population.add_reporter(early_stopper)

    fitness_term_stopper = FitnessTerminationReporter(threshold=-0.5)
    population.add_reporter(fitness_term_stopper)

    if verbose:
        tqdm_reporter = TqdmReporter(total_generations=generations)
        population.add_reporter(tqdm_reporter)

    if plot_best:
        plot_reporter = PlotReporter()
        population.add_reporter(plot_reporter)

    if parallel:
        evaluator = ParallelEvaluator(responses)
    else:
        evaluator = SerialEvaluator(responses)

    try:
        optimal_ls = population.run(evaluator.evaluate, generations)
    except EarlyStoppingException as exception:
        optimal_ls = exception.best_genome

        if verbose:
            # Explicitly close tqdm progress bar to fix printing to stdout.
            tqdm_reporter.close()

        if is_greedy:
            print('\nGreedy algorithm constructed learning space successfully.')
        else:
            print('\nNo fitness improvement '
                  'for {} generations.'.format(early_stopping_patience))
    except TerminationThresholdReachedException as exception:
        optimal_ls = exception.best_genome

        if verbose:
            # Explicitly close tqdm progress bar to fix printing to stdout.
            tqdm_reporter.close()

        print('\nTermination threshold reached. '
              'Found genome with {} discrepancy'.format(optimal_ls.discrepancy()))

    return optimal_ls
