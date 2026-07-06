"""md2pdf — render a repo markdown document to a GitHub-styled, print-ready PDF.

The practitioner prints documents; raw .md prints small and unreadable, while
GitHub's rendering prints beautifully. This reproduces that rendering locally:
markdown -> GitHub-flavored HTML (tables, fenced code) -> headless Edge -> PDF.

Usage:
    python tools/md2pdf.py TRAINING_HALL.md [more.md ...]
    python tools/md2pdf.py --all          # the standard printable set

PDFs land in Print/ (git-ignored generated artifacts).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "Print"

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

# The standard printable set for --all.
STANDARD_SET = [
    "1yeartoShaolin.md",
    "TEMPLE_DAY.md",
    "TRAINING_HALL.md",
    "Diet/README.md",
    "Diet/FOODS.md",
    "Mandarin/PINYIN.md",
    "Mandarin/CHARACTERS.md",
    "Mandarin/SPEAKING.md",
    "Mandarin/VOCABULARY.md",
    "Mandarin/CURRICULUM.md",
    "Mandarin/JOURNALING_METHOD.md",
]

# GitHub's visual language, tuned for paper. CJK fallbacks matter: the lane
# documents carry hanzi, and the PDF must render them.
CSS = """
@page { size: letter; margin: 0.6in; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
               "Microsoft YaHei", "PingFang SC", Helvetica, Arial, sans-serif;
  color: #1f2328; background: #fff;
  font-size: 11.5pt; line-height: 1.55;
  max-width: 7.3in; margin: 0 auto;
}
h1 { font-size: 20pt; font-weight: 600; margin: 0.4em 0 0.5em;
     padding-bottom: 0.25em; border-bottom: 1px solid #d1d9e0; }
h2 { font-size: 15.5pt; font-weight: 600; margin: 1.1em 0 0.5em;
     padding-bottom: 0.2em; border-bottom: 1px solid #d1d9e0;
     page-break-after: avoid; }
h3 { font-size: 13pt; font-weight: 600; margin: 1em 0 0.4em; page-break-after: avoid; }
h4 { font-size: 11.5pt; font-weight: 600; margin: 1em 0 0.4em; page-break-after: avoid; }
p, ul, ol { margin: 0 0 0.7em; }
li { margin-bottom: 0.25em; }
li > p { margin-bottom: 0.35em; }
a { color: #0969da; text-decoration: none; }
strong { font-weight: 600; }
hr { border: 0; border-top: 2px solid #d1d9e0; margin: 1.4em 0; }
blockquote { border-left: 4px solid #d1d9e0; color: #59636e;
             margin: 0 0 0.7em; padding: 0 1em; }
code { font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
       font-size: 10pt; background: #f6f8fa; border-radius: 4px; padding: 1px 5px; }
pre { background: #f6f8fa; border-radius: 6px; padding: 12px 14px;
      margin: 0 0 0.8em; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 9.5pt; line-height: 1.45; }
table { border-collapse: collapse; margin: 0 0 0.9em; width: 100%;
        font-size: 10.5pt; page-break-inside: auto; }
th, td { border: 1px solid #d1d9e0; padding: 5px 10px; text-align: left;
         vertical-align: top; }
th { background: #f6f8fa; font-weight: 600; }
tr { page-break-inside: avoid; }
tbody tr:nth-child(2n) { background: #fbfcfd; }
img { max-width: 100%; }
"""

HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title><style>{css}</style></head>
<body>
{body}
</body>
</html>
"""


def find_edge() -> Path:
    for p in EDGE_CANDIDATES:
        if p.exists():
            return p
    sys.exit("msedge.exe not found — install Edge or add its path to EDGE_CANDIDATES.")


def render(md_path: Path, edge: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists", "smarty"]
    )
    OUT_DIR.mkdir(exist_ok=True)
    stem = md_path.stem if md_path.parent == REPO_ROOT else (
        f"{md_path.parent.name}_{md_path.stem}"
    )
    html_path = OUT_DIR / f"{stem}.html"
    pdf_path = OUT_DIR / f"{stem}.pdf"
    html_path.write_text(
        HTML_SHELL.format(title=md_path.stem, css=CSS, body=body), encoding="utf-8"
    )
    subprocess.run(
        [str(edge), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=False, capture_output=True, timeout=120,
    )
    # Edge exits before the file is fully flushed sometimes; wait briefly.
    for _ in range(20):
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            break
        time.sleep(0.5)
    if not pdf_path.exists():
        sys.exit(f"Edge produced no PDF for {md_path}")
    return pdf_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="markdown files (repo-relative or absolute)")
    ap.add_argument("--all", action="store_true", help="render the standard printable set")
    args = ap.parse_args()

    targets = STANDARD_SET if args.all else args.files
    if not targets:
        ap.error("give markdown files or --all")

    edge = find_edge()
    for t in targets:
        p = Path(t)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.exists():
            print(f"skip (not found): {t}")
            continue
        pdf = render(p, edge)
        print(f"{t}  ->  {pdf.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
