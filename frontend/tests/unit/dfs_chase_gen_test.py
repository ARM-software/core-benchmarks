"""Tests for dfs_chase_gen."""
# Access to protected class members is common for unit tests.
# pylint: disable=protected-access

from frontend.proto import cfg_pb2
from frontend.cfg_generator import dfs_chase_gen
import unittest


class DirectCallDFSChaseGenTest(unittest.TestCase):

    def setUp(self):
        self.depth = 3
        self.branch_probability = 0.5
        self.gen = dfs_chase_gen.DFSChaseGenerator(self.depth, False,
                                                   self.branch_probability,
                                                   False)

    def test_generate_function_tree(self):
        self.gen._generate_function_tree()
        # A full binary tree of depth N has 2^n-1 nodes. function_tree only
        # includes functions that call others, so the leaves in the last layer
        # of the tree are excluded. Hence the expected number of nodes is
        # 2^(n-1) - 1.
        self.assertEqual(len(self.gen._function_tree), 2**(self.depth - 1) - 1)
        for children in self.gen._function_tree.values():
            if children:
                self.assertEqual(len(children), 2)

    def test_generate_conditional_branch_code_blocks(self):
        callees = [2, 3]  # Function IDs.
        code_blocks = self.gen._generate_conditional_branch_code_blocks(
            callees, self.branch_probability)
        self.assertEqual(len(code_blocks), 5)

        cond_block = code_blocks[0]
        ft_block = code_blocks[1]
        ft_block_ret = code_blocks[2]
        taken_block = code_blocks[3]
        taken_block_ret = code_blocks[4]

        self.assertEqual(cond_block.terminator_branch.type,
                         cfg_pb2.Branch.BranchType.CONDITIONAL_DIRECT)
        self.assertEqual(cond_block.code_block_body_id,
                         self.gen._function_body.id)
        self.assertEqual(cond_block.terminator_branch.targets, [taken_block.id])
        self.assertEqual(cond_block.terminator_branch.taken_probability,
                         [self.branch_probability])

        self.assertEqual(ft_block.terminator_branch.targets, [callees[1]])
        self.assertEqual(ft_block_ret.terminator_branch.type,
                         cfg_pb2.Branch.BranchType.RETURN)

        self.assertEqual(ft_block.terminator_branch.type,
                         cfg_pb2.Branch.BranchType.DIRECT_CALL)
        self.assertEqual(taken_block_ret.terminator_branch.type,
                         cfg_pb2.Branch.BranchType.RETURN)

    def test_generate_functions(self):
        self.gen._generate_function_tree()
        self.gen._generate_functions()
        self.assertEqual(len(self.gen._functions), 2**(self.depth) - 1)
        for func_id, func in self.gen._functions.items():
            if func_id in self.gen._function_tree:
                # Functions that call other functions have 5 call blocks.
                self.assertEqual(len(func.instructions), 5)
            else:
                # Leaf functions have just one.
                self.assertEqual(len(func.instructions), 1)
                self.assertEqual(func.instructions[0].code_block_body_id,
                                 self.gen._function_body.id)

    def test_generate_cfg(self):
        cfg = self.gen.generate_cfg()
        self.assertEqual(cfg.entry_point_function, self.gen._root_func)
        self.assertEqual(len(cfg.functions), len(self.gen._functions))
        for got_func in cfg.functions:
            self.assertEqual(got_func, self.gen._functions[got_func.id])
        # One CodeBlockBody per function signature and the shared code block
        # body for all functions.
        expected_codeblock_bodies = len(self.gen._functions) + 1
        self.assertEqual(len(cfg.code_block_bodies), expected_codeblock_bodies)


class IndirectCallDFSChaseGenTest(unittest.TestCase):

    def setUp(self):
        self.depth = 3
        self.branch_probability = 0.5
        self.gen = dfs_chase_gen.DFSChaseGenerator(
            self.depth,
            True,  # use_indirect_calls
            self.branch_probability,
            False  # insert_code_prefetches
        )

    def test_generate_indirect_call_code_block(self):
        callee_funcs = [2, 3]
        callee_probability = 0.6
        blocks = self.gen._generate_indirect_call_code_blocks(
            callee_funcs, callee_probability)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.INDIRECT_CALL)
        self.assertEqual(blocks[0].terminator_branch.targets, callee_funcs)
        self.assertEqual(blocks[0].code_block_body_id,
                         self.gen._function_body.id)
        self.assertAlmostEqual(blocks[0].terminator_branch.taken_probability[0],
                               0.6)
        self.assertAlmostEqual(blocks[0].terminator_branch.taken_probability[1],
                               0.4)


class CodePrefetchDirectCallDFSChaseGenTest(unittest.TestCase):

    def setUp(self):
        self.depth = 3
        self.branch_probability = 0.5
        self.gen = dfs_chase_gen.DFSChaseGenerator(
            self.depth,
            False,  # use_indirect_calls
            self.branch_probability,
            True,  # insert_code_prefetches
        )

    def test_dfs_graph_contains_code_prefetches(self):
        callees = [2, 3]  # Function IDs.
        code_blocks = self.gen._generate_conditional_branch_code_blocks(
            callees, self.branch_probability)

        # We should have two additional code prefetch code blocks at the start.
        self.assertEqual(len(code_blocks), 7)
        first_pf_body = self.gen._code_block_bodies[
            code_blocks[0].code_block_body_id]
        self.assertEqual(first_pf_body.code_prefetch.type,
                         cfg_pb2.CodePrefetchInst.TargetType.FUNCTION)
        self.assertEqual(first_pf_body.code_prefetch.degree, 1)
        self.assertEqual(first_pf_body.code_prefetch.target_id, callees[0])
        second_pf_body = self.gen._code_block_bodies[
            code_blocks[1].code_block_body_id]
        self.assertEqual(second_pf_body.code_prefetch.type,
                         cfg_pb2.CodePrefetchInst.TargetType.FUNCTION)
        self.assertEqual(second_pf_body.code_prefetch.degree, 1)
        self.assertEqual(second_pf_body.code_prefetch.target_id, callees[1])

        # Everything else afterwards should be the same as without code
        # prefetches inserted. Do a quick check of these.
        self.assertEqual(code_blocks[2].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.CONDITIONAL_DIRECT)
        self.assertEqual(code_blocks[3].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.DIRECT_CALL)
        self.assertEqual(code_blocks[4].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.RETURN)
        self.assertEqual(code_blocks[5].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.DIRECT_CALL)
        self.assertEqual(code_blocks[6].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.RETURN)


class CodePrefetchIndirectCallDFSChaseGenTest(unittest.TestCase):

    def setUp(self):
        self.depth = 3
        self.branch_probability = 0.5
        self.gen = dfs_chase_gen.DFSChaseGenerator(
            self.depth,
            True,  # use_indirect_calls
            self.branch_probability,
            True  # insert_code_prefetches
        )

    def test_dfs_graph_contains_code_prefetches(self):
        callee_funcs = [2, 3]
        callee_probability = 0.6
        code_blocks = self.gen._generate_indirect_call_code_blocks(
            callee_funcs, callee_probability)
        self.assertEqual(len(code_blocks), 3)
        first_pf_body = self.gen._code_block_bodies[
            code_blocks[0].code_block_body_id]
        self.assertEqual(first_pf_body.code_prefetch.type,
                         cfg_pb2.CodePrefetchInst.TargetType.FUNCTION)
        self.assertEqual(first_pf_body.code_prefetch.degree, 1)
        self.assertEqual(first_pf_body.code_prefetch.target_id, callee_funcs[0])
        second_pf_body = self.gen._code_block_bodies[
            code_blocks[1].code_block_body_id]
        self.assertEqual(second_pf_body.code_prefetch.type,
                         cfg_pb2.CodePrefetchInst.TargetType.FUNCTION)
        self.assertEqual(second_pf_body.code_prefetch.degree, 1)
        self.assertEqual(second_pf_body.code_prefetch.target_id,
                         callee_funcs[1])
        self.assertEqual(code_blocks[2].terminator_branch.type,
                         cfg_pb2.Branch.BranchType.INDIRECT_CALL)
        self.assertEqual(code_blocks[2].terminator_branch.targets, callee_funcs)
        self.assertAlmostEqual(
            code_blocks[2].terminator_branch.taken_probability[0], 0.6)
        self.assertAlmostEqual(
            code_blocks[2].terminator_branch.taken_probability[1], 0.4)


if __name__ == '__main__':
    unittest.main()
