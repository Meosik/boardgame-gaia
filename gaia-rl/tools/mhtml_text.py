"""Extract the readable text of a saved web page (.mhtml / "Saved by Blink") to stdout.

  .venv/bin/python -I tools/mhtml_text.py <file.mhtml> [--html]

Finds the text/html part, decodes it, drops scripts/styles and tags, and collapses whitespace.
Image parts are ignored. With --html the decoded HTML is printed instead.
"""
import argparse
import html
import re
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', type=Path)
    parser.add_argument('--html', action='store_true')
    args = parser.parse_args()
    message = BytesParser(policy=policy.default).parsebytes(args.path.read_bytes())
    parts = [p for p in message.walk() if p.get_content_type() == 'text/html']
    if not parts:
        raise SystemExit('no text/html part')
    raw = parts[0].get_payload(decode=True)
    charset = parts[0].get_content_charset() or 'utf-8'
    try:
        page = raw.decode(charset)
    except (UnicodeDecodeError, LookupError):
        page = raw.decode('utf-8', errors='replace')
    out_stream = open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
    if args.html:
        out_stream.write(page)
        return
    page = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', page)
    page = re.sub(r'(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|table|blockquote|section|article)>', '\n', page)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', page))
    lines = [re.sub(r'[ \t ​]+', ' ', line).strip() for line in text.splitlines()]
    out = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    out_stream.write('\n'.join(out))


if __name__ == '__main__':
    main()
