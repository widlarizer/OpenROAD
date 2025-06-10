import importlib.util
import re
import sys
from enum import Enum
from dataclasses import dataclass

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
err_flags = {'-hierarchical', '-regexp'}
ok_flags = {
    '-add',
    '-all',
    '-allow_paths',
    '-async_pins',
    '-asynchronous',
    '-cell_check',
    '-cell_delay',
    '-cells',
    '-clock',
    '-clock_fall',
    '-clock_path',
    '-clock_pins',
    '-combinational',
    '-compatible',
    '-data',
    '-data_path',
    '-data_pins',
    '-default',
    '-dont_scale',
    '-early',
    '-echo',
    '-edge_triggered',
    '-end',
    '-fall',
    '-group',
    '-gzip',
    '-high',
    '-hold',
    '-invert',
    '-late',
    '-level_sensitive',
    '-logically_exclusive',
    '-low',
    '-map_hpins',
    '-max',
    '-min',
    '-net_delay',
    '-no_clocks',
    '-no_design_rule',
    '-no_timestamp',
    '-nocase',
    '-output_pins',
    '-physically_exclusive',
    '-pin_load',
    '-quiet',
    '-reset_path',
    '-rise',
    '-setup',
    '-source',
    '-start',
    '-subtract_pin_load',
    '-verbose',
    '-wire_load',
}
known_flags = ok_flags | err_flags

class ObjTypes(Enum):
    CELL = 'cell'
    PIN = 'pin'
    NET = 'net'
    PORT = 'port'
    CLOCK = 'clock'
    LIBRARY = 'library'
    LIBRARY_CELL = 'library_cell'
    LIBRARY_PIN = 'library_pin'
    TIMING_ARC = 'timing_arc'

typed_tracked_keys = {
    '-cell': ObjTypes.CELL,
    '-clock': ObjTypes.CLOCK,
    '-fall_clock': ObjTypes.CLOCK,
    '-from_pin': ObjTypes.PIN,
    '-lib_cell': ObjTypes.CELL,
    '-master_clock': ObjTypes.CLOCK,
    '-pin': ObjTypes.PIN,
    '-rise_clock': ObjTypes.CLOCK,
    '-source': ObjTypes.PIN,
}

untyped_tracked_keys = {
    '-fall_from',
    '-fall_to',
    '-from',
    '-object_list',
    '-of_objects',
    '-rise_from',
    '-rise_to',
    '-to',
}
untracked_keys = {
    '-analysis_type',
    '-capacitance',
    '-comment',
    '-corner',
    '-critical_range',
    '-current',
    '-digits',
    '-distance',
    '-divide_by',
    '-duty_cycle',
    '-edge_shift',
    '-edges',
    '-encoding',
    '-hold',
    '-hsc',
    '-input_transition_fall',
    '-input_transition_rise',
    '-library',
    '-max',
    '-max_library',
    '-min',
    '-min_library',
    '-multiply_by',
    '-name',
    '-period',
    '-power',
    '-process',
    '-resistance',
    '-setup',
    '-significant_digits',
    '-temperature',
    '-time',
    '-type',
    '-voltage',
    '-waveform',
    '-weight',
}
err_keys = {'-filter'}
known_keys = untracked_keys | typed_tracked_keys.keys() | untyped_tracked_keys | err_keys
decl_proc_name_res = {
    # r'unset_.*',
    r'set_.*_delay',
}

@dataclass
class ProcSignature:
    name: str
    keys: list[tuple[str, str]]
    flags: list[str]
    positionals: int = None


def get_parsers(file):
    extracted = extract_utils.extract_proc(file)
    signatures = []
    for signature in extracted:
        assert len(signature) == 3 or len(signature) == 4, f"unexpected signature length {len(signature)} of signature {signature}"
        name = signature[0]
        keys = signature[1]
        flags = signature[2]
        checker = False
        if len(signature) == 4:
            checker = 'off' in signature[3]
        if checker:
            sys.stderr.write(f"Skipping {name}")
        name, keys, flags = prettify(name), prettify(keys), prettify(flags)
        keys, flags = unbrace(keys), unbrace(flags)
        unknown_keys = set()
        unknown_flags = set()

        for flag in flags:
            if flag not in known_flags:
                unknown_flags.add(flag)
                sys.stderr.write(f"# WARNING: unknown flag {flag} in {name}, skipping")
                continue

        for key in keys:
            if key not in known_keys:
                unknown_keys.add(key)
                sys.stderr.write(f"# WARNING: unknown key {key} in {name}, skipping")
                continue
        signatures.append(ProcSignature(name, keys, flags, None))
    return signatures

def write_ys_stubs(signatures):
    s = ""
    for sig in signatures:
        s += f'proc {sig.name} {{ args }} {{\n'
        s += f'  sta::parse_key_args "{sig.name}" args keys {{{' '.join(sig.keys)}}} \\\n'
        s += f'  flags {{{' '.join(sig.flags)}}}\n'

        for key in sig.keys:
            if key in typed_tracked_keys:
                type = typed_tracked_keys[key].value
                s += f'  if [info exists keys({key})] {{\n'
                s += f'    ys_track_typed_key {key} $keys({key}) {type} {sig.name}\n'
                s += f'  }}\n'

            if key in untyped_tracked_keys:
                s += f'  if [info exists keys({key})] {{\n'
                s += f'    ys_track_untyped_key {key} $keys({key}) {sig.name}\n'
                s += f'  }}\n'

            if key in err_keys:
                s += f'  if [info exists keys({key})] {{\n'
                s += f'    ys_err_key {key} $keys({key}) {sig.name}\n'
                s += f'  }}\n'
                pass

        for flag in sig.flags:
            if flag in err_flags:
                s += f'  if [info exists flag({flag})] {{\n'
                s += f'    ys_err_flag {flag} $flags({flag}) {sig.name}\n'
                s += f'  }}\n'

        # TODO positionals

        s += f'}}\n'
    return s

def process_doc_decl(doc_args):
    keys = []
    flags = []
    positionals = 0
    for arg in re.findall(r'\[[^\]]+\]', doc_args):
        assert(arg[0] == '[')
        assert(arg[-1] == ']')
        arg_split = arg[1:-1].split(' ')
        if len(arg_split) == 2:
            key, _ = arg_split
            keys.append(key)
        elif len(arg_split) == 1:
            flag = arg_split[0]
            flags.append(flag)
        else:
            sys.stderr.write(f"confusing {arg_split}")
            exit(1)
    for arg in prettify(doc_args).split():
        if ']' not in arg and '[' not in arg:
            positionals += 1
    return (keys, flags, positionals)

def is_doc_decl_defined(proc_name):
    for r in decl_proc_name_res:
        if re.match(r, proc_name):
            return True
    return False

def extract_doc_decls(file):
    unprocessed = []
    for name, thing in extract_utils.extract_help(file):
        if is_doc_decl_defined(name):
            unprocessed.append((name, thing.strip()))
    return unprocessed

def get_doc_decls(unprocessed):
    signatures = []
    for name, s in unprocessed:
        signatures.append(ProcSignature(name, *process_doc_decl(s)))
    return signatures

def fixup_positionals(unprocessed, old_signatures):
    new_signatures = old_signatures.copy()
    for name, s in unprocessed:
        for sig in new_signatures:
            if sig.name == name:
                # keys, flags, positionals = thing
                if is_doc_decl_defined(name):
                    continue
                assert sig.positionals == None, f"Already resolved positionals for {name}"
                new_sig = sig
                _, _, new_sig.positionals = process_doc_decl(s)
                new_signatures.append(new_sig)
    return new_signatures

def main():
    stub_file = ""
    with open('src/sta/sdc/Sdc.tcl') as f:
        stub_file = f.read()
    signatures = []
    signatures += get_parsers(stub_file)
    doc_decls = extract_doc_decls(stub_file)
    signatures += get_doc_decls(doc_decls)
    signatures = fixup_positionals(doc_decls, signatures)
    print(write_ys_stubs(signatures))

main()
