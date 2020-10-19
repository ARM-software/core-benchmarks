# pylint: disable=redefined-outer-name
"""Tests for source_generator.py"""
import os
import pytest
import platform
import glob
import re
from filecmp import dircmp
import sh
from frontend.code_generator import user_callgraph
from frontend.code_generator import source_generator


@pytest.fixture
def rootdir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.path.pardir)


@pytest.fixture
def resources(rootdir):
    return os.path.join(rootdir, 'resources')


X86_INDIRECT_CALL = r'callq\s+\*'
ARM_INDIRECT_CALL = r'\s+blr\s+x\d+'


def test_branch_indirect_call(resources, tmpdir):
    test_file = os.path.join(resources, 'branch_indirect_call.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = compile_and_return_output(
        tmpdir, 'function_2',
        switch_processor(X86_INDIRECT_CALL, ARM_INDIRECT_CALL))
    assert output, 'Missing indirect function call'


X86_DIRECT_CALL = r'callq\s+\d*'
ARM_DIRECT_CALL = r'\s+bl\s+\d*'


def test_branch_direct_call(resources, tmpdir):
    test_file = os.path.join(resources, 'branch_direct_call.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = compile_and_return_output(
        tmpdir, 'function_2', switch_processor(X86_DIRECT_CALL,
                                               ARM_DIRECT_CALL))
    assert output, 'Missing direct function call'


X86_INDIRECT_BRANCH = r'jmp\w*\s+\*'
ARM_INDIRECT_BRANCH = r'\s+br\s+x\d+'


def test_branch_indirect(resources, tmpdir):
    test_file = os.path.join(resources, 'branch_indirect.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = compile_and_return_output(
        tmpdir, 'function_2',
        switch_processor(X86_INDIRECT_BRANCH, ARM_INDIRECT_BRANCH))
    assert output, 'Missing indirect branch'


X86_CONDITIONAL_DIRECT = r'\s+je\s+.*'
ARM_CONDITIONAL_DIRECT = r'\s+b\.\w+\s+\d+'


def test_branch_conditional_direct(resources, tmpdir):
    test_file = os.path.join(resources, 'branch_conditional_direct.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = compile_and_return_output(
        tmpdir, 'function_2',
        switch_processor(X86_CONDITIONAL_DIRECT, ARM_CONDITIONAL_DIRECT))
    assert output, 'Missing indirect branch'


def test_branch_implicit_fallthrough(resources, tmpdir):
    test_file = os.path.join(resources, 'branch_implicit_fallthrough.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = compile_and_return_output(
        tmpdir, 'function_2',
        switch_processor(X86_CONDITIONAL_DIRECT, ARM_CONDITIONAL_DIRECT))
    assert output, 'Implicit fallthrough branch error'


def switch_processor(value1, value2):
    processor = platform.processor()
    if not processor:
      # platform.processor() is not always populated.
      processor = platform.machine()
    if processor == 'x86_64':
        return value1
    elif processor == 'aarch64':
        return value2
    raise RuntimeError(f'Unrecognized processor: {processor}')


def compile_and_return_output(directory, symbol, asm):
    gcc = sh.Command('gcc')
    objdump = sh.Command('objdump')
    output_file = f'{directory}/bin_output'
    gcc('-o', output_file, '-O0', glob.glob(f'{directory}/*.c'))
    out = objdump(f'--disassemble={symbol}', output_file)
    return bool(re.search(asm, str(out)))


def test_get_formatted_headers_onefunction(resources):
    test_file = os.path.join(resources, 'onefunction.pbtext')
    expected = 'void function_19();\n'
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_headers()
    assert output == expected


def test_write_onefunction(resources, tmpdir):
    test_file = os.path.join(resources, 'onefunction.pbtext')
    expected_dir = os.path.join(resources, 'write_onefunction')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = dircmp(tmpdir, expected_dir)
    diff_files = set(output.same_files) ^ set(output.left_list)
    assert diff_files == set(), f'Different files: {diff_files}'


def test_write_onefunction_globalvars(resources, tmpdir):
    test_file = os.path.join(resources, 'onefunction_globalvars.pbtext')
    expected_dir = os.path.join(resources, 'write_onefunction_globalvars')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files()
    output = dircmp(tmpdir, expected_dir)
    diff_files = set(output.same_files) ^ set(output.left_list)
    assert diff_files == set(), f'Different files: {diff_files}'


def test_write_onecallchain(resources, tmpdir):
    test_file = os.path.join(resources, 'onecallchain.pbtext')
    expected_dir = os.path.join(resources, 'write_onecallchain')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files(num_files=1)
    output = dircmp(tmpdir, expected_dir)
    diff_files = set(output.same_files) ^ set(output.left_list)
    assert diff_files == set(), f'Different files: {diff_files}'


@pytest.mark.parametrize('num_files', [48, 1, 12])
def test_dfs(resources, tmpdir, num_files):
    depth = 10
    test_file = os.path.join(resources, 'dfs', f'dfs_depth{depth}_cfg.pb')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    source_gen = source_generator.SourceGenerator(tmpdir, cfg)
    source_gen.write_files(num_files)
    misc_c_files = ['main.c']
    c_files = glob.glob(f'{tmpdir}/*.c')
    assert len(c_files) == pytest.approx(num_files + len(misc_c_files), 1)
    for c_file in c_files:
        with open(c_file, 'r') as f:
            matches = re.findall(source_gen.get_header_import_string(),
                                 f.read())
            assert len(matches) == 1
