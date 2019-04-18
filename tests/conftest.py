# pylint: skip-file
import collections
import njoy_core.core.model

collect_ignore = ["njoy_core/input_node/test_hid_event_loop.py"]


def pytest_runtest_setup(item):
    if "ensure_clean_input_node_cache" in item.keywords:
        njoy_core.core.model.InputNode.__NODES__ = collections.defaultdict(list)
    if "ensure_clean_output_node_cache" in item.keywords:
        njoy_core.core.model.OutputNode.__NODES__ = collections.defaultdict(list)
    if "ensure_clean_physical_device_cache" in item.keywords:
        njoy_core.core.model.PhysicalDevice.__ALIAS_INDEX__ = dict()
        njoy_core.core.model.PhysicalDevice.__NAME_INDEX__ = collections.defaultdict(list)
        njoy_core.core.model.PhysicalDevice.__GUID_INDEX__ = dict()
