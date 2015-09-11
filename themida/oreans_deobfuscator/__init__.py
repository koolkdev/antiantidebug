# TODO: Make everything as a module, so compiling this won't be needed
try:
    from oreans_deobfuscator import *
except ImportError:
    from setuptools.sandbox import DirectorySandbox
    from distutils import core
    import os
    import sys
    setup_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(setup_dir)
    try:
        os.unlink("_oreans_deobfuscator.pyd")
    except:
        pass
    old_argv = sys.argv
    sys.argv[:] = ["setup.py", "build_ext", "--inplace"]
    sys.path.insert(0, setup_dir)
    DirectorySandbox(setup_dir).run(
        lambda: execfile(
            "setup.py",
            {'__file__':"setup.py", '__name__':'__main__'}
            )
        )
    sys.path = sys.path[1:]
    sys.argv = old_argv
    from oreans_deobfuscator import *
    