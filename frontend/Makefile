.PHONY: all test

PROTOS = cfg.proto
PY_PROTOS = $(patsubst %.proto, %_pb2.py, $(PROTOS))

PY_SRCS = common.py \
	  dfs_chase_gen.py \
	  generate_benchmark.py \
	  inst_pointer_chase_gen.py

PY_TESTS = dfs_chase_gen_test.py \
	   inst_pointer_chase_gen_test.py

%_pb2.py: %.proto
	protoc --python_out=. $^

all: $(PY_PROTOS)

test: all
	@for t in $(PY_TESTS); do \
		echo Running $$t...; \
		python3 $$t; \
	done;
