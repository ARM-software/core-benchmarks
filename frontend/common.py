"""Common classes for generating benchmarks."""

import random
import cfg_pb2


class IDGenerator(object):
    """Returns an unused integer as a unique ID."""
    next_id = 0

    @staticmethod
    def next():
        """Get the next ID."""
        IDGenerator.next_id += 1
        return IDGenerator.next_id


def pop_random_element(somelist):
    """Pop off a random element from the list."""
    if not somelist:
        raise IndexError('PopRandomFunction: list is empty')
    idx = random.randrange(0, len(somelist))
    return somelist.pop(idx)


class BaseGenerator(object):
    """Common functionality for generating benchmarks."""

    def __init__(self):
        # Map from code block body ID to the CodeBlockBody proto.
        self._code_block_bodies = {}
        # Map from code block ID to the CodeBlock proto.
        self._code_blocks = {}
        # Map from function ID to the function proto.
        self._functions = {}

    def function_name(self, function_id):
        return 'function_%d' % function_id

    def _add_code_block_body(self, code):
        next_id = IDGenerator.next()
        self._code_block_bodies[next_id] = cfg_pb2.CodeBlockBody(
            id=next_id, instructions=code)
        return self._code_block_bodies[next_id]

    def _add_code_block(self):
        next_id = IDGenerator.next()
        self._code_blocks[next_id] = cfg_pb2.CodeBlock(id=next_id)
        return self._code_blocks[next_id]

    def _add_function_with_id(self, next_id):
        if next_id in self._functions:
            raise KeyError('there already exists a function with id %d' %
                           next_id)
        self._functions[next_id] = self._create_function_with_signature(next_id)
        return self._functions[next_id]

    def _create_function_with_signature(self, next_id):
        func = cfg_pb2.Function(id=next_id)
        signature = 'void %s' % self.function_name(next_id)
        sig_body = self._add_code_block_body(signature)
        func.signature.code_block_body_id = sig_body.id
        return func

    def _generate_cfg(self, functions, code_block_bodies, entry_func_id):
        cfg_proto = cfg_pb2.CFG()
        for func in functions.values():
            cfg_proto.functions.append(func)
        for cb in code_block_bodies.values():
            cfg_proto.code_block_bodies.append(cb)
        cfg_proto.entry_point_function = entry_func_id
        return cfg_proto
