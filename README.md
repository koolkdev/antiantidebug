# Themida Code Virtualizer Research Notes

This repository contains legacy Python research code for studying Themida's Code
Virtualizer protection, with a focus on devirtualizing protected code back into
native code. The work includes VM handler analysis, instruction cleanup, and
VM-to-native code reconstruction. The unpacking code was mostly
experimental and incomplete.

The code is kept for archival and research purposes. It reflects an older
workflow and dependency stack, and it is not maintained as a production-ready
library or ready-to-run tool.

## Scope

The project includes:

- Code Virtualizer VM handler parsing and cleanup logic
- VM instruction models and template-based transformation passes
- VM-to-native code reconstruction helpers
- mapped PE file abstractions for reading and patching executable images
- experimental Themida unpacking and deobfuscation helpers
- debugger helpers used by the research workflow

Most modules were written as research tooling. Some code paths assume a
Windows reverse-engineering environment and Python 2-era dependencies.

Use this code at your own risk. It is provided as-is, without support,
warranty, or guarantees of correctness.

## Targeted Versions

The code targets legacy Themida 2.x-era virtual machines, up to Themida 2.4.x,
with partial support for older CISC VM variants.

## Repository Layout

- `themida/` - experimental Themida unpacking and Oreans deobfuscation helpers
- `vms/codevirtualizer/` - Code Virtualizer VM models, handlers, and decoders
- `vms/templates/` - template definitions and generation helpers for cleanup
- `vms/vmtools.py` - shared VM discovery and devirtualization helpers
- `mappedfile.py`, `idamappedfile.py` - mapped binary access helpers
- `debugger.py` - debugger wrapper used by some workflows

## License

This project is licensed under the MIT License.
