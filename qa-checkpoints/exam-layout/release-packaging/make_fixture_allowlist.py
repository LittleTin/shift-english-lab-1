#!/usr/bin/env python3
"""Produce an allowlist for the local synthetic draft, never deployment."""
import json
import sys
from pathlib import Path

p=json.loads((Path(sys.argv[1])/'receipt.json').read_text())
assert p['localCandidateOnly'] and p['version']=='9.9.1', 'Not the local proof'
urls=[x for x,r in p['routes'].items() if r['roles']==['current-pack'] and x.split('/')[:2] in
      (['audio','exams'],['assets','exams'])]
print(json.dumps(sorted(urls),indent=2))
