"""Create a local visual QA contact sheet; no learner or credential data included."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'src' / 'phoenix'))
import nlm
from nlm_visuals import render, render_question

def main():
    output=ROOT/'.local/visual-qa'; output.mkdir(parents=True,exist_ok=True)
    parts=['<!doctype html><meta charset="utf-8"><title>NLM visual QA</title><style>body{font:16px system-ui;background:#edf1f5;margin:20px}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}section{background:white;padding:12px}svg{width:100%}p{font-size:13px}</style><h1>Newton visual QA · authored templates</h1><main>']
    for family in sorted(nlm.FAMILIES):
        svg,alt,_=render(family)
        parts.append(f'<section><h2>{family}</h2>{svg}<p>{alt}</p></section>')
    for q in nlm.load_pack()['questions']:
        if q['scene']:
            svg,alt=render_question(q['scene'])
            parts.append(f'<section><h2>{q["id"]}</h2>{svg}<p>{alt}</p></section>')
    parts.append('</main>'); (output/'index.html').write_text(''.join(parts),encoding='utf-8')
    print(output/'index.html')

if __name__=='__main__': main()
