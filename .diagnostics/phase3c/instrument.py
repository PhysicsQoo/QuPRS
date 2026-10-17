#!/usr/bin/env python3
"""Diagnostic-only patcher for disposable exported QuPRS trees. Never time these builds in ABBA.
Usage: python3 instrument.py SOURCE_DIR
Snapshots scan phase keys; timing includes nested observation overhead, but excludes end
snapshot/JSON formatting. get_used_vars retains every original call and scan.
"""
import pathlib, sys, shutil
root = pathlib.Path(sys.argv[1]).resolve()
if (root / '.git').exists():
    raise SystemExit('Refusing Git checkout/worktree; export a disposable source tree first')
src = root / 'rust/pathsum/src'
if not src.exists():
    src = root / 'src'

def edit(file, fn):
    p = src / file
    s = p.read_text()
    if 'crate::attribution::' in s or 'mod attribution;' in s:
        raise SystemExit(f'already instrumented: {p}')
    p.write_text(fn(s))

def function(s, signature, begin='', end=''):
    start = s.index(signature)
    op = s.index('{', start)
    # Rust function bodies here contain no unmatched braces inside strings/comments.
    depth = 1
    i = op + 1
    while depth:
        if s[i] == '{': depth += 1
        elif s[i] == '}': depth -= 1
        i += 1
    return s[:op+1] + '\n' + begin + s[op+1:i-1] + end + '\n' + s[i-1:]

edit('lib.rs', lambda s: function(s, 'pub fn check_equivalence(', '    let _attribution_run = crate::attribution::RunScope::new();\n') + '\nmod attribution;\n')
def encoding(s):
    old='wmc_mgr.encode_trace(&ps_miter);'
    assert s.count(old)==1
    return s.replace(old, 'let attribution_encode_start = Instant::now();\n        '+old+'\n        crate::attribution::encoding(attribution_encode_start.elapsed().as_nanos());')
p=src/'lib.rs';p.write_text(encoding(p.read_text()))
edit('ir.rs', lambda s: function(s, 'pub fn apply(', '        crate::attribution::gate_begin(ps, is_bra);\n', '        crate::attribution::gate_end(ps, is_bra);\n'))
def reduction(s):
    s = function(s, 'pub fn full_reduce(', end='        crate::attribution::reduce_end(_attribution_reduce, self);\n')
    marker = 'if !self.stats.is_enabled() {\n            return;\n        }'
    assert s.count(marker) == 1
    s = s.replace(marker, marker + '\n        let _attribution_reduce = crate::attribution::reduce_begin(self);')
    s = s.replace('while reduced {', 'while reduced {\n            crate::attribution::sample(self);')
    s = function(s, 'pub fn try_reduce_elim(', '        let _attribution_elim = crate::attribution::ElimSpan::new();\n')
    for rule in ('Elim', 'HH', 'Omega'):
        for kind in ('attempt', 'success'):
            marker = f'self.stats.record_{kind}(RuleType::{rule});'
            assert marker in s
            s = s.replace(marker, marker + f'\n        crate::attribution::rule({("Elim", "HH", "Omega").index(rule)}, {str(kind == "success").lower()});')
    return s
edit('reduction.rs', reduction)
def phase(s):
    s = function(s, 'pub fn get_used_vars(', '        let mut _attribution_used = crate::attribution::UsedSpan::new(self.terms.len());\n')
    marker = 'for mono in self.terms.keys() {\n            used_vars.extend'
    assert marker in s
    return s.replace(marker, 'for mono in self.terms.keys() {\n            _attribution_used.entries(mono.len());\n            used_vars.extend', 1)
edit('pathsum/phase_poly.rs', phase)
shutil.copyfile(pathlib.Path(__file__).with_name('attribution.rs'), src / 'attribution.rs')
print(src)
