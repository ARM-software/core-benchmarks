.PHONY: all test lint clean init update-deps install

PROTO_DIR = src/frontend/proto
TEST_DIR = src/frontend/cfg_generator
VPATH = $(PROTO_DIR)
PROTOS = cfg.proto
PY_PROTOS = $(patsubst %.proto, %_pb2.py, $(PROTOS))
PYI_PROTOS = $(addsuffix i, $(PY_PROTOS))

%_pb2.py: %.proto
	protoc --python_out=. --mypy_out=. $^

all: $(PY_PROTOS)

test: all
	pytest tests/unit/

lint: all
	pylint src/frontend tests/unit/*.py
	mypy src/frontend  tests/unit/*.py
	yapf --style=google -r src/frontend tests/ -q -p -e *pb2.py

install:
	pip install --editable .

update-deps:
	pip install pip-tools
	pip-compile --upgrade --generate-hashes --output-file requirements.txt requirements.in

init: update-deps install
	pip install --upgrade -r requirements.txt

clean:
	-rm -f $(addprefix $(PROTO_DIR)/, $(PY_PROTOS))
	-rm -f $(addprefix $(PROTO_DIR)/, $(PYI_PROTOS))
