"""In-memory representation of a callgraph.
"""
from __future__ import annotations
from typing import Dict, Optional, Collection, Callable, List
from frontend.code_generator import blocks
from frontend.proto import cfg_pb2
from google.protobuf import text_format  # type: ignore[attr-defined]


class Callgraph:
    """Representation of a protobuf callgraph

    Include helper methods to format string representations or interact with a
    underlying data structures.

        Typical usage example:
        cg = Callgraph.from_proto('/path/to/protobuf.pb')
        with open('c_file.c', 'w') as f:
            f.write(cg.format_function(1))
    """

    def __init__(self, functions: Dict[int, blocks.Function], entry_point: int,
                 global_vars_decl: blocks.CodeBlock,
                 global_vars_def: blocks.CodeBlock) -> None:
        self.entry_point: int = entry_point
        self.global_vars_decl: blocks.CodeBlock = global_vars_decl
        self.global_vars_def: blocks.CodeBlock = global_vars_def
        self.code_blocks: Dict[int, blocks.CodeBlock] = {}
        self.functions: Dict[int, blocks.Function] = functions
        for function in self.functions.values():
            for cb in function.code_blocks:
                self.code_blocks[cb.name] = cb

    @classmethod
    def from_proto(cls, path: str) -> Callgraph:
        cfg = cls._load_cfg_from_file(path)
        code_block_bodies = {}
        for proto_cbb in cfg.code_block_bodies:
            cbb = blocks.CodeBlockBody.from_proto(proto_cbb)
            code_block_bodies[cbb.name] = cbb
        if 0 not in code_block_bodies:
            code_block_bodies[0] = blocks.CodeBlockBody(name=0, instructions='')
        functions = {}
        for proto_func in cfg.functions:
            func = blocks.Function.from_proto(proto_func, code_block_bodies)
            functions[func.name] = func
        vars_decl = blocks.CodeBlock.from_proto(cfg.global_vars_decl,
                                                code_block_bodies)
        vars_def = blocks.CodeBlock.from_proto(cfg.global_vars_def,
                                               code_block_bodies)
        return cls(functions=functions,
                   entry_point=cfg.entry_point_function,
                   global_vars_decl=vars_decl,
                   global_vars_def=vars_def)

    @staticmethod
    def _load_cfg_from_file(path: str) -> cfg_pb2.CFG:
        cfg = cfg_pb2.CFG()
        with open(path, 'rb') as f:
            if path.endswith('pb'):
                cfg.ParseFromString(f.read())
            elif path.endswith('pbtxt'):
                text_format.Parse(f.read(), cfg)
            else:
                raise RuntimeError(
                    'Invalid protobuf suffix found, expected .pb or .pbtxt')
        return cfg

    def format_vars_definition(self) -> str:
        return self.format_code_block_body(self.global_vars_def)

    def format_code_block_body(self, code_block: blocks.CodeBlock) -> str:
        return code_block.get_instructions()

    def function_call_signature_for(self, function_name: int) -> str:
        return self.get_function(function_name).get_call_signature()

    def get_function(self, function_name: int) -> blocks.Function:
        return self.functions[function_name]

    def format_vars_declaration(self) -> str:
        return self.format_code_block_body(self.global_vars_decl)

    def format_headers(self) -> str:
        headers = []
        for function in self.functions.values():
            headers.append(f'{function.get_signature_header()}();')
        out = '\n'.join(headers)
        out += '\n'
        return out

    def direct_call_targets_for_function(
            self, function_name) -> Collection[Optional[int]]:
        function = self.get_function(function_name)
        return function.get_branch_targets(
            blocks.Branch.filter(blocks.BranchType.DIRECT_CALL))

    def format_function(self, function_name: int) -> str:
        function = self.get_function(function_name)
        result = function.get_signature_header() + '() {\n'
        code_block_texts = [
            self.format_code_block_with_label(code_block)
            for code_block in function.code_blocks
        ]
        result = result + ''.join(code_block_texts)
        result += '}\n'
        return result

    def format_code_block_with_label(self, codeblock: blocks.CodeBlock) -> str:
        return (f'{self.format_code_block_label(codeblock)}:;\n'
                f'{self.format_code_block(codeblock)}')

    def format_code_block_label(self, codeblock: blocks.CodeBlock) -> str:
        return f'label{codeblock.name}'

    def format_code_block(self, codeblock: blocks.CodeBlock) -> str:
        cbb_text = self.format_code_block_body(codeblock)
        branch_text = self.format_branch(codeblock.terminator_branch)
        return f'{cbb_text}{branch_text}'

    def format_branch(self, branch: blocks.Branch) -> str:
        branch_formatters: Dict[blocks.BranchType, Callable] = {
            blocks.BranchType.INDIRECT_CALL:
                self._format_branch_indirect_call,
            blocks.BranchType.DIRECT_CALL:
                self._format_branch_direct_call,
            blocks.BranchType.FALLTHROUGH:
                self._format_branch_fallthrough,
            blocks.BranchType.UNKNOWN:
                self._format_branch_fallthrough,
            blocks.BranchType.CONDITIONAL_DIRECT:
                self._format_branch_conditional_direct,
            blocks.BranchType.CONDITIONAL_INDIRECT:
                self._format_branch_conditional_indirect,
            blocks.BranchType.INDIRECT:
                self._format_branch_indirect,
            blocks.BranchType.DIRECT:
                self._format_branch_direct,
            blocks.BranchType.RETURN:
                self._format_branch_return
        }
        if branch.branch_type in branch_formatters:
            return branch_formatters[branch.branch_type](branch)
        raise ValueError(f'Unknown branch type: {branch.branch_type}')

    def _format_branch_indirect_call(self,
                                     branch: blocks.Branch,
                                     uuid: int = None) -> str:
        """Format an indirect call.

        Args:
            branch: blocks.Branch instance. Must have branch_type of
              INDIRECT_CALL.
            uuid: Unique suffix to use for local variables. Used to
              differentiate multiple branches in a single function and to avoid
              any overlapping variables provided in user defined instructions.
              Leaving unspecified will let the program decide a unique suffix.

        Returns:
            A str representing an indirect call in C.
        """
        if uuid is None:
            uuid = id(branch)
        if len(branch.get_targets()) == 1:
            return self._format_indirect_call_singletarget(branch, uuid)
        return self._format_indirect_call_multitarget(branch, uuid)

    def _format_indirect_call_singletarget(self, branch: blocks.Branch,
                                           uuid: int) -> str:
        target = branch.next_valid_target()
        sig = self.function_call_signature_for(target)
        return (f'void (*frontend_{uuid})(void) = {sig};\n'
                f'frontend_{uuid}();\n')

    def _format_indirect_call_multitarget(self, branch: blocks.Branch,
                                          uuid: int) -> str:
        paths = branch.next_target_sequence()
        max_index = len(paths)
        paths_array_name = f'paths_{uuid}'
        paths_array = self._create_target_sequence_array(
            paths, paths_array_name)
        func_array = self._create_call_target_array(branch.get_targets(),
                                                    f'array_{uuid}')
        result = (
            f'static int index_{uuid} = 0;\n'
            f'{paths_array}'
            f'{func_array}'
            f'void (*f_{uuid})(void) = '
            f'array_{uuid}[{paths_array_name}[index_{uuid}++ % {max_index}]];\n'
            f'f_{uuid}();\n')
        return result

    def _create_target_sequence_array(self, target_sequence: List[int],
                                      array_name: str) -> str:
        max_index = len(target_sequence)
        target_sequence_formatted = ','.join(
            [str(target) for target in target_sequence])
        result = (f'static int {array_name}[{max_index}] = '
                  '{'
                  f'{target_sequence_formatted}'
                  '};\n')
        return result

    def _create_call_target_array(self, targets: List[Optional[int]],
                                  array_name: str) -> str:
        result = f'static void* {array_name}[] = ' + '{'
        func_targets = []
        for target in targets:
            if target is None:
                raise ValueError('Call to None target found')
            func_targets.append('&' + self.function_call_signature_for(target))
        result += ', '.join(func_targets)
        result += '};\n'
        return result

    def _format_branch_direct_call(self, branch: blocks.Branch) -> str:
        target = branch.next_valid_target()
        string = self.function_call_signature_for(target)
        return f'{string}();\n'

    def _format_branch_fallthrough(self, branch: blocks.Branch) -> str:
        del branch  # Unused.
        return ''

    def _format_branch_conditional_direct(self, branch: blocks.Branch) -> str:
        paths = branch.next_target_sequence()
        max_index = len(paths)
        branch_id = id(branch)
        paths_array_name = f'paths_{branch_id}'
        paths_array = self._create_target_sequence_array(
            paths, paths_array_name)
        switch_cases = self._build_switch_cases(branch)
        result = (
            f'static int index_{branch_id} = 0;\n'
            f'{paths_array}'
            f'switch ({paths_array_name}[index_{branch_id}++ % {max_index}]) '
            '{\n'
            f'{switch_cases}'
            '}\n')
        return result

    def _build_switch_cases(self, branch: blocks.Branch) -> str:
        result = ''
        for i in range(len(branch.targets)):
            target = branch.get_target_from_index(i)
            new_string = f'case {i}:\n'
            if target is None:
                # Fallthrough branch
                new_string = f'{new_string}\tbreak;\n'
            else:
                label = self.format_code_block_label(self.code_blocks[target])
                new_string = f'{new_string}\tgoto {label};\n'
            result += new_string
        return result

    def _format_branch_conditional_indirect(self, branch: blocks.Branch) -> str:
        raise ValueError(f'{branch.branch_type} is not implemented')

    def _format_branch_indirect(self, branch: blocks.Branch) -> str:
        target = branch.next_valid_target()
        label = self.format_code_block_label(self.code_blocks[target])
        branch_id = id(branch)
        fake_label = f'label{branch_id}'
        result = (f'{fake_label}:;\n'
                  'int label_target = 0;\nvoid* array[] = {'
                  f'&&{label}'
                  f', &&{fake_label}'
                  '};\n'
                  'goto *(array[label_target]);\n')
        return result

    def _format_branch_direct(self, branch: blocks.Branch) -> str:
        target = branch.next_valid_target()
        label = self.format_code_block_label(self.code_blocks[target])
        return f'goto {label};\n'

    def _format_branch_return(self, branch: blocks.Branch) -> str:
        del branch  # Unused.
        return 'return;\n'
