"""Simple CLI entrypoint to run train or build subcommands.

Usage: python -m learning_space_generator.cli.main train ...
       python -m learning_space_generator.cli.main build ...
"""
import sys
from argparse import ArgumentParser

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print('Usage: python -m learning_space_generator.cli.main <train|build> [args]')
        return
    cmd = argv[0]
    subargs = argv[1:]
    if cmd == 'train':
        from . import train
        train.main(subargs)
    elif cmd == 'build':
        from . import build
        build.main(subargs)
    else:
        print('Unknown command:', cmd)


if __name__ == '__main__':
    main()
