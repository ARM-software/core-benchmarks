"""Tests for inst_pointer_chase_gen."""
# Access to protected class members is common for unit tests.
# pylint: disable=protected-access

import unittest

import cfg_pb2
import inst_pointer_chase_gen


def _pop_next_function(function_list):
    """Pops and returns the next function in the list."""
    if not function_list:
        raise IndexError('in _pop_next_function: list of functions is empty')
    return function_list.pop(0)


class InstPointerChaseGeneratorTest(unittest.TestCase):

    def setUp(self):
        self.depth = 3
        self.num_callchains = 2
        self.gen = inst_pointer_chase_gen.InstPointerChaseGenerator(
            self.depth,
            self.num_callchains,
            function_selector=_pop_next_function)

    def _target_branch_for(self, func):
        """Returns the branch to the intended callee of this function."""
        return func.instructions[1].terminator_branch

    def test_generate_callchain_mappings(self):
        self.gen._generate_callchain_mappings()
        self.assertEqual(self.gen._caller2callee[0], 1)
        self.assertEqual(self.gen._caller2callee[1], 2)
        self.assertEqual(self.gen._caller2callee[2],
                         inst_pointer_chase_gen.NO_CALLEE)
        self.assertEqual(self.gen._caller2callee[3], 4)
        self.assertEqual(self.gen._caller2callee[4], 5)
        self.assertEqual(self.gen._caller2callee[5],
                         inst_pointer_chase_gen.NO_CALLEE)

    def test_generate_callchain_function_codeblockbodies(self):
        self.gen._generate_callchain_mappings()
        self.gen._generate_callchain_functions()
        self.assertEqual(len(self.gen._functions),
                         self.depth * self.num_callchains)

        # All functions should use the same main code block body.
        code_block_bodies = set()
        for func_id, func in self.gen._functions.items():
            main_code_block = func.instructions[0]
            code_block_bodies.add(main_code_block.code_block_body_id)
            sig_body = (
                self.gen._code_block_bodies[func.signature.code_block_body_id])
            self.assertIn(self.gen.function_name(func_id),
                          sig_body.instructions)

        for func_id, func in self.gen._functions.items():
            self.assertEqual(main_code_block.terminator_branch.type,
                             cfg_pb2.Branch.BranchType.FALLTHROUGH)

        self.assertEqual(
            len(code_block_bodies),
            1,
            msg='All functions should share the same main code block body.')

    def test_generate_callchain_function_callees(self):
        self.gen._generate_callchain_mappings()
        self.gen._generate_callchain_functions()
        # Map from a caller function to its callee in the chain.
        expected_caller2callee = {0: 1, 1: 2, 3: 4, 4: 5}

        for func_id, func in self.gen._functions.items():
            if func_id in expected_caller2callee:
                # This function calls another in a chain.
                self.assertEqual(len(func.instructions), 2)
                self.assertEqual(
                    self._target_branch_for(func).type,
                    cfg_pb2.Branch.BranchType.DIRECT_CALL)
                expected_callee_func = (
                    self.gen._functions[expected_caller2callee[func_id]])
                self.assertEqual(
                    self._target_branch_for(func).targets[0],
                    expected_callee_func.id,
                    msg='Function %d should call function %d, got %d' %
                    (func_id, expected_callee_func.id,
                     self._target_branch_for(func).targets[0]))
                self.assertEqual(
                    self._target_branch_for(func).taken_probability[0], 1)
            else:
                self.assertEqual(len(func.instructions), 1)

    def test_generate_entry_function(self):
        self.gen._generate_callchain_mappings()
        self.gen._generate_callchain_functions()
        self.gen._generate_entry_function()
        entry_func = self.gen._functions[self.gen._entry_function_id]
        entry_func_sig = self.gen._code_block_bodies[
            entry_func.signature.code_block_body_id]
        self.assertIn(self.gen.function_name(entry_func.id),
                      entry_func_sig.instructions)
        self.assertEqual(len(entry_func.instructions), self.num_callchains)
        for code_block in entry_func.instructions:
            self.assertEqual(code_block.terminator_branch.type,
                             cfg_pb2.Branch.BranchType.DIRECT_CALL)
            self.assertEqual(code_block.terminator_branch.type,
                             cfg_pb2.Branch.BranchType.DIRECT_CALL)
            self.assertIn(code_block.terminator_branch.targets[0],
                          self.gen._functions)
            self.assertEqual(code_block.terminator_branch.taken_probability[0],
                             1)

    def test_generate_cfg(self):
        cfg = self.gen.generate_cfg()
        # +1 accounts for the entry function.
        num_total_functions = self.depth * self.num_callchains + 1
        self.assertEqual(len(cfg.functions), num_total_functions)
        # Each function adds a code block body to store its signature, and all
        # functions share the same main code block body.
        self.assertEqual(len(cfg.code_block_bodies), num_total_functions + 1)


if __name__ == '__main__':
    unittest.main()
