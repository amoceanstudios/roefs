import io,unittest,zipfile
from services import spreadsheets as s
from domain import Problem

class Spreadsheets(unittest.TestCase):
 def edit(self,updates):
  original=s.xlsx([('Gegevens',[['external_id','date','start_time'],['0001','2030-02-04','08:30']])]);out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(original)) as source,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as target:
   for name in source.namelist():target.writestr(name,updates.pop(name,source.read(name)))
   for name,data in updates.items():target.writestr(name,data)
  return out.getvalue()
 def test_csv_separators_bom_empty_cells_and_leading_zeros(self):
  for sep in (';',',','\t','|'):
   headers,rows=s.read('x.csv',('\ufeffexternal_id'+sep+'name'+sep+'phone\n0001'+sep+'Fictief'+sep+'\n').encode());self.assertEqual(rows[0]['values'],['0001','Fictief',''])
 def test_excel_numeric_dates_time_and_identifier_format(self):
  sheet=b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>external_id</t></is></c><c r="B1" t="inlineStr"><is><t>date</t></is></c><c r="C1" t="inlineStr"><is><t>start_time</t></is></c></row><row r="2"><c r="A2" s="1"><v>1</v></c><c r="B2" s="2"><v>47518</v></c><c r="C2" s="3"><v>0.3541666666666667</v></c></row></sheetData></worksheet>'
  styles=b'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts><numFmt numFmtId="164" formatCode="00000"/></numFmts><cellXfs><xf numFmtId="0"/><xf numFmtId="164"/><xf numFmtId="14"/><xf numFmtId="20"/></cellXfs></styleSheet>'
  _,rows=s.read('x.xlsx',self.edit({'xl/worksheets/sheet1.xml':sheet,'xl/styles.xml':styles}));self.assertEqual(rows[0]['values'],['00001','2030-02-04','08:30'])
 def test_external_content_entities_traversal_and_corruption(self):
  attacks=[{'xl/externalLinks/x.xml':b'x'},{'../evil':b'x'},{'xl/worksheets/sheet1.xml':b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><x>&x;</x>'},{'xl/worksheets/sheet1.xml':b'bad xml'},{'xl/_rels/extra.rels':b'<Relationships><Relationship TargetMode="External" Target="https://fictief.invalid"/></Relationships>'}]
  for extra in attacks:
   with self.subTest(extra=list(extra)),self.assertRaises(Problem):s.read('x.xlsx',self.edit(extra))
  with self.assertRaises(Problem):s.read('x.xlsx',b'PK truncated')
 def test_decompression_and_row_limits(self):
  with self.assertRaises(Problem):s.read('x.xlsx',self.edit({'huge.xml':b'0'*(31*1024*1024)}))
  with self.assertRaises(Problem):s.read('x.csv',b'id;name\n'+b'1;Fictief\n'*25001)
 def test_visible_first_sheet_order(self):
  original=s.xlsx([('Uitleg',[['Tekst'],['Fictieve uitleg']]),('Gegevens',[['external_id','name'],['0001','Fictief']])]);out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(original)) as source,zipfile.ZipFile(out,'w') as target:
   for name in source.namelist():
    data=source.read(name)
    if name=='xl/workbook.xml':data=data.replace(b'<sheet name="Uitleg" sheetId="1" r:id="rId1"/><sheet name="Gegevens" sheetId="2" r:id="rId2"/>',b'<sheet name="Gegevens" sheetId="2" r:id="rId2"/><sheet name="Uitleg" sheetId="1" r:id="rId1"/>')
    target.writestr(name,data)
  headers,rows=s.read('x.xlsx',out.getvalue());self.assertEqual(headers,['external_id','name']);self.assertEqual(rows[0]['values'],['0001','Fictief'])
