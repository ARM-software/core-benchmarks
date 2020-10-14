# pylint: disable=redefined-outer-name
"""Tests for blocks.py"""
import pytest
from frontend.code_generator import blocks


@pytest.fixture
def fallthrough():
    return blocks.Branch(blocks.BranchType.FALLTHROUGH)


def test_branch():
    br = blocks.Branch(blocks.BranchType.DIRECT,
                       targets=['A', 'B', 'C'],
                       taken_probability=[0.3, 0.3, 0.4])
    assert br.targets == [('A', 0.3), ('B', 0.3), ('C', 0.4)]


def test_branch_filter_single_true(fallthrough):
    filt = blocks.Branch.filter(blocks.BranchType.FALLTHROUGH)
    assert filt(fallthrough)


def test_branch_filter_single_false(fallthrough):
    filt = blocks.Branch.filter(blocks.BranchType.INDIRECT)
    assert not filt(fallthrough)


def test_branch_filter_multiple_true(fallthrough):
    filt = blocks.Branch.filter(
        [blocks.BranchType.INDIRECT, blocks.BranchType.FALLTHROUGH])
    assert filt(fallthrough)


def test_branch_filter_multiple_false(fallthrough):
    filt = blocks.Branch.filter(
        [blocks.BranchType.INDIRECT, blocks.BranchType.DIRECT])
    assert not filt(fallthrough)
