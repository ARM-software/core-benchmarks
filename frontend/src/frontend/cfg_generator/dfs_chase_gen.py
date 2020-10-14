"""Generates a DFS tree-based instruction pointer chase benchmark.

The benchmark consists of a full binary tree of depth D. Each node is a
conditional branch that calls one child function. This process repeats until we
reach the leaf.
"""

from typing import List, Optional, Dict
from frontend.proto import cfg_pb2
from frontend.cfg_generator import common

MODULE_NAME = 'dfs_chase_gen'


def register_args(parser):
    subparser = parser.add_parser(MODULE_NAME)
    subparser.add_argument('--depth',
                           default=20,
                           type=int,
                           help='Depth of the function call tree.')
    subparser.add_argument('--branch_probability',
                           default=0.5,
                           type=float,
                           help='Branch taken probability.')


class DFSChaseGenerator(common.BaseGenerator):
    """Generates a DFS instruction pointer chase benchmark."""

    def __init__(self, depth: int, branch_probability: float) -> None:
        super().__init__()

        self._depth: int = depth
        # Map from function id to its left/right callee.
        self._function_tree: Dict[int, List[int]] = {}
        # A list of functions that do not call other functions.
        self._leaf_functions: List[int] = []
        # ID of the function at the root of the function tree.
        self._root_func: int = 0
        self._branch_probability: float = branch_probability
        self._function_body: cfg_pb2.CodeBlockBody = self._add_code_block_body(
            'int x = 1;\n'
            'int y = x*x + 3;\n'
            'int z = y*x + 12345;\n'
            'int w = z*z + x - y;\n')

    def _add_code_block_with_branch(
            self,
            branch_type: cfg_pb2.Branch.BranchTypeValue,
            target: Optional[int] = None,
            probability: Optional[float] = None) -> cfg_pb2.CodeBlock:
        """Add an empty code block with the specified terminator branch."""
        block = self._add_code_block()
        block.terminator_branch.type = branch_type
        if target:
            block.terminator_branch.targets.append(target)
        if probability:
            block.terminator_branch.taken_probability.append(probability)
        return block

    def _generate_conditional_branch_code_blocks(
            self, call_targets: List[int],
            probability: float) -> List[cfg_pb2.CodeBlock]:
        if len(call_targets) != 2:
            raise ValueError('call_targets must have length 2, got %d' %
                             len(call_targets))

        # Conditional branch taken path.
        taken_block = self._add_code_block_with_branch(
            cfg_pb2.Branch.BranchType.DIRECT_CALL, call_targets[0], 1)
        taken_block_ret = self._add_code_block_with_branch(
            cfg_pb2.Branch.BranchType.RETURN)

        # Fallthrough block.
        ft_block = self._add_code_block_with_branch(
            cfg_pb2.Branch.BranchType.DIRECT_CALL, call_targets[1], 1)
        ft_block_ret = self._add_code_block_with_branch(
            cfg_pb2.Branch.BranchType.RETURN)

        cond_block = self._add_code_block_with_branch(
            cfg_pb2.Branch.BranchType.CONDITIONAL_DIRECT, taken_block.id,
            probability)

        # Fallthrough must come right after the conditional branch.
        return [
            cond_block, ft_block, ft_block_ret, taken_block, taken_block_ret
        ]

    def _generate_leaf_function_code_blocks(self) -> cfg_pb2.CodeBlock:
        codeblock = self._add_code_block()
        codeblock.terminator_branch.type = cfg_pb2.Branch.BranchType.RETURN
        return codeblock

    def _generate_function_tree(self) -> None:
        next_id = common.IDGenerator.next()
        self._root_func = next_id
        queue = [next_id]
        for _ in range(0, self._depth - 1):
            children: List[int] = []
            for func in queue:
                self._function_tree[func] = [
                    common.IDGenerator.next(),
                    common.IDGenerator.next()
                ]
                children.extend(self._function_tree[func])
            queue = children
            # The callees of the second-to-last level in the tree are leaves.
            self._leaf_functions = children

    def _generate_functions(self) -> None:
        self._add_function_with_id(self._root_func)
        for caller, callees in self._function_tree.items():
            for callee in callees:
                self._add_function_with_id(callee)
            self._functions[caller].instructions.extend(
                self._generate_conditional_branch_code_blocks(
                    callees, self._branch_probability))

        for leaf in self._leaf_functions:
            self._functions[leaf].instructions.append(
                self._generate_leaf_function_code_blocks())

    def generate_cfg(self) -> cfg_pb2.CFG:
        self._generate_function_tree()
        self._generate_functions()
        return self._generate_cfg(self._functions, self._code_block_bodies,
                                  self._root_func)


def generate_cfg(args):
    """Generate a CFG of arbitrary callchains."""
    print('Generating DFS instruction pointer chase benchmark...')
    generator = DFSChaseGenerator(args.depth, args.branch_probability)
    return generator.generate_cfg()
