#!/usr/bin/env python3
"""Verify every site-internal URL in the built output carries the baseURL prefix.

Motivation: the site deploys to a GitHub Pages *project* site, so it lives at
/<repo>/ (e.g. /algorithmica/). Hugo does NOT rewrite root-absolute paths that
appear verbatim in templates or content — `relURL` does, but it returns
leading-slash inputs unchanged, so arguments must omit the slash. Forgetting
either rule silently produces links that 404 in production while working fine
under `hugo serve` (which serves from the site root). This script catches that
class of bug before deploy.

Run after a build:  python3 check_urls.py
Exit code 1 if any internal link lacks the prefix.
"""
import os, re, sys, html

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
PUBLIC = os.path.join(ROOT, 'public')

# reveal.js runtime assets referenced by its own notes/print pages
WHITELIST = ('/socket.io/', '/plugin/', '/reveal-js/')

def base_prefix():
    from urllib.parse import urlparse
    cfg = open(os.path.join(ROOT, 'config.yaml')).read()
    m = re.search(r'^baseURL:\s*"([^"]+)"', cfg, re.M)
    return (urlparse(m.group(1)).path if m else '/').rstrip('/')

def main():
    if not os.path.isdir(PUBLIC):
        sys.exit('public/ not found — run `hugo` first')
    prefix = base_prefix()
    if not prefix:
        print('baseURL has no subpath; nothing to check')
        return 0
    pat = re.compile(r'(?:href|src)=(?:"([^"]+)"|([^\s>]+))')
    bad = {}
    total = 0
    for root, _, files in os.walk(PUBLIC):
        for fn in files:
            if not fn.endswith('.html'): continue
            p = os.path.join(root, fn)
            c = open(p, encoding='utf-8', errors='ignore').read()
            for m in pat.finditer(c):
                u = html.unescape(m.group(1) or m.group(2))
                if not u.startswith('/') or u.startswith('//'): continue
                total += 1
                if u.startswith(prefix + '/') or u == prefix: continue
                if u.startswith(WHITELIST): continue
                bad.setdefault(u, []).append(os.path.relpath(p, PUBLIC))
    print(f'checked {total} internal URLs against prefix "{prefix}"')
    if bad:
        print(f'FAIL: {len(bad)} URL(s) missing the baseURL prefix:')
        for u in sorted(bad): print(f'  {u}  <- {bad[u][0]}')
        return 1
    print('OK: every internal URL carries the prefix')
    return 0

if __name__ == '__main__':
    sys.exit(main())
