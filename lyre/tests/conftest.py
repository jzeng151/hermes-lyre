"""Make the plugin directory importable as the package ``lyre``.

The tests live inside the plugin (lyre/tests/), so the plugin's parent folder goes on
sys.path. Hermes imports the plugin under its own namespace; that does not matter here
because the formatter and hook have no Hermes imports.
"""

import sys
from pathlib import Path

_PLUGIN_PARENT = Path(__file__).resolve().parents[2]
if str(_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_PARENT))
