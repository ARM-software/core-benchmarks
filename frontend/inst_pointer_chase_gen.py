"""Generates an instruction pointer-chase benchmark."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random

import cfg_pb2, common

MODULE_NAME = 'inst_pointer_chase_gen'

def register_args(parser):
  subparser = parser.add_parser(MODULE_NAME)
  subparser.add_argument('--depth', default=20, type=int,
                         help='Depth of each callchain.')
  subparser.add_argument('--num_callchains', default=1000, type=int,
                         help='Number of distinct callchains.')


def _PopRandomFunction(function_list):
  if not function_list:
    raise IndexError('in _PopRandomFunction: list of functions is empty')
  idx = int(random.random() * len(function_list))
  return function_list.pop(idx)

# Indicates in the caller-to-callee mapping that a function does not call any
# other function.
NO_CALLEE = -1

class InstPointerChaseGenerator(common.BaseGenerator):
  """Generates an instruction pointer chase benchmark."""

  def __init__(self, depth, num_callchains, function_selector=None):
    super().__init__()
    self._depth = depth
    self._num_callchains = num_callchains
    self._caller2callee = {}
    self._callchain_entry_functions = []
    self._entry_function_id = None
    if function_selector is None:
      self._function_selector = _PopRandomFunction
    else:
      self._function_selector = function_selector
    self._function_body = self._AddCodeBlockBody(
        'int x = 1;\n'
        'int y = x*x + 3;\n'
        'int z = y*x + 12345;\n'
        'int w = z*z + x - y;\n'
    )


  def _GenerateCallchainMappings(self):
    num_functions = self._num_callchains * self._depth
    function_list = list(range(0, num_functions))
    for c in range(0, self._num_callchains):
      # Generate a pointer chase. The final function will just return.
      caller = self._function_selector(function_list)
      self._callchain_entry_functions.append(caller)
      for d in range(0, self._depth-1):
        callee = self._function_selector(function_list)
        self._caller2callee[caller] = callee
        caller = callee
      # The final function in the chain does not call.
      self._caller2callee[caller] = NO_CALLEE

    assert len(self._caller2callee) == num_functions, (
           'There should be exactly one caller2callee mapping for every '
           'function.')


  def _GenerateCallchainFunctions(self):
    # First, generate codeblocks. Each function has two: the main body, with a
    # fallthrough branch, and the call, with a return terminator branch.

    for caller, callee in self._caller2callee.items():
      function = self._AddFunction(caller)
      main_body = self._AddCodeBlock()
      main_body.code_block_body_id = self._function_body.id
      main_body.terminator_branch.type = cfg_pb2.Branch.BranchType.FALLTHROUGH
      function.instructions.append(main_body)

      if not callee == NO_CALLEE:
        call_block = self._AddCodeBlock()
        # Leave the branch target unspecified for now.
        call_block.terminator_branch.type = (
            cfg_pb2.Branch.BranchType.DIRECT_CALL)
        call_block.terminator_branch.targets.append(callee)
        call_block.terminator_branch.taken_probability.append(1)
        # The end of a function in C will implicitly return, no need to create
        # another CodeBlock.
        function.instructions.append(call_block)


  def _GenerateEntryFunction(self):
    entry_func = self._AddFunction(common.IDGenerator.Next())
    for callchain_start in self._callchain_entry_functions:
      # Get the first CodeBlock of the called function.
      called_func = self._functions[callchain_start]
      # Create a CodeBlock that just calls this function (the start of a
      # callchain), no additional CodeBlockBody required.
      code_block = self._AddCodeBlock()
      code_block.terminator_branch.type = cfg_pb2.Branch.BranchType.DIRECT_CALL
      code_block.terminator_branch.targets.append(called_func.id)
      code_block.terminator_branch.taken_probability.append(1)
      entry_func.instructions.append(code_block)
    self._entry_function_id = entry_func.id;


  def GenerateCFG(self):
    self._GenerateCallchainMappings()
    self._GenerateCallchainFunctions()
    self._GenerateEntryFunction()
    cfg_proto = cfg_pb2.CFG()
    for func in self._functions.values():
      cfg_proto.functions.append(func)
    for cb in self._code_block_bodies.values():
      cfg_proto.code_block_bodies.append(cb)
    cfg_proto.entry_point_function = self._entry_function_id
    return cfg_proto


def generate_cfg(args):
  """Generate a CFG of arbitrary callchains."""
  print("Generating instruction pointer chase benchmark...")
  generator = InstPointerChaseGenerator(args.depth, args.num_callchains)
  return generator.GenerateCFG()
