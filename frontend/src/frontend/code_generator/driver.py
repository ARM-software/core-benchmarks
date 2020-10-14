"""Generate source files from provided callgraph."""
#!/usr/bin/python3

import argparse
from frontend.code_generator import source_generator
from frontend.code_generator import user_callgraph

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('callgraph', type=str, help='path to cfg protobuf')
    parser.add_argument('output_dir',
                        type=str,
                        help='directory to output c/source files to')
    parser.add_argument('--num-files',
                        default=None,
                        type=int,
                        help='number of c files to write to')
    args = parser.parse_args()
    callgraph = user_callgraph.Callgraph.from_proto(args.callgraph)
    sg = source_generator.SourceGenerator(args.output_dir, callgraph)
    sg.write_files(args.num_files)
