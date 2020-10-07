"""Tests for inst_pointer_chase_gen."""

from __future__ import absolute_import  # Not necessary in a Python 3-only module
from __future__ import division  # Not necessary in a Python 3-only module
from __future__ import print_function  # Not necessary in a Python 3-only module

import random
import unittest

import inst_pointer_chase_gen, cfg_pb2


def _PopNextFunction(function_list):
  """Pops and returns the next function in the list."""
  if not function_list:
    raise IndexError("in _PopNextFunction: list of functions is empty")
  return function_list.pop(0)


class InstPointerChaseGeneratorTest(unittest.TestCase):


  def setUp(self):
    self.depth = 3
    self.num_callchains = 2
    self.gen = inst_pointer_chase_gen.InstPointerChaseGenerator(
        self.depth, self.num_callchains, function_selector=_PopNextFunction)


  def test_generate_callchain_mappings(self):
    self.gen._GenerateCallchainMappings()
    self.assertEqual(self.gen._caller2callee[0], 1)
    self.assertEqual(self.gen._caller2callee[1], 2)
    self.assertEqual(self.gen._caller2callee[2],
                     inst_pointer_chase_gen.NO_CALLEE)
    self.assertEqual(self.gen._caller2callee[3], 4)
    self.assertEqual(self.gen._caller2callee[4], 5)
    self.assertEqual(self.gen._caller2callee[5],
                     inst_pointer_chase_gen.NO_CALLEE)


  def test_generate_callchain_functions(self):
    self.gen._GenerateCallchainMappings()
    self.gen._GenerateCallchainFunctions()
    self.assertEqual(len(self.gen._functions), self.depth * self.num_callchains)
    # Map from a caller function to its callee in the chain.
    expected_caller2callee = { 0: 1, 1: 2, 3: 4, 4: 5 }

    # All functions should use the same main code block body.
    code_block_bodies = set()
    for func_id, func in self.gen._functions.items():
      code_block_bodies.add(func.instructions[0].code_block_body_id)
      sig_body = (
          self.gen._code_block_bodies[func.signature.code_block_body_id])
      self.assertIn(self.gen._FunctionName(func_id),
                    sig_body.instructions)
      self.assertEqual(func.instructions[0].terminator_branch.type,
                       cfg_pb2.Branch.BranchType.FALLTHROUGH)
      if func_id in expected_caller2callee:
        # This function calls another in a chain.
        self.assertEqual(len(func.instructions), 2)
        self.assertEqual(func.instructions[1].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.DIRECT_CALL)
        expected_callee_func = (
            self.gen._functions[expected_caller2callee[func_id]])
        self.assertEqual(
            func.instructions[1].terminator_branch.targets[0],
            expected_callee_func.id,
            msg="Function %d should call function %d, got %d" % (
                func_id, expected_callee_func.id,
                func.instructions[1].terminator_branch.targets[0]))
        self.assertEqual(
            func.instructions[1].terminator_branch.taken_probability[0], 1)
      else:
        self.assertEqual(len(func.instructions), 1)
    self.assertEqual(
        len(code_block_bodies), 1,
        msg="All functions should share the same main code block body.")


  def test_generate_entry_function(self):
    self.gen._GenerateCallchainMappings()
    self.gen._GenerateCallchainFunctions()
    self.gen._GenerateEntryFunction()
    entry_func = self.gen._functions[self.gen._entry_function_id]
    entry_func_sig = self.gen._code_block_bodies[
        entry_func.signature.code_block_body_id]
    self.assertIn(self.gen._FunctionName(entry_func.id),
                  entry_func_sig.instructions)
    self.assertEqual(len(entry_func.instructions), self.num_callchains)
    for code_block in entry_func.instructions:
      self.assertEqual(code_block.terminator_branch.type,
                       cfg_pb2.Branch.BranchType.DIRECT_CALL)
      self.assertEqual(code_block.terminator_branch.type,
                       cfg_pb2.Branch.BranchType.DIRECT_CALL)
      self.assertIn(code_block.terminator_branch.targets[0],
                    self.gen._functions)
      self.assertEqual(
          code_block.terminator_branch.taken_probability[0], 1)


  def test_generate_cfg(self):
    cfg = self.gen.GenerateCFG()
    # +1 accounts for the entry function.
    num_total_functions = self.depth * self.num_callchains+1
    self.assertEqual(len(cfg.functions), num_total_functions)
    # Each function adds a code block body to store its signature, and all
    # functions share the same main code block body.
    self.assertEqual(len(cfg.code_block_bodies), num_total_functions + 1)


if __name__ == '__main__':
  unittest.main()
