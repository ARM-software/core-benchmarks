"""Tests for dfs_chase_gen."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import unittest

import cfg_pb2, dfs_chase_gen


class DFSChaseGenTest(unittest.TestCase):

  def setUp(self):
    self.depth = 3
    self.branch_probability = 0.5
    self.gen = dfs_chase_gen.DFSChaseGenerator(
        self.depth, self.branch_probability)


  def test_generate_function_tree(self):
    self.gen._GenerateFunctionTree()
    self.assertEqual(len(self.gen._function_tree), 2**(self.depth-1) - 1)
    for caller, children in self.gen._function_tree.items():
      if children:
        self.assertEqual(len(children), 2)

  def test_generate_conditional_branch_code_blocks(self):
    callees = [2, 3]  # Function IDs.
    codeblock, ft_block, ft_block_ret, taken_block, taken_block_ret = \
        self.gen._GenerateConditionalBranchCodeBlocks(
            callees, self.branch_probability)
    self.assertEqual(codeblock.terminator_branch.type,
                     cfg_pb2.Branch.BranchType.CONDITIONAL_DIRECT)
    self.assertEqual(codeblock.terminator_branch.targets, [taken_block.id])
    self.assertEqual(codeblock.terminator_branch.taken_probability,
                     [self.branch_probability])

    self.assertEqual(taken_block.terminator_branch.type,
                     cfg_pb2.Branch.BranchType.DIRECT_CALL)
    self.assertEqual(taken_block.terminator_branch.targets, [callees[0]])

    self.assertEqual(ft_block.terminator_branch.type,
                     cfg_pb2.Branch.BranchType.DIRECT_CALL)
    self.assertEqual(ft_block.terminator_branch.targets, [callees[1]])

    self.assertEqual(taken_block_ret.terminator_branch.type,
                     cfg_pb2.Branch.BranchType.RETURN)
    self.assertEqual(ft_block_ret.terminator_branch.type,
                     cfg_pb2.Branch.BranchType.RETURN)


  def test_generate_functions(self):
    self.gen._GenerateFunctionTree()
    self.gen._GenerateFunctions()
    self.assertEqual(len(self.gen._functions), 2**(self.depth)-1)
    for func_id, func in self.gen._functions.items():
      if func_id in self.gen._function_tree:
        # Functions that call other functions have 5 call blocks.
        self.assertEqual(len(func.instructions), 5)
      else:
        # Leaf functions have just one.
        self.assertEqual(len(func.instructions), 1)

  def test_generate_cfg(self):
    cfg = self.gen.GenerateCFG()
    self.assertEqual(cfg.entry_point_function, self.gen._root_func)
    self.assertEqual(len(cfg.functions), len(self.gen._functions))
    for got_func in cfg.functions:
      self.assertEqual(got_func, self.gen._functions[got_func.id])
    # One codeblockbody per function signature and the shared code block body
    # for all functions.
    expected_codeblock_bodies = len(self.gen._functions) + 1
    self.assertEqual(len(cfg.code_block_bodies), expected_codeblock_bodies)


if __name__ == '__main__':
  unittest.main()
