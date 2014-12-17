from distutils.core import setup
from distutils.extension import Extension
#from Cython.Build import cythonize
from Cython.Distutils import build_ext
from distutils.util import get_platform

if get_platform() == "win32":
    folder = "Win32"
elif get_platform() == "win-amd64":
    folder = "x64"
else:
    assert False # Unsupported platform
    
x86utils_dir = r"..\..\..\x86utils"

ext_modules = [Extension("oreans_deobfuscator",
                     sources=["Cleaner.cpp",
                              "deobfuscator.cpp",
                              "oreans_deobfuscator.pyx"],
                     language='c',
                     #define_macros=[('MS_NO_COREDLL', None)],
                     include_dirs=[ r'%s\x86utils' % x86utils_dir, r'%s\libyasm-2.1.2' % x86utils_dir, r'%s\udis86-1.7.2' % x86utils_dir],
                     library_dirs=[r'%s\%s\Release' % (x86utils_dir, folder)],
                     libraries=['x86utils', 'modules', 'libyasm', 'libudis86'],
                     )]
setup(
  name = 'oreans deobfuscator',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules
)
