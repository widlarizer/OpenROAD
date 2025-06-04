import importlib.util
import re
import sys

spec = importlib.util.spec_from_file_location("extract_proc", "docs/src/scripts/extract_utils.py")
extract_utils = importlib.util.module_from_spec(spec)
sys.modules["extract_utils"] = extract_utils
spec.loader.exec_module(extract_utils)
# extract

def prettify(s):
    s = re.sub(r'\\\n', '', s)
    s = re.sub(r' +', ' ', s)
    s = s.strip()
    return s

def unbrace(s):
    s = re.search(r'\{(.*)\}', s).group(1)
    s = s.split()
    return s

# def pair_up(l):
#     assert len(l) % 2 != 1, f"unexpected odd length {len(l)} of arglist {l}"
#     l = zip(l[::2], l[1::2])
#     return l

# def extract_args
with open('src/sta/sdc/Sdc.tcl') as f:
    known_keys = set()
    known_flags = set()
    extracted = extract_utils.extract_proc(f.read())
    for signature in extracted:
        assert len(signature) == 3 or len(signature) == 4, f"unexpected signature length {len(signature)} of signature {signature}"
        name = signature[0]
        keys = signature[1]
        flags = signature[2]
        checker = False
        if len(signature) == 4:
            checker = 'off' in signature[3]
        if checker:
            print(f"Skipping {name}")
        name, keys, flags = prettify(name), prettify(keys), prettify(flags)
        keys, flags = unbrace(keys), unbrace(flags)
        print(name)
        for key in keys:
            known_keys.add(key)
        for flag in flags:
            known_flags.add(flag)
        print(keys)
        print(flags)
    print(sorted(list(known_keys)))
    print(sorted(list(known_flags)))
