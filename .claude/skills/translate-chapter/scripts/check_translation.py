#!/usr/bin/env python3
"""Mechanical checks for a translated chapter of the Algorithmica zh fork.

Usage: check_translation.py content/chinese/hpc/<chapter>

Checks:
  1. Hugo build (hugo --gc --minify) passes with no ERROR/WARN
  2. Every non-draft en article in the chapter has a zh counterpart
  3. Code blocks byte-identical (ignoring per-line trailing whitespace)
  4. Math formula ($...$ / $$...$$) sequences identical
  5. front matter: weight/authors preserved; title/part contain CJK
  6. Site-wide dead-link scan: a missing target that exists under /en/
     counts as expected (untranslated future page); otherwise real
  7. English remnant heuristic on the zh chapter files

Exit code 0 iff no real problems.
"""
import os, re, subprocess, sys, html
from urllib.parse import unquote

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../scripts
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))  # repo root
FAIL = []

def fail(msg): FAIL.append(msg); print('  ✗', msg)
def ok(msg): print('  ✓', msg)

def run_build():
    print('[1] Hugo build')
    r = subprocess.run(['hugo', '--gc', '--minify'], cwd=ROOT,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0:
        fail('build exited %d:\n%s' % (r.returncode, out[-800:]))
        return False
    if 'ERROR' in out or 'WARN' in out:
        fail('build has ERROR/WARN:\n%s' % out[-800:]); return False
    ok('clean build'); return True

def strip_code(t):  return re.sub(r'```.*?```', '', t, flags=re.S)
def codeblocks(t):  return re.findall(r'```(?:\w+)?\n(.*?)```', t, re.S)
def formulas(t):
    t = strip_code(t)
    return re.findall(r'\$\$(.+?)\$\$|\$([^\$\n]+?)\$', t, re.S)

def norm_block(b): return '\n'.join(l.rstrip() for l in b.rstrip('\n').splitlines())

def frontmatter(t):
    m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
    return m.group(1) if m else ''

def has_cjk(s): return any('\u4e00' <= c <= '\u9fff' for c in s)

def check_chapter(zh_dir):
    rel = os.path.relpath(zh_dir, ROOT)
    en_dir = os.path.join(ROOT, 'content/english', *rel.split(os.sep)[2:])
    print('[2] file coverage: %s' % rel)
    if not os.path.isdir(en_dir): fail('no en counterpart dir %s' % en_dir); return
    en_files = sorted(f for f in os.listdir(en_dir) if f.endswith('.md'))
    for f in en_files:
        en_t = open(os.path.join(en_dir, f)).read()
        zh_p = os.path.join(zh_dir, f)
        if re.search(r'^draft:\s*true', frontmatter(en_t), re.M):
            print('  - skip draft %s' % f); continue
        if not os.path.isfile(zh_p): fail('missing translation %s' % zh_p); continue
        zh_t = open(zh_p).read()
        print('  checking %s' % f)
        ec, zc = codeblocks(en_t), codeblocks(zh_t)
        if len(ec) != len(zc):
            fail('%s: code block count en=%d zh=%d' % (f, len(ec), len(zc)))
        else:
            for i, (a, b) in enumerate(zip(ec, zc)):
                if norm_block(a) != norm_block(b):
                    fail('%s: code block %d differs' % (f, i))
        ef, zf = formulas(en_t), formulas(zh_t)
        if ef != zf:
            fail('%s: formula sequences differ (en %d vs zh %d), first diff: %r vs %r'
                 % (f, len(ef), len(zf),
                    next((a for a, b in zip(ef, zf) if a != b), None),
                    next((b for a, b in zip(ef, zf) if a != b), None)))
        for key in ('weight', 'authors'):
            mv = re.search(r'^%s:.*$' % key, frontmatter(en_t), re.M)
            zv = re.search(r'^%s:.*$' % key, frontmatter(zh_t), re.M)
            if mv and (not zv or mv.group(0) != zv.group(0)):
                fail('%s: front matter %s changed: %r vs %r' % (f, key, mv.group(0), zv and zv.group(0)))
        for key in ('title', 'part'):
            zv = re.search(r'^%s:\s*(.+)$' % key, frontmatter(zh_t), re.M)
            if zv and not has_cjk(zv.group(1)):
                print('  ! %s: %s has no CJK (check if intended): %s' % (f, key, zv.group(1)))
    ok('chapter checks done')

WHITELIST = re.compile(
    r'cache line|SIMD|CPU|GPU|open-access|HackerNews|CodeForces|Twitter|Prose|ppm|netlify|'
    r'GitHub|issue|pull request|JIT|BLAS|OpenBLAS|numpy|PyPy|bytecode|just-in-time|fork|RAM|'
    r'FPGA|ASIC|VM|nm|Karatsuba|OpenMP|CUDA|kernel|warp|block|actor|all-reduce|MapReduce|'
    r'Cython|Numba|Julia|OpenCL|oneAPI|Verilog|Spark|Rust|Dask|FFT|TLB|L\d|Zen|AMD|Intel|'
    r'Algorithmica|Math|TODO|what you want|University|std::|argmin|popcount|popcnt|scanf|'
    r'sort|find|accumulate|lower_bound|unordered|for-for-for|march|native|ffast-math|'
    r'instruction|latency|pointer|complexity|microchip|scaling|power|fidelity|leakage|managed|'
    r'Python|JavaScript|Ruby|Java|Erlang|Scala|Elixir|Apple|Atari|Commodore|IBM|Windows|Linux|'
    r'NumPy|OpenBLAS|matmul|numpy|pip|venv|JDK|'
    r'float|double|int|char|bool|struct|class|static|void|const|long|short|unsigned|define|include|'
    r'fmla|fmul|fadd|fdiv|scvtf|otool|clang|gcc|GCC|LLVM|'
    r'x86|ARM|RISC|SSE|AVX|NEON|M\d|A\d\d')

def remnants(zh_dir):
    print('[5] English remnant heuristic')
    for f in sorted(os.listdir(zh_dir)):
        if not f.endswith('.md'): continue
        t = open(os.path.join(zh_dir, f)).read()
        t = re.sub(r'```.*?```', '', t, flags=re.S)
        t = re.sub(r'\$[^$]*\$', '', t)
        t = re.sub(r'\[\^\w+\]', '', t)  # footnote markers
        t = re.sub(r'\[[^\]]*\]\([^)]*\)', '链接', t)
        t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
        t = re.sub(r'^---.*?---', '', t, flags=re.S)
        for m in re.finditer(r'[A-Za-z][A-Za-z\'\-]{3,}(?:\s+[A-Za-z][A-Za-z\'\-]{2,}){0,4}', t):
            if not WHITELIST.search(m.group(0)):
                fail('%s: possible remnant "%s"' % (f, m.group(0)[:60]))
    ok('remnant scan done')

def deadlinks():
    print('[3] site-wide dead links (expected-404 aware)')
    base = os.path.join(ROOT, 'public'); origin = 'https://algorithmica-zh.netlify.app'
    pat = re.compile(r'(?:href|src)=(?:"([^"]+)"|([^\s>]+))')
    real, expected = {}, set()
    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith('.html'): continue
            p = os.path.join(root, fn)
            c = open(p, encoding='utf-8', errors='ignore').read()
            for m in pat.finditer(c):
                u = html.unescape(m.group(1) or m.group(2))
                if u.startswith(origin): u = u[len(origin):]
                if not u.startswith('/') or u.startswith('//'): continue
                u = unquote(u.split('#')[0].split('?')[0])
                if not u: continue
                t = os.path.join(base, u.lstrip('/'))
                if os.path.isfile(t) or os.path.isfile(os.path.join(t, 'index.html')) \
                   or os.path.isfile(t.rstrip('/') + '/index.html') or os.path.isfile(t.rstrip('/')):
                    continue
                en_t = os.path.join(base, 'en', u.lstrip('/'))
                if os.path.isfile(os.path.join(en_t, 'index.html')) or os.path.isfile(en_t):
                    expected.add(u); continue
                real.setdefault(u, []).append(os.path.relpath(p, base))
    for u in sorted(real): fail('dead link %s <- %s' % (u, real[u][0]))
    ok('%d expected untranslated-page links (auto-whitelisted), %d real dead'
       % (len(expected), len(real)))

def main():
    zh_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not zh_dir or not os.path.isdir(zh_dir):
        sys.exit('usage: check_translation.py content/chinese/hpc/<chapter>')
    if not run_build(): sys.exit(1)
    print('[4] chapter checks')
    check_chapter(zh_dir)
    deadlinks()
    remnants(zh_dir)
    print('\n%s' % ('FAIL (%d)' % len(FAIL) if FAIL else 'ALL CHECKS PASSED'))
    sys.exit(1 if FAIL else 0)

if __name__ == '__main__':
    main()
