from distutils.core import setup
import oreans_deobfuscator_build

setup(
  name = 'oreans deobfuscator',
  py_modules=['oreans_deobfuscator'],
  ext_modules = [oreans_deobfuscator_build.ffi.distutils_extension()],
  install_requires=['cffi']
)
