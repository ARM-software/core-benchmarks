# Frontend
![Python package](https://github.com/ARM-software/core-benchmarks/workflows/Python%20package/badge.svg?branch=main&event=push)

## About
Frontend python module is designed to produce a benchmark that stresses the frontend of a processor. Frontend consists of a callgraph generator and a code generator.

Frontend supports python versions 3.7 and up.

### Callgraph Generator
The callgraph generator generates the desired control flow graph (CFG). Each node in the graph is a function. CFGs can be described by a small number of parameters -- average depth, average width at each level, presence/lack of intra-function control flow.

CFGs are represented as a protobuf. See `src/frontend/proto/cfg.proto` for the definition.

### Code Generator
The code generator takes a CFG protobuf as input, and produces a set of .c files and a Makefile. Running `make` on the makefile will produce the frontend benchmark.

## Using

Install pip packages and build the protocol buffer libraries. Recommended to use virtualenv.

    $ make init
    $ make all

Generate the cfg protobuf. First argument is what generator to use.

    $ python3 -m frontend.cfg_generator.generate_benchmark
    e.g.
    $ python3 -m frontend.cfg_generator.generate_benchmark dfs_chase_gen --depth 10 cfg.pb

Generate C code from cfg protobuf.

    $ mkdir output
    $ python3 -m frontend.code_generator.driver --num-files=24 cfg.pb output

Compile benchmark.

    $ cd output
    $ make

## Installation

### Required Packages
#### Ubuntu 18.04, 20.04
    $ apt install gcc make protobuf-compiler

### Pip Setup
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ make init

## Contributing
- Create an Issue for your work if one does not already exist. This gives everyone visibility of whether others are working on something similar.
- Create a pull request from your fork to the `main` branch of this repo
- If a commit fixes a GitHub issue, include a reference; this ensures the issue is automatically closed when merged into the core-benchmarks `main` branch.

### Testing
- All tests must pass before merging.
- All-in-one testing command: `make test`.
- New tests must be created using the pytest framework and placed under the tests/ directory.

### Style
- Follow the Google Python style guideline: https://google.github.io/styleguide/pyguide.html
- All-in-one linting command: `make lint`.
- Lint your code using pylint and mypy.
- Include type annotations in your code.
- Format your code using `yapf --style=google`. The `-i` flag can be used to modify your code in place.
