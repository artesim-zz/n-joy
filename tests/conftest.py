import collections
import pytest
import njoy_core.core.model

collect_ignore = ["njoy_core/core/model/test_device.py",
                  "njoy_core/core/test_actuators.py",
                  "njoy_core/core/test_core.py",
                  "njoy_core/core/test_core_controls.py",
                  "njoy_core/core/test_input_buffers.py",
                  "njoy_core/input_node/test_input_node.py"]


def pytest_runtest_setup(item):
    if "ensure_clean_input_node_cache" in item.keywords:
        njoy_core.core.model.InputNode.__NODES__ = collections.defaultdict(list)
    if "ensure_clean_output_node_cache" in item.keywords:
        njoy_core.core.model.OutputNode.__NODES__ = collections.defaultdict(list)
