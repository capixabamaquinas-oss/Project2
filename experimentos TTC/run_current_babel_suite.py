import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True
BABEL_DIR = pathlib.Path(r"C:\OllamaLimit\Sei lá\Projeto TTC\Babel TTC")
test_path = BABEL_DIR / "test_babel.py"
spec = importlib.util.spec_from_file_location(
    "babel", BABEL_DIR / "__init__.py",
    submodule_search_locations=[str(BABEL_DIR)],
)
pkg = importlib.util.module_from_spec(spec)
sys.modules["babel"] = pkg
spec.loader.exec_module(pkg)
ts = importlib.util.spec_from_file_location("test_babel", test_path)
tm = importlib.util.module_from_spec(ts)
ts.loader.exec_module(tm)
suite = unittest.defaultTestLoader.loadTestsFromModule(tm)
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
print(f"SUITE_RESULT tests={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} skipped={len(result.skipped)}")
sys.exit(0 if result.wasSuccessful() else 1)
