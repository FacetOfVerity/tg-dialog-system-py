import tests.routing.sample_handlers as sample
from tg_dialog_system.routing.discovery import discover_handlers


def test_discover_imports_all_submodules():
    # Importing the package alone does not import feature.py; discovery must.
    discover_handlers(sample)
    lookup = sample.feature.REGISTRY.get_command("/from_discovery")
    assert lookup.is_ok()
