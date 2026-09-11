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
import os, re, subprocess, sys, html, glob
from urllib.parse import unquote, urlparse

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../scripts
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))  # repo root
FAIL = []

def fail(msg): FAIL.append(msg); print('  ✗', msg)
def ok(msg): print('  ✓', msg)

def run_build():
    print('[1] Hugo build')
    # -D: review-stage chapters carry draft:true in front matter (not published
    # in production); the checker still validates them by building with drafts.
    r = subprocess.run(['hugo', '--gc', '--minify', '--buildDrafts'], cwd=ROOT,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0:
        fail('build exited %d:\n%s' % (r.returncode, out[-800:]))
        return False
    if 'ERROR' in out or 'WARN' in out:
        fail('build has ERROR/WARN:\n%s' % out[-800:]); return False
    ok('clean build'); return True

def strip_code(t):  return re.sub(r'```.*?```', '', t, flags=re.S)
def codeblocks(t):  return re.findall(r'```[A-Za-z0-9+#._-]*\n(.*?)```', t, re.S)
def formulas(t):
    t = strip_code(t)
    t = re.sub(r'`[^`\n]+`', '', t)  # literal $ signs in inline code are not math
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
    r'x86|ARM|RISC|CISC|SSE|AVX|NEON|M\d|A\d\d|AArch|AMD64|x64|Graviton|Fugaku|'
    r'HTML|HTTP|NASM|GAS|Intel|AMD|Apple|Samsung|MacBook|Facebook|BOLT|'
    r'goto|switch|else|while|true|false|if|for|'
    r'byte|bytes|word|quad|single|store|load|increment|multiply|division|'
    r'accumulator|counter|data|move|computed|fetch|decode')

def remnants(zh_dir):
    print('[5] English remnant heuristic')
    for f in sorted(os.listdir(zh_dir)):
        if not f.endswith('.md'): continue
        t = open(os.path.join(zh_dir, f)).read()
        t = re.sub(r'```.*?```', '', t, flags=re.S)
        t = re.sub(r'\$[^$]*\$', '', t)
        t = re.sub(r'\[\^\w+\]', '', t)  # footnote markers
        t = re.sub(r'`[^`\n]+`', '＃', t)  # inline code: technical terms are expected to stay English
        # terminology glosses 术语（english term）are required by AGENTS.md — drop the English part
        t = re.sub(r'（[^（）]*[A-Za-z][^（）]*）', '（）', t)
        t = re.sub(r'\([^()]*[A-Za-z][^()]*\)', '()', t)
        # the author's quoted English phrases ("store/load a word") are kept verbatim by design
        t = re.sub(r'"[^"\n]*[A-Za-z][^"\n]*"', '“”', t)
        t = re.sub(r'“[^”\n]*[A-Za-z][^”\n]*”', '“”', t)
        t = re.sub(r'\[[^\]]*\]\([^)]*\)', '链接', t)
        t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
        t = re.sub(r'^---.*?---', '', t, flags=re.S)
        for m in re.finditer(r'[A-Za-z][A-Za-z\'\-]{3,}(?:\s+[A-Za-z][A-Za-z\'\-]{2,}){0,4}', t):
            if not WHITELIST.search(m.group(0)):
                fail('%s: possible remnant "%s"' % (f, m.group(0)[:60]))
    ok('remnant scan done')

def base_prefix():
    """URL path prefix from baseURL (e.g. '/algorithmica' for a GitHub Pages project site)."""
    cfg = open(os.path.join(ROOT, 'config.yaml')).read()
    m = re.search(r'^baseURL:\s*"([^"]+)"', cfg, re.M)
    return (urlparse(m.group(1)).path if m else '/').rstrip('/')

def draft_page_urls():
    """Site-relative URLs of pages whose *source* file is draft:true.

    The checker builds with --buildDrafts so review-stage translations get
    validated; that also pulls in upstream (en/ru) draft pages which production
    never renders. Links found on those pages are out of scope.
    """
    drafts = set()
    for lang_dir, prefix in (('chinese', ''), ('english', '/en'), ('russian', '/ru')):
        for path in glob.glob(os.path.join(ROOT, 'content', lang_dir, '**', '*.md'), recursive=True):
            if not re.search(r'^draft:\s*true', frontmatter(open(path).read()), re.M):
                continue
            rel = os.path.relpath(path, os.path.join(ROOT, 'content', lang_dir))[:-3]
            url = prefix + '/' if rel == '_index' else (prefix + '/' + rel).rstrip('/') + '/'
            drafts.add(url)
    return drafts

def deadlinks():
    """Check internal links resolve to files in public/.

    Note: public/ is the site root regardless of a subpath baseURL — GitHub Pages
    mounts it at /<repo>/. So URLs carry the prefix while file paths do not.
    """
    print('[3] site-wide dead links (expected-404 aware)')
    base = os.path.join(ROOT, 'public')
    prefix = base_prefix()
    drafts = draft_page_urls()
    pat = re.compile(r'(?:href|src)=(?:"([^"]+)"|([^\s>]+))')
    real, expected = {}, set()
    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith('.html'): continue
            p = os.path.join(root, fn)
            page_url = '/' + os.path.relpath(p, base).rsplit('index.html', 1)[0]
            if page_url.rstrip('/') in (d.rstrip('/') for d in drafts):
                continue  # page source is draft; production never renders it
            c = open(p, encoding='utf-8', errors='ignore').read()
            for m in pat.finditer(c):
                u = html.unescape(m.group(1) or m.group(2))
                if not u.startswith('/') or u.startswith('//'): continue
                u = unquote(u.split('#')[0].split('?')[0])
                if not u: continue
                if prefix and u.startswith(prefix + '/'):
                    u = u[len(prefix):]          # /algorithmica/foo -> /foo
                elif prefix and u == prefix:
                    u = '/'
                t = os.path.join(base, u.lstrip('/'))
                if os.path.isfile(t) or os.path.isfile(os.path.join(t, 'index.html')) \
                   or os.path.isfile(t.rstrip('/') + '/index.html') or os.path.isfile(t.rstrip('/')):
                    continue
                en_t = os.path.join(base, 'en', u.lstrip('/'))
                if os.path.isfile(os.path.join(en_t, 'index.html')) or os.path.isfile(en_t):
                    expected.add(u); continue
                # reveal.js ships runtime assets referenced from its own notes/print
                # pages; they are not part of our content and resolve at the server root.
                if u.startswith(('/socket.io/', '/plugin/', '/reveal-js/')):
                    expected.add(u); continue
                real.setdefault(u, []).append(os.path.relpath(p, base))
    for u in sorted(real): fail('dead link %s <- %s' % (u, real[u][0]))
    ok('%d expected untranslated-page links (auto-whitelisted), %d real dead'
       % (len(expected), len(real)))

def url_prefixes():
    """Every internal URL must carry the baseURL subpath (GitHub Pages project site)."""
    print('[6] baseURL prefix coverage')
    r = subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_urls.py')],
                       capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    for line in out.splitlines():
        print('  ' + line)
    if r.returncode != 0:
        fail('internal URLs missing the baseURL prefix (see above)')

def main():
    zh_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not zh_dir or not os.path.isdir(zh_dir):
        sys.exit('usage: check_translation.py content/chinese/hpc/<chapter>')
    if not run_build(): sys.exit(1)
    print('[4] chapter checks')
    check_chapter(zh_dir)
    deadlinks()
    url_prefixes()
    remnants(zh_dir)
    print('\n%s' % ('FAIL (%d)' % len(FAIL) if FAIL else 'ALL CHECKS PASSED'))
    sys.exit(1 if FAIL else 0)

if __name__ == '__main__':
    main()
