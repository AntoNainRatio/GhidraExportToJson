# Export all decompiled functions to JSON for SiftRank
# @category Export

import json
import os
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.util.exception import CancelledException

DEFAULT_MAX_CODE_SIZE = 8000

def ask_max_code_size():
    # Script args (e.g. headless: ExportToSiftrank.py 4000) take precedence over the prompt
    args = getScriptArgs()
    if args:
        return int(args[0])
    try:
        return askInt("Max function size",
                      "Skip functions whose decompiled code exceeds N characters (0 = no limit, suggested {}):".format(DEFAULT_MAX_CODE_SIZE))
    except CancelledException:
        return DEFAULT_MAX_CODE_SIZE

def run():
    max_code_size = ask_max_code_size()
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    functions = []
    func_manager = currentProgram.getFunctionManager()
    all_funcs = func_manager.getFunctions(True)

    count = 0
    skipped = 0

    for func in all_funcs:
        if func.isThunk() or func.isExternal():
            skipped += 1
            continue

        result = decompiler.decompileFunction(func, 30, monitor)
        if result is not None and result.decompileCompleted():
            code = result.getDecompiledFunction().getC()

            if max_code_size > 0 and len(code) > max_code_size:
                skipped += 1
                continue

            functions.append({
                "name": func.getName(),
                "address": "0x" + func.getEntryPoint().toString(),
                "signature": func.getPrototypeString(False, True),
                "code": code
            })
            count += 1
        else:
            skipped += 1

    out_dir = os.path.expanduser("~/siftrank_exports")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    program_name = currentProgram.getName()
    out_path = os.path.join(out_dir, program_name + "_functions.json")

    with open(out_path, "w") as f:
        json.dump(functions, f, indent=2)

    print("Exported {} functions ({} skipped) to {}".format(count, skipped, out_path))

run()
