import json,unittest,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from support import LiveServer,ROOT

class EnterpriseBrowser(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.play=sync_playwright().start();exe=os.environ.get('ROEFS_TEST_BROWSER') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None);cls.browser=cls.play.chromium.launch(executable_path=exe,headless=True)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.play.stop()
 def setUp(self):
  self.s=LiveServer();self.admin=self.s.login();self.context=self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,timezone_id='Europe/Amsterdam');self.page=self.context.new_page();self.errors=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)))
 def tearDown(self):
  self.context.close();self.s.close();self.assertEqual(self.errors,[])
 def login(self):
  self.page.goto(self.s.url);self.page.locator('#username').fill('Roefs');self.page.locator('#password').fill('Amocean1!');self.page.get_by_role('button',name='Veilig inloggen').click();self.page.get_by_role('button',name='Oud Portaal',exact=True).click();self.page.locator('.daily-home').wait_for()
 def open(self,tab):
  self.page.evaluate('(tab)=>v5Select(tab)',tab);self.page.locator('#v5body').wait_for()
 def test_all_viewports_real_pages_cookie_and_reload(self):
  self.login();self.assertIsNone(self.page.evaluate("sessionStorage.getItem('roefsToken')"));self.assertNotIn('roefs_session',self.page.evaluate('document.cookie'));self.page.reload();self.page.locator('.daily-home').wait_for()
  for width in (320,375,390,430,768,1024,1440,1920):
   self.page.set_viewport_size({'width':width,'height':900})
   for tab in ('workorders','calendar','customers','contacts','certifications','files','time','invoices'):
    self.open(tab);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1,(width,tab))
   for target in ('notifications','reportsv5','settingsv5','integrations'):
    self.page.evaluate('(p)=>openPage(p)',target);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1,(width,target))
  self.page.set_viewport_size({'width':390,'height':844});self.open('calendar');self.page.screenshot(path=str(ROOT/'reports'/'v5-mobile-planning.png'),full_page=True)
 def test_customer_form_persistence_validation_and_timeline(self):
  self.login();self.open('customers');self.page.get_by_role('button',name='Nieuw toevoegen',exact=True).click();self.page.locator('#v5-name').fill('Fictieve browserklant');self.page.locator('#v5-email').fill('browser@fictief.invalid');self.page.locator('#v5-billing_address').fill('Teststraat 12');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  card=self.page.locator('.v5-item').filter(has_text='Fictieve browserklant');card.get_by_role('button',name='Klantdossier').click();self.page.get_by_role('heading',name='Klantdossier · Fictieve browserklant').wait_for();self.page.get_by_role('button',name='Sluiten',exact=True).click();self.page.reload();self.page.locator('.daily-home').wait_for();self.open('customers');self.assertIn('Fictieve browserklant',self.page.locator('#v5body').inner_text())
  data=self.s.request('/api/v5/entities/customers?q=browserklant',token=self.admin)[1];self.assertEqual(data['items'][0]['billing_address'],'Teststraat 12')
 def test_planning_copy_and_conflict_keyboard_alternative(self):
  self.login();self.open('calendar');self.page.get_by_role('button',name='Dienst toevoegen',exact=True).click();self.page.locator('#v5-object_id').select_option('1');self.page.locator('#v5-employee_id').select_option('1');self.page.locator('#v5-date').fill('2030-04-01');self.page.locator('#v5-start_time').fill('08:00');self.page.locator('#v5-end_time').fill('12:00');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  self.page.evaluate("plannerDate='2030-04-01';v5Calendar()");self.page.locator('.v5-shift').first.click();self.page.get_by_role('button',name='Einde +15 minuten').click();self.assertEqual(self.page.locator('#v5-end_time').input_value(),'12:15');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  self.page.locator('.v5-shift').first.click();self.page.get_by_role('button',name='Wekelijks kopiëren').click();self.page.locator('input[name=count]').fill('2');self.page.get_by_role('button',name='Kopieën opslaan').click();self.page.locator('#modalbg').wait_for(state='detached')
  rows=self.s.request('/api/records/shifts',token=self.admin)[1];self.assertEqual(len([s for s in rows if s['date'] in ('2030-04-08','2030-04-15')]),2)
 def test_workorder_checklist_and_file_upload_real_storage(self):
  self.login();self.open('workorders');self.page.get_by_role('button',name='Nieuw toevoegen',exact=True).click();self.page.locator('#v5-object_id').select_option('1');self.page.locator('#v5-description').fill('Fictieve mobiele opdracht');self.page.locator('#v5-date').fill('2030-04-02');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached');self.page.locator('.v5-item').filter(has_text='Fictieve mobiele opdracht').get_by_role('button',name='Opdracht openen').click();self.page.locator('input[name=title]').fill('Vloer controleren');self.page.get_by_role('button',name='Taak toevoegen').click();self.page.get_by_label('Vloer controleren',exact=True).check();self.page.get_by_role('button',name='Foto of bestand toevoegen').click();self.page.locator('#v5file').set_input_files({'name':'fictief-verslag.txt','mimeType':'text/plain','buffer':b'Fictief verslag vanuit browsertest.'});self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached');expect(self.page.locator('#v5body')).to_contain_text('fictief-verslag.txt')
  files=self.s.request('/api/v5/files',token=self.admin)[1];self.assertEqual(len(files),1);self.assertEqual(files[0]['name'],'fictief-verslag.txt')

 def test_inactive_integration_saved_and_visible(self):
  self.login();self.page.evaluate("openPage('integrations')");self.page.get_by_role('button',name='Koppeling toevoegen').click();self.page.locator('input[name=name]').fill('Fictieve AFAS-koppeling');self.page.locator('select[name=provider]').select_option('afas');self.page.get_by_role('button',name='Configuratie opslaan').click();self.page.locator('#modalbg').wait_for(state='detached');card=self.page.locator('.v5-item').filter(has=self.page.get_by_role('heading',name='Fictieve AFAS-koppeling'));self.assertIn('Niet actief',card.inner_text());self.page.reload();self.page.locator('.daily-home').wait_for();self.page.evaluate("openPage('integrations')");self.assertIn('Fictieve AFAS-koppeling',self.page.locator('#content').inner_text())
