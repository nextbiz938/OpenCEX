#!/usr/bin/env python3
"""Builds README.md (a GitHub-rendered gallery) from the agents' <LETTER>-captions.md files."""
import pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
SECTIONS = [
    ('A', 'Public site, sign-up and sign-in'),
    ('B', 'Wallet, deposits and withdrawals'),
    ('C', 'Trading and charts'),
    ('D', 'Operator side: admin panel, queues, mail'),
]
out = ['# OpenCEX test install: screenshot tour', '',
       'Captured from the smoke-test stack (`smoke-test/setup.sh`) on a throwaway VM. '
       'Play money only; no blockchain nodes and no internet inside the containers, so anything '
       'that needs a real chain or a price feed is shown failing honestly.', '']
toc, body = [], []
for letter, title in SECTIONS:
    cap = HERE / f'{letter}-captions.md'
    if not cap.exists():
        continue
    anchor = re.sub(r'[^a-z0-9 -]', '', title.lower()).replace(' ', '-')
    toc.append(f'- [{title}](#{anchor})')
    body += [f'## {title}', '']
    for line in cap.read_text().splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3 or not (HERE / parts[0]).exists():
            continue
        fname, short, caption = parts[0], parts[1], ' | '.join(parts[2:])
        body += [f'### {short}', '', caption, '', f'![{short}]({fname})', '']
out += toc + [''] + body
(HERE / 'README.md').write_text('\n'.join(out))
print(f"wrote README.md with {sum(1 for l in body if l.startswith('!['))} images")
