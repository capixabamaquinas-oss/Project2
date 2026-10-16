import importlib,importlib.util,pathlib,sys,os,builtins,typing
builtins.Optional=typing.Optional
sys.dont_write_bytecode=True
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
b=pathlib.Path(sys.argv[1]);spec=importlib.util.spec_from_file_location("babel_probe",b/"__init__.py",submodule_search_locations=[str(b)]);m=importlib.util.module_from_spec(spec);sys.modules["babel_probe"]=m;spec.loader.exec_module(m);cli=importlib.import_module("babel_probe.cli");sys.argv=["babel",*sys.argv[2:]];cli.main()
