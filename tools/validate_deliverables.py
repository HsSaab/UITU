"""Validate delivered artifacts against the rendered documents and live evidence."""
from pathlib import Path
import re,json,hashlib
from zipfile import ZipFile
from docx import Document
from lxml import etree
import fitz
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
NAMES=['Тарасов Арсений Максимович','Дементиевский Дмитрий Максимович','Тыцкий Богдан Максимович']
results=[]
for number in [4,5,6]:
 path=ROOT/'reports'/f'УИТУ_Практическая_{number}_ТехноСервис.docx'
 with ZipFile(path) as z:assert z.testzip() is None
 doc=Document(path);pdf=fitz.open(path.with_suffix('.pdf'))
 text='\n'.join(p.text for p in doc.paragraphs)
 assert not re.search(r'PAGE_COUNT|FIGURE_COUNT|TABLE_COUNT|SOURCE_COUNT|Содержание обновляется',text)
 assert all(n in text for n in NAMES)
 assert 'ИКБО-74-23' in text and 'Демидов Н.А.' in text
 for title in ['РЕФЕРАТ','ВВЕДЕНИЕ','ЗАКЛЮЧЕНИЕ','СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ']:
  assert any(p.text==title and p.style.name=='Heading 1' for p in doc.paragraphs)
 sec=doc.sections[0]
 for attr,value in [('page_width',21),('page_height',29.7),('left_margin',3),('right_margin',1.5),('top_margin',2),('bottom_margin',2)]:
  assert abs(getattr(sec,attr).cm-value)<.01,(path.name,attr)
 assert sec.different_first_page_header_footer
 normal=doc.styles['Normal'];assert normal.font.name=='Times New Roman' and normal.font.size.pt==14
 assert normal.paragraph_format.line_spacing==1.5
 assert abs(normal.paragraph_format.first_line_indent.cm-1.25)<.01
 figures=[p.text for p in doc.paragraphs if re.match(r'^Рисунок \d+ —',p.text)]
 tables=[p.text for p in doc.paragraphs if re.match(r'^Таблица \d+ —',p.text)]
 sources=[p for p in doc.paragraphs if re.match(r'^\d+\. ',p.text)]
 stats=next(p.text for p in doc.paragraphs if p.text.startswith('Объём отчёта:'))
 counts=list(map(int,re.findall(r'\d+',stats)))
 assert counts==[len(pdf),len(figures),len(tables),len(sources)],(stats,counts)
 assert len(figures)==len(doc.inline_shapes)
 for i in range(1,len(figures)+1):assert re.search(r'рисунке '+str(i)+r'\b',text)
 for i in range(1,len(tables)+1):assert re.search(r'таблице '+str(i)+r'\b',text)
 for i in range(1,len(sources)+1):assert re.search(r'\[[^\]]*\b'+str(i)+r'\b[^\]]*\]',text)
 headings=[p for p in doc.paragraphs if p.style.name in ['Heading 1','Heading 2']]
 cached=doc._element.body.xpath('./w:sdt[w:sdtPr/w:tag[@w:val="UITU_TOC"]]/w:sdtContent/w:p')
 assert len(headings)==len(cached)
 assert any('TOC ' in (x.text or '') for x in doc._element.body.xpath('.//w:instrText'))
 from finalize_reports import get_pages
 _,pages=get_pages(path.with_suffix('.pdf'),[(p.text,1) for p in headings])
 for p,entry in zip(headings,cached):
  title=''.join(entry.xpath('./w:hyperlink//w:t/text()'))
  number_text=''.join(entry.xpath('./w:r/w:t/text()'))
  assert title==p.text and int(number_text)==pages[p.text]
 for i,page in enumerate(pdf):
  assert len(page.get_text().strip())>220,(path.name,'unexpected short page',i+1)
  bottom=page.get_text(clip=fitz.Rect(0,780,page.rect.width,page.rect.height)).strip()
  assert bottom==('' if i==0 else str(i+1)),(path.name,i+1,bottom)
  for block in page.get_text('dict')['blocks']:
   if block['type']==0:
    x0,y0,x1,y1=block['bbox'];assert x0>=25 and x1<=page.rect.width-20 and y0>=20 and y1<=page.rect.height-10
 hashes={suffix:hashlib.sha256(path.with_suffix(suffix).read_bytes()).hexdigest() for suffix in ['.docx','.pdf']}
 results.append({'report':number,'pages':len(pdf),'figures':len(figures),'tables':len(tables),'sources':len(sources),'toc':'verified against PDF','sha256':hashes})
 pdf.close()
index=json.loads((ROOT/'diagrams/idef0-index.json').read_text());assert len(index)==10
for key in ['vps','monitoring']:
 nodes={m['node'] for m in index if m['stem'].startswith(key)};assert nodes=={'A-0','A0','A1','A2','A3'}
for item in index:
 for extension in ['.drawio','.svg']:etree.parse(str(ROOT/'diagrams'/(item['stem']+extension)))
 with Image.open(ROOT/'diagrams/png'/(item['stem']+'.png')) as im:assert im.width>=2400
api=json.loads((ROOT/'evidence/api-results.json').read_text());assert api['executed']==20 and api['failed']==api['errors']==0
browser=json.loads((ROOT/'evidence/browser-results.json').read_text());assert browser['executed']==13 and browser['failed']==0
units=json.loads((ROOT/'evidence/unit-results.json').read_text());assert len(units)==10 and all(x['status']=='passed' for x in units)
for p in (ROOT/'docs/practices').glob('*.docx'):
 originals=list(Path('/workspace/attachments').rglob(p.name))
 if originals:assert p.read_bytes()==originals[0].read_bytes()
(ROOT/'evidence/document-validation.json').write_text(json.dumps({'reports':results,'idef0_diagrams':10,'unit_tests':10,'api_tests':20,'browser_checks':13,'status':'passed'},ensure_ascii=False,indent=2))
for r in results:print(f'Report {r["report"]}: {r["pages"]} pages, {r["figures"]} figures, {r["tables"]} tables; validated')
print('All documents, TOCs, page numbers, diagrams and test evidence validated.')
