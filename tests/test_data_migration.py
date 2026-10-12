import base64,csv,io,json,sqlite3,unittest,zipfile
from support import LiveServer
from services import spreadsheets
class Migration(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.t=self.s.login()
 def tearDown(self):self.s.close()
 def req(self,path,body=None,status=200,token=None):
  code,data,_=self.s.request('/api/v5/migration'+path,'POST' if body is not None else 'GET',body,token or self.t);self.assertEqual(code,status,data);return data
 def upload(self,category,rows,xlsx=False):
  if xlsx:data=spreadsheets.xlsx([('Gegevens',rows)])
  else:
   stream=io.StringIO();csv.writer(stream,delimiter=';').writerows(rows);data=stream.getvalue().encode('utf-8-sig')
  return self.req('/uploads',{'source':'Fictieve NoCore-export','category':category,'filename':'fictief.xlsx' if xlsx else 'fictief.csv','content':base64.b64encode(data).decode()})
 def preview(self,j,policy='reject',mapping=None):return self.req(f'/{j["id"]}/preview',{'version':j['version'],'mapping':mapping or j['mapping'],'policy':policy,'profile_name':'Fictieve mapping'})
 def runjob(self,j):
  j=self.req(f'/{j["id"]}/confirm',{'version':j['version'],'confirm':True})
  while j['status']=='Bezig':j=self.req(f'/{j["id"]}/batch',{'version':j['version']})
  self.assertEqual(j['status'],'Voltooid',j.get('last_error'));return j
 def test_csv_dryrun_reimport_update_and_restart(self):
  data=[['Klantnummer','Bedrijfsnaam'],['0001','Fictieve CSV-klant']];j=self.upload('customers',data)
  with sqlite3.connect(self.s.db) as c:before=c.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
  j=self.preview(j);self.assertEqual(j['summary']['Nieuw'],1)
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM customers').fetchone()[0],before);self.assertEqual(c.execute('SELECT COUNT(*) FROM migration_links').fetchone()[0],0)
  self.req(f'/{j["id"]}/confirm',{'version':j['version'],'confirm':False},status=400)
  j=self.runjob(j);self.assertEqual(j['results']['Nieuw'],1)
  j=self.runjob(self.preview(self.upload('customers',data)));self.assertEqual(j['results']['Ongewijzigd'],1)
  data[1][1]='Fictieve gewijzigde klant';blocked=self.preview(self.upload('customers',data));self.assertEqual(blocked['status'],'Geblokkeerd')
  j=self.runjob(self.preview(blocked,'update'));self.assertEqual(j['results']['Bijgewerkt'],1)
  self.s.stop();self.s.start()
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute("SELECT external_id FROM migration_links WHERE category='customers'").fetchone()[0],'0001');self.assertEqual(c.execute('SELECT COUNT(*) FROM customers').fetchone()[0],before+1)
 def test_xlsx_relations_missing_parent_duplicate_and_unauthorized(self):
  rows=[['external_id','name','customer_id'],['L001','Fictieve locatie','0001']]
  j=self.preview(self.upload('objects',rows,True));self.assertEqual(j['status'],'Geblokkeerd');self.assertIn('ontbrekende relatie',j['rows'][0]['preview']['error'])
  self.runjob(self.preview(self.upload('customers',[['external_id','name'],['0001','Fictieve ouder']],True)))
  j=self.runjob(self.preview(j));self.assertEqual(j['results']['Nieuw'],1)
  duplicated=self.preview(self.upload('customers',[['external_id','name'],['002','Fictief A'],['002','Fictief B']]));self.assertEqual(duplicated['summary']['Duplicaten'],1);self.req(f'/{duplicated["id"]}/confirm',{'version':duplicated['version'],'confirm':True},status=409)
  emp=self.s.login('Bart van Aalde','Amocean2!');self.req('',token=emp,status=403);self.req(f'/{j["id"]}',token=emp,status=403);self.req('/uploads',{},token=emp,status=403)
 def test_checkpoint_pause_resume_and_concurrent_change(self):
  j=self.preview(self.upload('customers',[['external_id','name']]+[[str(i),'Fictieve batch '+str(i)] for i in range(205)]));j=self.req(f'/{j["id"]}/confirm',{'version':j['version'],'confirm':True});j=self.req(f'/{j["id"]}/batch',{'version':j['version']});self.assertEqual(j['cursor'],100)
  self.req(f'/{j["id"]}/batch',{'version':j['version']-1},status=409)
  self.s.stop();self.s.start();j=self.req(f'/{j["id"]}');self.assertEqual(j['cursor'],100)
  while j['status']=='Bezig':j=self.req(f'/{j["id"]}/batch',{'version':j['version']})
  self.assertEqual(j['results']['Nieuw'],205)
  update=self.preview(self.upload('customers',[['external_id','name'],['0','Fictief wijziging']]),'update')
  with sqlite3.connect(self.s.db) as c:c.execute("UPDATE customers SET name='Tussentijdse wijziging' WHERE id=(SELECT local_id FROM migration_links WHERE external_id='0' AND category='customers')")
  update=self.req(f'/{update["id"]}/confirm',{'version':update['version'],'confirm':True});update=self.req(f'/{update["id"]}/batch',{'version':update['version']});self.assertEqual(update['status'],'Onderbroken');self.assertEqual(update['cursor'],0)
  update=self.runjob(self.preview(update,'update'));self.assertEqual(update['results']['Bijgewerkt'],1)
 def test_unsafe_files_and_dutch_dates(self):
  self.req('/uploads',{'source':'Fictief','category':'customers','filename':'x.csv','content':base64.b64encode(b'external_id;name\n1;=IMPORTXML("x")').decode()},status=400)
  data=spreadsheets.xlsx([('Gegevens',[['external_id','name'],['001','Fictief']])]);source=zipfile.ZipFile(io.BytesIO(data));out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   for n in source.namelist():z.writestr(n,source.read(n).replace(b'<is><t',b'<f>1+1</f><is><t') if n.endswith('sheet1.xml') else source.read(n))
  self.req('/uploads',{'source':'Fictief','category':'customers','filename':'x.xlsx','content':base64.b64encode(out.getvalue()).decode()},status=400)
  from services.migration_registry import convert
  self.assertEqual(convert('start_date','31-12-2030'),'2030-12-31')
 def test_all_categories_templates_and_additive_model_relationships(self):
  meta=self.req('')['categories']
  for category in meta:
   for format in ('csv','xlsx'):
    code,data,_=self.s.request(f'/api/v5/migration/template/{category}/{format}',token=self.t);self.assertEqual(code,200,(category,format));headers,rows=spreadsheets.read('template.'+format,data);self.assertEqual(headers,meta[category]['fields']);self.assertEqual(len(rows),1)
  fixtures=[('customers',[['external_id','name'],['C','Fictieve ruimtenklant']]),('objects',[['external_id','name','customer_id'],['L','Fictieve verdieping','C']]),('rooms',[['external_id','name','object_id','area'],['R','Fictieve lesruimte','L','50,5']]),('service_types',[['external_id','name'],['S','Fictieve interieurverzorging']]),('work_programs',[['external_id','name','object_id','service_type_id'],['P','Fictief dagprogramma','L','S']]),('work_instructions',[['external_id','name','program_id','room_id','instructions'],['I','Fictieve vloerinstructie','P','R','Fictieve dweilinstructie']])]
  for category,rows in fixtures:self.runjob(self.preview(self.upload(category,rows,True)))
  code,result,_=self.s.request('/api/v5/resources/work_instructions',token=self.t);self.assertEqual(code,200);self.assertEqual(result[0]['instructions'],'Fictieve dweilinstructie')
 def test_numeric_normalization_reimport_and_explicit_existing_link(self):
  rows=[['external_id','name','contract_hours'],['0002','Fictieve medewerker','38,0']]
  self.runjob(self.preview(self.upload('employees',rows)));self.assertEqual(self.runjob(self.preview(self.upload('employees',rows)))['results']['Ongewijzigd'],1)
  name=self.s.request('/api/v5/entities/customers/1',token=self.t)[1]['name'];rows=[['external_id','existing_id','name'],['legacy-001','1',name]]
  self.assertEqual(self.runjob(self.preview(self.upload('customers',rows)))['results']['Ongewijzigd'],1)
 def test_every_advertised_category_can_import_its_template(self):
  order=['customers','contacts','objects','rooms','teams','employees','service_types','contracts','work_programs','work_instructions','workorders','shifts','hours','inspections','alerts']
  meta=self.req('')['categories'];order += [x for x in meta if x not in order]
  for category in order:
   with self.subTest(category=category):
    code,data,_=self.s.request(f'/api/v5/migration/template/{category}/xlsx',token=self.t);self.assertEqual(code,200)
    j=self.req('/uploads',{'source':'Fictieve templateketen','category':category,'filename':'voorbeeld.xlsx','content':base64.b64encode(data).decode()});j=self.preview(j)
    self.assertEqual(j['status'],'Gecontroleerd',j['rows']);self.runjob(j)
    code,csvdata,_=self.s.request(f'/api/v5/migration/template/{category}/csv',token=self.t);self.assertEqual(code,200)
    repeat=self.req('/uploads',{'source':'Fictieve templateketen','category':category,'filename':'voorbeeld.csv','content':base64.b64encode(csvdata).decode()});repeat=self.preview(repeat);self.assertEqual(repeat['status'],'Gecontroleerd',repeat['rows']);self.assertEqual(self.runjob(repeat)['results'].get('Ongewijzigd'),1)
    code,rows,_=self.s.request('/api/v5/'+('entities/' if category in ('customers','objects','contracts','quotes','employees','shifts','hours','inspections','logbook','workorders','orders','assets','keys','vehicles','documents','leave','availability','alerts') else 'resources/')+category,token=self.t);self.assertEqual(code,200);self.assertTrue(rows.get('items') if isinstance(rows,dict) else rows)
 def test_concurrent_confirmation_and_type_mapping(self):
  import concurrent.futures
  rows=[['external_id','name','Onbekende kolom'],['0009','Fictieve typeherkenning','test@fictief.invalid']]
  j=self.upload('customers',rows);self.assertEqual(j['mapping']['Onbekende kolom'],'email');j=self.preview(j)
  def confirm():return self.s.request(f'/api/v5/migration/{j["id"]}/confirm','POST',{'version':j['version'],'confirm':True},self.t)[0]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(lambda _:confirm(),range(2)))
  self.assertEqual(sorted(codes),[200,409]);j=self.req(f'/{j["id"]}');j=self.req(f'/{j["id"]}/batch',{'version':j['version']});self.assertEqual(j['results']['Nieuw'],1)
