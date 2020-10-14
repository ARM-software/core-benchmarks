.PHONY: all test clean

PROTO_DIR = src/frontend/proto
TEST_DIR = src/frontend/cfg_generator
VPATH = $(PROTO_DIR)
PROTOS = cfg.proto
PY_PROTOS = $(patsubst %.proto, %_pb2.py, $(PROTOS))
PYI_PROTOS = $(addsuffix i, $(PY_PROTOS))

PY_TESTS = dfs_chase_gen_test.py \
	   inst_pointer_chase_gen_test.py

%_pb2.py: %.proto
	protoc --python_out=. --mypy_out=. $^

all: $(PY_PROTOS)

test: all
	@for t in $(addprefix $(TEST_DIR)/, $(PY_TESTS)); do \
		echo Running $$t...; \
		python3 $$t; \
	done;

clean:
	-rm -f $(addprefix $(PROTO_DIR)/, $(PY_PROTOS))
	-rm -f $(addprefix $(PROTO_DIR)/, $(PYI_PROTOS))
