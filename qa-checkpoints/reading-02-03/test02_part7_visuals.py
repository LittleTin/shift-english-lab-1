"""Generate three mobile-width SVG document tables, add image metadata.
Usage: python test02_part7_visuals.py input.json output.json output-graphics-dir
English display and unchanged English prose provide equivalent access to all values."""
import json,sys
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET
inp,out,d=map(Path,sys.argv[1:]); assert inp.resolve()!=out.resolve()
x=json.loads(inp.read_text()); gs={g['id']:g for g in x['groups']}
d.mkdir(parents=True,exist_ok=True)
TABLES=[
 ('05','Adapter model comparison',
   ['Model','Network','USB-A','Charge','Mass'],
   [('R10','1','0','None','45 g'),('R20','1','1','60 W','70 g'),('R30','2','1','90 W','110 g')],
   [16,80,153,210,270],
   'Adapter model comparison: counts of wired network and USB-A ports, maximum pass-through charging power, and adapter weight.',
   'Maximum pass-through charging power and port counts by adapter model.'),
 ('11','Monday initial test results',
   ['Lot','Tested','Passed¹','Rework','Scrap'],
   [('A','200','190','8','2'),('B','100','96','3','1')],
   [16,60,120,202,270],
   'Initial test results for lots A and B, with counts tested, passed immediately, sent for rework, and marked for scrap.',
   'Document 1: Monday initial test results. ¹ Passed immediately.'),
 ('12','Tuesday train schedule',
   ['Train','Departs','Arrives','Seats'],
   [('A','8:00 a.m.','9:15 a.m.','Available'),('B','8:30 a.m.','10:20 a.m.','Available'),('C','9:00 a.m.','10:05 a.m.','Fully booked'),('D','9:35 a.m.','11:00 a.m.','Available')],
   [16,71,150,231],
   'Tuesday train timetable from Eastford to Milltown, including departure time, arrival time and seat availability.',
   'Document 1: Tuesday trains from Eastford to Milltown.')
]
for num,title,headers,rows,cols,alt,caption in TABLES:
 g=gs['t02-r-p7-'+num]
 path=f't02-r-p7-{num}.svg'
 g.update(image='assets/graphics/'+path,imageAlt=alt,imageCaption=caption)
 h=84+31*len(rows)
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 336 {h}" role="img" aria-labelledby="t d">',
    f'<title id="t">{escape(title)}</title><desc id="d">{escape(alt)}</desc>',
    f'<rect width="336" height="{h}" rx="9" fill="#f4f8f5"/>',
    '<rect width="336" height="40" rx="9" fill="#174b3a"/>',
    f'<text x="16" y="26" fill="white" font-family="Arial,sans-serif" font-size="19" font-weight="700">{escape(title)}</text>',
    '<g fill="#163e31" font-family="Arial,sans-serif" font-size="14">']
 for i,lab in enumerate(headers):
  s.append(f'<text x="{cols[i]}" y="62" font-weight="700">{escape(lab)}</text>')
 for j,row in enumerate(rows):
  y=72+31*j
  s.append(f'<rect x="8" y="{y}" width="320" height="29" rx="4" fill="#{"e4efe8" if not j%2 else "f8fbf9"}"/>')
  for i,val in enumerate(row):
   s.append(f'<text x="{cols[i]}" y="{y+20}">{escape(val)}</text>')
 s.append('</g></svg>')
 buf='\n'.join(s)+'\n'
 parsed=ET.fromstring(buf)
 cells=[n.text for n in parsed.iter('{http://www.w3.org/2000/svg}text')]
 assert cells==[title]+headers+[val for row in rows for val in row]
 (d/path).write_text(buf)
out.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
