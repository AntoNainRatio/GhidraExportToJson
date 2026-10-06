# Export all decompiled functions to JSON for SiftRank
# @category Export

import json
import os
import re
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.util.exception import CancelledException

DEFAULT_MAX_CODE_SIZE = 8000
OVERLAP_LINES = 2

_STRING_RE = re.compile(r'"(\\.|[^"\\])*"|\'(\\.|[^\'\\])*\'')

def brace_delta(line):
    line = _STRING_RE.sub('""', line)
    return line.count("{") - line.count("}")

def split_header(lines):
    # Header = signature, "{" and the local variable declarations (ends at the first blank line after "{")
    brace = None
    for i, line in enumerate(lines):
        if "{" in line:
            brace = i
            break
    if brace is None:
        return [], lines
    end = brace + 1
    for i in range(brace + 1, len(lines)):
        if not lines[i].strip():
            end = i + 1
            break
    else:
        end = brace + 1
    return lines[:end], lines[end:]

def split_code(code, budget):
    """Split decompiled C into chunks of at most ~budget chars, cutting at the shallowest
    brace depth possible. Each chunk repeats the header (signature + local declarations)."""
    lines = code.splitlines()
    header, body = split_header(lines)
    header_text = "\n".join(header)
    if len(header_text) > budget // 2:
        header = lines[:1]
        header_text = "\n".join(header)
        body = lines[1:]

    # depth[i] = brace depth before body[i] (function's own "{" is in the header, so top level = 1)
    depth = []
    d = 1 if any("{" in l for l in header) else 0
    for line in body:
        depth.append(d)
        d += brace_delta(line)

    room = max(budget - len(header_text) - 120, 200)
    chunks = []
    start = 0
    while start < len(body):
        size = 0
        end = start
        best = None  # (depth, end): cut before body[end]
        while end < len(body):
            size += len(body[end]) + 1
            if size > room and end > start:
                break
            end += 1
            if end < len(body) and (best is None or depth[end] <= best[0]):
                best = (depth[end], end)
        if end < len(body) and best is not None:
            end = best[1]
        chunks.append((start, end))
        start = end

    result = []
    n = len(chunks)
    for i, (a, b) in enumerate(chunks):
        parts = list(header)
        if i > 0:
            parts.append("  /* ... previous part ... */")
            parts.extend(body[max(a - OVERLAP_LINES, 0):a])
            parts.append("  /* --- part {}/{} starts here --- */".format(i + 1, n))
        parts.extend(body[a:b])
        if i < n - 1:
            parts.append("  /* ... continued in part {}/{} ... */".format(i + 2, n))
        result.append("\n".join(parts))
    return result

def ask_max_code_size():
    # Script args (e.g. headless: ExportToSiftrank.py 4000) take precedence over the prompt
    args = getScriptArgs()
    if args:
        return int(args[0])
    try:
        return askInt("Max function size",
                      "Split functions whose decompiled code exceeds N characters (0 = never split, keep huge functions whole; suggested {}):".format(DEFAULT_MAX_CODE_SIZE))
    except CancelledException:
        return DEFAULT_MAX_CODE_SIZE

def skip_entry(func, reason):
    return {
        "name": func.getName(),
        "address": "0x" + func.getEntryPoint().toString(),
        "reason": reason
    }

def run():
    max_code_size = ask_max_code_size()
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    functions = []
    func_manager = currentProgram.getFunctionManager()
    all_funcs = func_manager.getFunctions(True)

    count = 0
    skipped = []
    split = 0

    for func in all_funcs:
        if func.isThunk() or func.isExternal():
            skipped.append(skip_entry(func, "external" if func.isExternal() else "thunk"))
            continue

        result = decompiler.decompileFunction(func, 30, monitor)
        if result is not None and result.decompileCompleted():
            code = result.getDecompiledFunction().getC()

            name = func.getName()
            address = "0x" + func.getEntryPoint().toString()
            signature = func.getPrototypeString(False, True)

            if max_code_size > 0 and len(code) > max_code_size:
                chunks = split_code(code, max_code_size)
                for i, chunk in enumerate(chunks):
                    functions.append({
                        "name": "{}#part{}".format(name, i + 1),
                        "address": address,
                        "signature": signature,
                        "part": i + 1,
                        "parts": len(chunks),
                        "code": chunk
                    })
                split += 1
            else:
                functions.append({
                    "name": name,
                    "address": address,
                    "signature": signature,
                    "code": code
                })
            count += 1
        else:
            reason = "decompile failed"
            if result is not None and result.getErrorMessage():
                reason += ": " + result.getErrorMessage()
            skipped.append(skip_entry(func, reason))

    out_dir = os.path.expanduser("~/siftrank_exports")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    program_name = currentProgram.getName()
    out_path = os.path.join(out_dir, program_name + "_functions.json")

    with open(out_path, "w") as f:
        json.dump(functions, f, indent=2)

    skipped_path = os.path.join(out_dir, program_name + "_skipped.json")
    with open(skipped_path, "w") as f:
        json.dump(skipped, f, indent=2)

    for s in skipped:
        print("Skipped {} ({}): {}".format(s["name"], s["address"], s["reason"]))
    print("Exported {} entries from {} functions ({} split into parts, {} skipped) to {}".format(
        len(functions), count, split, len(skipped), out_path))
    print("Skipped functions listed in {}".format(skipped_path))

run()
