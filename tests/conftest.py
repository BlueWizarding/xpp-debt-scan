import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fixtures"))

import build_fixture  # noqa: E402


@pytest.fixture(scope="session")
def pld_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("pld")
    return build_fixture.build(str(root))
