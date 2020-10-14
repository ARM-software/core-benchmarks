# pylint: disable=redefined-outer-name
"""Tests for user_callgraph.py"""
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
    test_file = os.path.join(resources, 'onecallchain.pbtext')
    expected = ('void function_2();\n'
                'void function_3();\n'
                'void function_4();\n'
                'void function_5();\n'
                'void function_6();\n')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_headers()
    assert output == expected


def test_load_onecallchain(resources):
    test_file = os.path.join(resources, 'onecallchain.pbtext')
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
    test_file = os.path.join(resources, 'onefunction.pbtext')
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    assert isinstance(cfg, user_callgraph.Callgraph)
    assert len(cfg.functions) == 1
    assert cfg.entry_point == 2


def test_print_function_onefunction(resources):
    test_file = os.path.join(resources, 'onefunction.pbtext')
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
    test_file = os.path.join(resources, 'onecallchain.pbtext')
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


@pytest.mark.parametrize('seed,function', [(1, 5), (2, 6)])
def test_print_branch_indirect_call(resources, seed, function):
    test_file = os.path.join(resources, 'onecallchain.pbtext')
    expected = ('void function_4() {\n'
                'label72:;\n'
                'int x = 1;\n'
                'int y = x*x + 3;\n'
                'int z = y*x + 12345;\n'
                'int w = z*z + x - y;\n'
                f'void (*frontend_f)(void) = function_{function};\n'
                'frontend_f();\n'
                '}\n')
    blocks.Branch.set_seed(seed)
    cfg = user_callgraph.Callgraph.from_proto(test_file)
    output = cfg.format_function(4)
    assert output == expected
