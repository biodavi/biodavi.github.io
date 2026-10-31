#!/usr/bin/env python3
"""Builds cv.html and cv.pdf from index.html.

Run `python3 build_cv.py` after editing index.html to refresh the downloadable CV.
Needs beautifulsoup4 and Google Chrome (used headless to print the PDF).
"""
import copy
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SUMMARY = (
    "Molecular biologist from Colombia and PhD student in Veterinary Medical Sciences "
    "(Wildlife Health and Ecology) at the University of Calgary. My doctoral project studies emerging pathogens in wild mammals from "
    "Costa Rica using molecular and bioinformatic approaches and artificial intelligence. My background spans molecular biology, bioinformatics, the microbiome, "
    "tick-borne pathogens and space biology, with experience in molecular diagnostics, field "
    "sampling of wild mammals, zebrafish research on bone under simulated microgravity, "
    "and university teaching."
)

# (section id, heading) in CV order
SECTIONS = [
    ("education", "Education"),
    ("experience", "Professional experience"),
    ("publications", "Publications"),
    ("projects", "Research projects & grants"),
    ("awards", "Awards & recognition"),
    ("events", "Scientific events & presentations"),
    ("courses", "Postgraduate courses & training"),
    ("volunteering", "Volunteering & memberships"),
]

DROP = [
    "img", "button", ".exp-logo-wrap", ".vol-logo-ph", ".award-icon", ".proj-ph", ".proj-img",
]

CSS = """
@page { size: Letter; margin: 12mm 14mm; }
* { box-sizing: border-box; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 9pt; line-height: 1.32; color: #1a1a1a; margin: 0; }
a { color: inherit; text-decoration: none; }
header { border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; margin-bottom: 10px; }
h1 { font-size: 21pt; margin: 0; letter-spacing: -.01em; }
.sub { font-size: 10.5pt; color: #444; margin: 2px 0 6px; }
.contact { font-size: 8.5pt; color: #333; display: flex; flex-wrap: wrap; gap: 4px 14px; }
h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: .06em; margin: 11px 0 5px; padding-bottom: 2px; border-bottom: 1px solid #999; break-after: avoid; }
h3 { font-size: 9.5pt; margin: 9px 0 3px; color: #333; break-after: avoid; }
p { margin: 0 0 4px; }
.skills { margin-top: 4px; font-size: 9pt; color: #333; }
.exp-item, .pub-item, .vol-item, .award-row, .proj-card { break-inside: avoid; margin: 0 0 5px; }
.exp-role, .vol-title, .award-name, .proj-title, .pub-title { font-weight: 700; }
.exp-org, .vol-org, .award-inst, .pub-journal { color: #333; }
.exp-date, .vol-date, .award-year, .proj-tag, .proj-meta, .pub-year { color: #666; font-size: 8.5pt; }
.pub-year { display: inline; margin-right: 4px; font-weight: 700; }
.pub-title, .pub-authors, .pub-journal, .pub-link { display: inline; }
.pub-item { margin: 0 0 4px; }
.pub-title { font-weight: 700; }
.pub-authors, .pub-journal { margin-left: 3px; }
.pub-journal { font-style: italic; }
.pub-link { margin-left: 3px; }
.pub-title::after, .pub-journal::after { content: '.'; }
.pub-title::after { font-weight: 400; }
.pub-authors, .ev-authors { color: #444; }
.ev-authors { display: block; font-size: 8.5pt; }
.exp-desc, .vol-desc, .award-desc { margin-top: 1px; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin: 0; }
.proj-grid { display: block; }
.proj { margin: 0 0 5px; break-inside: avoid; }
.proj strong { display: block; }
.proj-skills { color: #666; }
.proj-body { padding: 0; }
.proj-foot { display: block; margin: 1px 0 0; }
.proj-role { font-weight: 600; }
.proj-grant { color: #1a1a1a; font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 8pt; text-transform: uppercase; letter-spacing: .05em; color: #666; border-bottom: 1px solid #999; padding: 2px 4px; }
td { padding: 2px 4px; border-bottom: 1px solid #e3e3e3; vertical-align: top; }
tr { break-inside: avoid; }
td:last-child { white-space: nowrap; text-align: right; }
th:last-child { text-align: right; }
.role-badge { font-weight: 600; font-size: 8.5pt; }
"""


def clean(node):
    node = copy.copy(node)
    for sel in DROP:
        for el in node.select(sel):
            el.decompose()
    for el in node.find_all(True):
        for attr in ("style", "onclick", "onerror", "target"):
            el.attrs.pop(attr, None)
    for card in node.select(".proj-card"):
        txt = lambda sel: (card.select_one(sel).decode_contents().strip() if card.select_one(sel) else "")
        grant = txt(".proj-grant")
        para = (
            f'<p class="proj"><strong>{txt(".proj-title")}</strong> '
            f'{txt(".proj-role")}. {txt(".proj-tag")}. '
            f'{grant + ". " if grant else ""}<span class="proj-skills">{txt(".proj-meta")}.</span></p>'
        )
        card.replace_with(BeautifulSoup(para, "html.parser"))
    for item, name, parts in (
        (".award-row", ".award-name", (".award-inst", ".award-year", ".award-desc")),
        (".vol-item", ".vol-title", (".vol-org", ".vol-date", ".vol-desc")),
    ):
        for row in node.select(item):
            get = lambda sel: (row.select_one(sel).decode_contents().strip() if row.select_one(sel) else "")
            line = " ".join(
                (t if t.endswith((".", "?", "!")) else t + ".") for t in (get(s) for s in parts) if t
            )
            row.replace_with(BeautifulSoup(
                f'<p class="proj"><strong>{get(name)}</strong>{line}</p>', "html.parser"))
    for a in node.select("a.pub-link"):
        a.string = a.get_text().replace("↗", "").strip()
    return node


def main():
    soup = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8"), "html.parser")
    parts = []
    for sid, heading in SECTIONS:
        sec = soup.find(id=sid)
        if sec is None:
            sys.exit(f"section #{sid} not found in index.html")
        sec = clean(sec)
        for h in sec.find_all("h2"):
            h.decompose()
        parts.append(f"<section><h2>{heading}</h2>{sec.decode_contents()}</section>")

    skills = ", ".join(c.get_text(strip=True) for c in soup.select("#about .chip"))
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Juan David Carvajal-Agudelo, CV</title>
<style>{CSS}</style></head><body>
<header>
  <h1>Juan David Carvajal-Agudelo</h1>
  <div class="sub">PhD Student, Veterinary Medical Sciences · University of Calgary</div>
  <div class="contact">
    <a href="mailto:jdavidcarvajal@gmail.com">jdavidcarvajal@gmail.com</a>
    <a href="mailto:juandavid.carvajal@ucalgary.ca">juandavid.carvajal@ucalgary.ca</a>
    <a href="https://linkedin.com/in/biodavi">linkedin.com/in/biodavi</a>
    <a href="https://orcid.org/0000-0002-2888-7147">orcid.org/0000-0002-2888-7147</a>
    <a href="https://scholar.google.com/citations?user=_loX9b4AAAAJ">scholar.google.com/citations?user=_loX9b4AAAAJ</a>
  </div>
</header>
<section><h2>Summary</h2><p>{SUMMARY}</p><p class="skills"><strong>Research areas:</strong> {skills}.</p></section>
{''.join(parts)}
</body></html>"""
    (ROOT / "cv.html").write_text(html, encoding="utf-8")

    pdf = ROOT / "Juan-David-Carvajal-Agudelo-CV.pdf"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", (ROOT / "cv.html").as_uri()],
        check=True, capture_output=True,
    )
    print("wrote", pdf)


if __name__ == "__main__":
    main()
