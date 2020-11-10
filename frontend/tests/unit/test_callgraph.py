# pylint: disable=redefined-outer-name
"""Tests for user_callgraph.py"""
# pylint: disable=protected-access
import pytest
import os
from frontend.code_generator import user_callgraph
from frontend.code_generator import blocks


@pytest.fixture
def rootdir():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.path.pardir,
    )


@pytest.fixture
def resources(rootdir):
    return os.path.join(rootdir, 'resources')


def test_callgraph_from_proto_file(resources):
    path = os.path.join(resources, 'cfg.pb')
    cfg = user_callgraph.Callgraph.from_proto(path)
    assert len(cfg.functions.keys()) > 10


def test_get_formatted_headers_onecallchain(resources):
    test_file = os.path.join(resources, 'onecallchain.pbtxt')
    expected = ('void function_2();\n'
                'void function_3();\n'
                'void function_4();\n'
                'void function_5();\n'
                'void function_6();\n')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_headers()
    assert output == expected


def test_load_onecallchain(resources):
    test_file = os.path.join(resources, 'onecallchain.pbtxt')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    assert isinstance(cfg, user_callgraph.Callgraph)
    assert len(cfg.functions) == 5
    assert cfg.entry_point == 2


def test_load_binary_proto(resources):
    test_file = os.path.join(resources, 'onefunction.pb')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    assert isinstance(cfg, user_callgraph.Callgraph)
    assert len(cfg.functions) == 1
    assert cfg.entry_point == 2


def test_load_onefunction(resources):
    test_file = os.path.join(resources, 'onefunction.pbtxt')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    assert isinstance(cfg, user_callgraph.Callgraph)
    assert len(cfg.functions) == 1
    assert cfg.entry_point == 2


def test_print_function_onefunction(resources):
    test_file = os.path.join(resources, 'onefunction.pbtxt')
    expected = ('void function_19() {\n'
                'label1:;\n'
                'int x = 1;\n'
                'int y = x*x + 3;\n'
                'int z = y*x + 12345;\n'
                'int w = z*z + x - y;\n'
                '}\n')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_function(2)
    assert output == expected


def test_print_function_onecallchain(resources):
    test_file = os.path.join(resources, 'onecallchain.pbtxt')
    expected_2 = ('void function_2() {\n'
                  'label74:;\n'
                  'int x = 1;\n'
                  'int y = x*x + 3;\n'
                  'int z = y*x + 12345;\n'
                  'int w = z*z + x - y;\n'
                  'function_3();\n'
                  '}\n')
    expected_3 = ('void function_3() {\n'
                  'label71:;\n'
                  'int x = 1;\n'
                  'int y = x*x + 3;\n'
                  'int z = y*x + 12345;\n'
                  'int w = z*z + x - y;\n'
                  'function_4();\n'
                  '}\n')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    assert cfg.format_function(2) == expected_2
    assert cfg.format_function(3) == expected_3


def test_get_formatted_headers_onefunction(resources):
    test_file = os.path.join(resources, 'onefunction.pbtxt')
    expected = 'void function_19();\n'
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_headers()
    assert output == expected


def test_indirect_branch_multitarget(resources):
    test_file = os.path.join(resources,
                             'branch_indirect_call_multitarget.pbtxt')
    blocks.Branch.set_seed(0)
    expected = (
        'static int index_1034 = 0;\n'
        'static int paths_1034[16] = {1,1,0,0,1,0,1,0,0,1,1,1,0,1,1,0};\n'
        'static void* array_1034[] = {&function_3, &function_4};\n'
        'void (*f_1034)(void) = array_1034[paths_1034[index_1034++ % 16]];\n'
        'f_1034();\n')

    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg._format_branch_indirect_call(
        cfg.get_function(2).code_blocks[0].terminator_branch, uuid=1034)
    assert output == expected
