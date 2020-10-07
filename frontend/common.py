"""Common classes for generating benchmarks."""

import cfg_pb2

class IDGenerator(object):
  """Returns an unused integer as a unique ID."""
  next_id = 0

  def Next():
    """Get the next ID."""
    IDGenerator.next_id += 1
    return IDGenerator.next_id


class BaseGenerator(object):
  """Common functionality for generating benchmarks."""

  def __init__(self):
    # Map from code block body ID to the CodeBlockBody proto.
    self._code_block_bodies = {}
    # Map from code block ID to the CodeBlock proto.
    self._code_blocks = {}
    # Map from function ID to the function proto.
    self._functions = {}


  def _AddCodeBlockBody(self, code):
    id = IDGenerator.Next()
    self._code_block_bodies[id] = cfg_pb2.CodeBlockBody(
        id=id, instructions=code)
    return self._code_block_bodies[id]


  def _AddCodeBlock(self):
    id = IDGenerator.Next()
    self._code_blocks[id] = cfg_pb2.CodeBlock(id=id)
    return self._code_blocks[id]


  def _FunctionName(self, function_id):
    return 'function_%d' % function_id


  def _AddFunction(self, id):
    if id in self._functions:
      raise KeyError('there already exists a function with id %d' % id)
    self._functions[id] = cfg_pb2.Function(id=id)
    signature = 'void %s' % self._FunctionName(id)
    sig_body = self._AddCodeBlockBody(signature)
    self._functions[id].signature.code_block_body_id = sig_body.id
    return self._functions[id]
