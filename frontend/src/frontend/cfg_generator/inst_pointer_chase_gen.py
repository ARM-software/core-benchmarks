"""Generates an instruction pointer-chase benchmark.

The benchmark consists of a collection of N callchains of length L.  Each
function runs a small amount of simple instructions, then calls the next
function. The function call sequence is designed to look arbitrary. Once this
callchain completes and unwinds, the function moves on to the next callchain.
"""

from typing import List, Optional, Dict
from frontend.proto import cfg_pb2
from frontend.cfg_generator import common

MODULE_NAME = 'inst_pointer_chase_gen'


def register_args(parser):
    subparser = parser.add_parser(MODULE_NAME)
    subparser.add_argument('--depth',
                           default=20,
                           type=int,
                           help='Depth of each callchain.')
    subparser.add_argument('--num_callchains',
                           default=1000,
                           type=int,
                           help='Number of distinct callchains.')
    subparser.add_argument('--insert_code_prefetches',
                           default=False,
                           action='store_true',
                           help='Insert code prefetches into the '
                           'callchains. Not available on all platforms.')


# Indicates in the caller-to-callee mapping that a function does not call any
# other function.
NO_CALLEE = -1


class InstPointerChaseGenerator(common.BaseGenerator):
    """Generates an instruction pointer chase benchmark."""

    def __init__(
            self,
            depth: int,
            num_callchains: int,
            insert_code_prefetches: bool,
            function_selector: Optional[common.FunctionSelector] = None
    ) -> None:
        super().__init__()
        self._depth: int = depth
        self._num_callchains: int = num_callchains
        self._insert_code_prefetches: bool = insert_code_prefetches
        self._caller2callee: Dict[int, int] = {}
        self._callchain_entry_functions: List[int] = []
        self._entry_function_id: int = 0
        if function_selector is None:
            self._function_selector: common.FunctionSelector = \
                common.pop_random_element
        else:
            self._function_selector = function_selector
        self._function_body: cfg_pb2.CodeBlockBody = self._add_code_block_body(
            'int x = 1;\n'
            'int y = x*x + 3;\n'
            'int z = y*x + 12345;\n'
            'int w = z*z + x - y;\n')

    def _generate_callchain_mappings(self) -> None:
        num_functions = self._num_callchains * self._depth
        function_list = list(range(0, num_functions))
        for _ in range(0, self._num_callchains):
            # Generate a pointer chase. The final function will just return.
            caller = self._function_selector(function_list)
            self._callchain_entry_functions.append(caller)
            for _ in range(0, self._depth - 1):
                callee = self._function_selector(function_list)
                self._caller2callee[caller] = callee
                caller = callee
            # The final function in the chain does not call.
            self._caller2callee[caller] = NO_CALLEE

        assert len(self._caller2callee) == num_functions, (
            'There should be exactly one caller2callee mapping for every '
            'function.')

    def _add_code_prefetch_code_block(self,
                                      function_id: Optional[int] = None,
                                      code_block_id: Optional[int] = None,
                                      degree: int = 1) -> cfg_pb2.CodeBlock:
        """Create a code prefetch code block.

        The target address to prefetch is specified by either function_id or
        code_block_id, which also indicate what the target type is. Only one of
        these can be specified.
        """
        if function_id is not None and code_block_id is not None:
            raise ValueError(
                'cannot specify both function_id and code_block_id')
        if degree <= 0:
            raise ValueError('prefetch degree must be > 0')
        prefetch_inst = self._add_code_block_body()
        if function_id is not None:
            prefetch_inst.code_prefetch.type = \
                cfg_pb2.CodePrefetchInst.TargetType.FUNCTION
            prefetch_inst.code_prefetch.target_id = function_id
        elif code_block_id is not None:
            prefetch_inst.code_prefetch.type = \
                cfg_pb2.CodePrefetchInst.TargetType.CODE_BLOCK
            prefetch_inst.code_prefetch.target_id = code_block_id
        else:
            raise ValueError('must specify one of function_id or code_block_id')
        prefetch_inst.code_prefetch.degree = degree
        prefetch_body = self._add_code_block()
        prefetch_body.code_block_body_id = prefetch_inst.id
        return prefetch_body

    def _generate_callchain_functions(self) -> None:
        # First, generate codeblocks. Each function has two: the main body, with
        # a fallthrough branch, and the call, with a return terminator branch.
        for caller, callee in self._caller2callee.items():
            function = self._add_function_with_id(caller)
            if self._insert_code_prefetches and callee != NO_CALLEE:
                function.instructions.append(
                    self._add_code_prefetch_code_block(function_id=callee))

            main_body = self._add_code_block()
            main_body.code_block_body_id = self._function_body.id
            main_body.terminator_branch.type = \
                cfg_pb2.Branch.BranchType.FALLTHROUGH
            function.instructions.append(main_body)

            if callee != NO_CALLEE:
                call_block = self._add_code_block()
                # Leave the branch target unspecified for now.
                call_block.terminator_branch.type = (
                    cfg_pb2.Branch.BranchType.DIRECT_CALL)
                call_block.terminator_branch.targets.append(callee)
                call_block.terminator_branch.taken_probability.append(1)
                # The end of a function in C will implicitly return, no need to
                # create another CodeBlock.
                function.instructions.append(call_block)

    def _generate_entry_function(self) -> None:
        entry_func = self._add_function_with_id(common.IDGenerator.next())
        for callchain_start in self._callchain_entry_functions:
            # Get the first CodeBlock of the called function.
            called_func = self._functions[callchain_start]
            # Create a CodeBlock that just calls this function (the start of a
            # callchain), no additional CodeBlockBody required.
            code_block = self._add_code_block()
            code_block.terminator_branch.type = \
                cfg_pb2.Branch.BranchType.DIRECT_CALL
            code_block.terminator_branch.targets.append(called_func.id)
            code_block.terminator_branch.taken_probability.append(1)
            entry_func.instructions.append(code_block)
        self._entry_function_id = entry_func.id

    def generate_cfg(self) -> cfg_pb2.CFG:
        self._generate_callchain_mappings()
        self._generate_callchain_functions()
        self._generate_entry_function()
        return self._generate_cfg(self._functions, self._code_block_bodies,
                                  self._entry_function_id)


def generate_cfg(args):
    """Generate a CFG of arbitrary callchains."""
    print('Generating instruction pointer chase benchmark...')
    generator = InstPointerChaseGenerator(args.depth,
                                          args.insert_code_prefetches,
                                          args.num_callchains)
    return generator.generate_cfg()
