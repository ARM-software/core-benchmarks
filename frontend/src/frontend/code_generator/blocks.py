"""Classes representing Callgraph building blocks.

The intention of this module is to remove interaction with protobuf directly.
Classes are modeled after protobuf messages, but include additional quality
of life features and/or bookkeeping.

Only one calling class should instantiate and interact with classes in the
module.
"""
from __future__ import annotations
import math
import random
import re
from enum import Enum
from typing import List, Optional, Iterable, Union, Dict, NamedTuple, Set, Callable


class BranchType(Enum):
    UNKNOWN = 0
    DIRECT = 1
    CONDITIONAL_DIRECT = 2
    INDIRECT = 3
    CONDITIONAL_INDIRECT = 4
    DIRECT_CALL = 5
    INDIRECT_CALL = 6
    RETURN = 7
    FALLTHROUGH = 8


class BranchTargetAndProbability(NamedTuple):
    target: Optional[int]
    probability: float


class BranchFilter:

    def __init__(self, branch_type: Union[BranchType,
                                          Iterable[BranchType]]) -> None:
        if isinstance(branch_type, BranchType):
            branch_type = [branch_type]
        self.branch_types: Set[BranchType] = set(branch_type)

    def __call__(self, branch: Branch) -> bool:
        return branch.branch_type in self.branch_types


class Branch:
    """Represents a branch instruction, aka an edge in the callgraph."""
    seed: int

    def __init__(self,
                 branch_type: str,
                 targets: Optional[List[int]] = None,
                 taken_probability: Optional[List[float]] = None) -> None:
        self.branch_type: BranchType = BranchType(branch_type)
        if not targets:
            targets = []
        if not taken_probability:
            taken_probability = []
        self.targets: List[BranchTargetAndProbability] = [
            BranchTargetAndProbability(target, prob)
            for target, prob in zip(targets, taken_probability)
        ]
        self.validate_probabilities(taken_probability)

    def __str__(self) -> str:
        return f'Branch(type: {self.branch_type}, targets: {self.targets})'

    def validate_probabilities(self, taken_probability: List[float]) -> None:
        if self.branch_type in (BranchType.FALLTHROUGH, BranchType.UNKNOWN,
                                BranchType.RETURN):
            return
        total = sum(taken_probability)
        if not math.isclose(total, 1.0, rel_tol=1e-03):
            if self.branch_type in (BranchType.CONDITIONAL_DIRECT,
                                    BranchType.CONDITIONAL_INDIRECT):
                # The rest of the probability is a fallthrough branch
                self.targets.append(
                    BranchTargetAndProbability(None, 1.0 - total))
            else:
                raise ValueError(
                    'Sum of probabilities in branch is not 1.0 (Got {})\n{}'.
                    format(total, self))

    @classmethod
    def from_proto(cls, proto_branch) -> Branch:
        return cls(branch_type=proto_branch.type,
                   targets=proto_branch.targets,
                   taken_probability=proto_branch.taken_probability)

    @classmethod
    def set_seed(cls, seed) -> None:
        cls.seed = seed
        random.seed(cls.seed)

    @staticmethod
    def filter(
            branch_filter: Union[BranchType, Iterable[BranchType]]) -> Callable:
        return BranchFilter(branch_filter)

    def get_targets(self) -> List[Optional[int]]:
        return [branch_target.target for branch_target in self.targets]

    def next_valid_target(self) -> int:
        index = self._get_next_target_index()
        target = self.get_target_from_index(index)
        if target is None:
            raise ValueError('Valid target not found')
        return target

    def _get_next_target_index(self) -> int:
        random_value = random.random()
        seen_values = 0.0
        for index, branch_target in enumerate(self.targets):
            seen_values += branch_target.probability
            if random_value < seen_values:
                return index
        raise RuntimeError('This should never happen')

    def get_target_from_index(self, index: int) -> Optional[int]:
        return self.targets[index].target

    def next_target_sequence(self, length: int = 16) -> List[int]:
        paths = []
        for _ in range(length):
            index = self._get_next_target_index()
            paths.append(index)
        return paths


class CodeBlockBody:
    """Contains instructions."""

    def __init__(self, name: int, instructions: str) -> None:
        self.name: int = name
        self.instructions: str = instructions

    def __str__(self) -> str:
        return (f'CodeBlockBody(name: {self.name}, '
                f'instructions: {self.instructions})')

    @classmethod
    def from_proto(cls, proto_cbb) -> CodeBlockBody:
        return cls(name=proto_cbb.id, instructions=proto_cbb.instructions)


class CodeBlock:
    """Represents a set of instructions, terminated by a branch instruction."""

    def __init__(self,
                 name: int,
                 code_block_body: CodeBlockBody,
                 terminator_branch: Branch,
                 unroll_factor: int = 0) -> None:
        self.name: int = name
        self.code_block_body: CodeBlockBody = code_block_body
        self.terminator_branch: Branch = terminator_branch
        self.unroll_factor: int = unroll_factor

    def __str__(self) -> str:
        return (f'CodeBlock(name: {self.name}, '
                f'code_block_body: {self.code_block_body}, '
                f'branch: {self.terminator_branch}, '
                f'unroll_factor: {self.unroll_factor})')

    @classmethod
    def from_proto(cls, proto_cb,
                   code_block_bodies: Dict[int, CodeBlockBody]) -> CodeBlock:
        branch = Branch.from_proto(proto_cb.terminator_branch)
        code_block_body = code_block_bodies[proto_cb.code_block_body_id]
        return cls(name=proto_cb.id,
                   code_block_body=code_block_body,
                   terminator_branch=branch,
                   unroll_factor=proto_cb.unroll_factor)

    def get_instructions(self) -> str:
        return self.code_block_body.instructions

    def get_branch_targets(self) -> List[Optional[int]]:
        return self.terminator_branch.get_targets()


class Function:
    """Represents a function in C code."""

    def __init__(self,
                 name: int,
                 signature: CodeBlock,
                 code_blocks: Optional[List[CodeBlock]] = None) -> None:
        self.name: int = name
        self.signature: CodeBlock = signature
        self.code_blocks: List[CodeBlock] = code_blocks if code_blocks else []

    def __str__(self) -> str:
        return (f'Function(name: {self.name}, signature: {self.signature}, '
                f'code_blocks len: {len(self.code_blocks)})')

    @classmethod
    def from_proto(cls, proto_func,
                   code_block_bodies: Dict[int, CodeBlockBody]) -> Function:
        code_blocks = []
        for instruction in proto_func.instructions:
            codeblk = CodeBlock.from_proto(instruction, code_block_bodies)
            code_blocks.append(codeblk)
        func = cls(name=proto_func.id,
                   signature=CodeBlock.from_proto(proto_func.signature,
                                                  code_block_bodies),
                   code_blocks=code_blocks)
        return func

    def get_call_signature(self) -> str:
        ''' strips return type off the function signature

        e.g.
            void signature_10 -> signature_10
        '''
        match = re.search(r'\w+\s+(\w+)', self.get_signature_header())
        if not match:
            raise RuntimeError('Malformed function signature format: '
                               f'{self.get_signature_header()}')
        return match.group(1)

    def get_signature_header(self) -> str:
        return self.signature.get_instructions()

    def get_branch_targets(
            self, branch_filter: Callable[[Branch],
                                          bool]) -> List[Optional[int]]:
        targets: List[Optional[int]] = []
        for code_block in self.code_blocks:
            if branch_filter(code_block.terminator_branch):
                targets.extend(code_block.get_branch_targets())
        return targets
