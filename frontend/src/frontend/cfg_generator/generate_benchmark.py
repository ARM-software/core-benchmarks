"""Generates a frontend benchmark.

Usage:
  python3 generate_benchmark.py [cfg_type] [cfg_options] output_filename

Example: to generate an instruction pointer chase:
  python3 generate_benchmark.py inst_pointer_chase_gen \
      --depth=10 --num_callchains=10 /tmp/ichase.pb
"""

import argparse

import inst_pointer_chase_gen as ichase_gen
import dfs_chase_gen


def main():
    parser = argparse.ArgumentParser('Control flow graph generator.')
    subparsers = parser.add_subparsers(
        title='CFG type',
        description='Individual options per CFG type',
        dest='cfg_type')
    ichase_gen.register_args(subparsers)
    dfs_chase_gen.register_args(subparsers)
    parser.add_argument('output_filename',
                        default='/tmp/cfg.pbtxt',
                        help='Output textproto file location.')
    args = parser.parse_args()

    if args.cfg_type == ichase_gen.MODULE_NAME:
        cfg = ichase_gen.generate_cfg(args)
    elif args.cfg_type == dfs_chase_gen.MODULE_NAME:
        cfg = dfs_chase_gen.generate_cfg(args)
    else:
        raise ValueError('Invalid CFG type: %s' % args.cfg_type)

    if args.output_filename.endswith('.pbtxt'):
        with open(args.output_filename, 'w') as f:
            f.write(str(cfg))
    elif args.output_filename.endswith('.pb'):
        with open(args.output_filename, 'wb') as f:
            f.write(cfg.SerializeToString())
    else:
        raise ValueError('Unknown output file extension %s' %
                         args.output_filename)


if __name__ == '__main__':
    main()
