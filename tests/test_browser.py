"""Echte Chromium-browser tegen de Python-server; geen API-mocks."""
import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from support import LiveServer,ROOT
from playwright.sync_api import sync_playwright
class Browser(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pw=sync_playwright().start();exe=os.environ.get('ROEFS_TEST_BROWSER')
  if not exe and Path('/usr/bin/chromium').exists():exe='/usr/bin/chromium'
  cls.browser=cls.pw.chromium.launch(executable_path=exe,headless=True)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop()
 def setUp(self):
  self.s=LiveServer();self.errors=[];self.context=self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  self.page=self.context.new_page();self.page.on('pageerror',lambda e:self.errors.append(str(e)))
  self.page.on('dialog',lambda d:d.accept())
 def tearDown(self):
  try:self.assertEqual(self.errors,[])
  finally:self.context.close();self.s.close()
 def login(self,employee=False):
  self.page.goto(self.s.url);self.page.locator('#username').fill('Bart van Aalde' if employee else 'Roefs');self.page.locator('#password').fill('Amocean2!' if employee else 'Amocean1!');self.page.get_by_role('button',name='Veilig inloggen').click();self.page.locator('.daily-home').wait_for()
 def open(self,page):
  self.page.evaluate('(p)=>openPage(p)',page);self.page.wait_for_function('(p)=>page===p',arg=page)
 def test_all_admin_screens_real_backend(self):
  self.login()
  pages=self.page.evaluate('Object.keys(NAMES)')
  for p in pages:
   with self.subTest(page=p):
    self.open(p);self.assertTrue(self.page.locator('#content').inner_text().strip());self.assertFalse(self.page.locator('.toast').count(),self.page.locator('.toast').all_text_contents())
  self.assertEqual(self.errors,[])
 def test_mobile_tablet_desktop_layout(self):
  self.login()
  for width,height in [(320,740),(375,812),(390,844),(412,915),(768,1024),(1024,768),(1440,900)]:
   self.page.set_viewport_size({'width':width,'height':height})
   for p in ['start','shifts','hours','messages','users','hrcenter','cao','guide']:
    with self.subTest(width=width,page=p):
     self.open(p)
     overflowing=self.page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
     self.assertFalse(overflowing)
     if width<=800:
      self.page.locator('.mobile-menu').click();self.page.locator('.side.mobile-open').wait_for();self.page.locator('.side .nav').last.scroll_into_view_if_needed();self.assertTrue(self.page.locator('.side .nav').last.is_visible());self.page.locator('.drawer-close').click();self.page.locator('.side').wait_for(state='hidden');self.assertFalse(self.page.locator('.side').is_visible())
  self.open('start');self.page.screenshot(path=str(ROOT/'reports'/'desktop.png'),full_page=True)
  self.page.set_viewport_size({'width':390,'height':844});self.open('start');self.page.screenshot(path=str(ROOT/'reports'/'mobile.png'),full_page=True)
 def test_back_and_focus_trap(self):
  self.login();self.open('hours');self.open('shifts');self.page.go_back();self.page.wait_for_function("()=>page==='hours'");self.page.go_forward();self.page.wait_for_function("()=>page==='shifts'")
  self.page.locator('.mobile-menu').click();self.page.keyboard.press('Shift+Tab');self.assertTrue(self.page.evaluate("document.activeElement===document.querySelector('.side .nav:last-child')"));self.page.keyboard.press('Escape');self.page.locator('.side').wait_for(state='hidden');self.assertFalse(self.page.locator('.side').is_visible())
 def test_crud_form_persists_and_no_xss(self):
  self.login();self.open('customers');self.page.get_by_role('button',name='+ Nieuw toevoegen').click();self.page.locator('#field-name').fill('<img src=x onerror=alert(1)> Fictieve klant');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('customers')
  self.assertIn('<img src=x onerror=alert(1)> Fictieve klant',self.page.locator('table').inner_text());self.assertEqual(self.page.locator('table img').count(),0)
  row=self.page.locator('tr').filter(has_text='Fictieve klant');row.get_by_role('button',name='Bewerk').click();self.page.locator('#field-city').fill('Demostad');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('customers');self.assertIn('Demostad',self.page.locator('table').inner_text())
  self.page.locator('tr').filter(has_text='Fictieve klant').get_by_role('button',name='Verwijder').click();self.page.wait_for_function("()=>!records.some(x=>x.city==='Demostad')")
 def test_employee_hours_and_availability(self):
  self.login(True);self.assertIn('Hoi Bart',self.page.locator('.daily-core').inner_text());self.open('hours');self.page.get_by_role('button',name='+ Nieuw toevoegen').click();self.page.locator('#field-hours').fill('2');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('hours');self.assertIn('Ingediend',self.page.locator('table').inner_text());self.assertEqual(self.page.locator('.smartbox').count(),0)
  self.open('availability');self.page.get_by_role('button',name='+ Nieuw toevoegen').click();self.page.locator('#field-start_time').fill('15:00');self.page.locator('#field-end_time').fill('18:00');self.page.locator('#field-status').select_option('Niet beschikbaar');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('availability');self.assertIn('Niet beschikbaar',self.page.locator('table').inner_text())
 def test_planner_suggestion_to_saved_shift(self):
  self.login();self.open('shifts');self.page.locator('#planStart').fill('12:00');self.page.locator('#planEnd').fill('16:00');self.page.get_by_role('button',name='Zoek medewerkers').click();self.page.get_by_role('button',name='Dienst voorbereiden').click();self.page.locator('#field-object_id').select_option('1');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('shifts');self.assertEqual(self.page.locator('.plan-shift').count(),2)
 def test_server_validation_inline(self):
  self.login();self.open('shifts');self.page.get_by_role('button',name='+ Dienst plannen').click();self.page.locator('#field-object_id').select_option('1');self.page.locator('#field-employee_id').select_option('1');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#formError').filter(has_text='Roosterconflict').wait_for();self.assertTrue(self.page.locator('#modalbg').is_visible())
 def test_tour_uses_live_screens(self):
  self.login();self.open('guide');self.page.get_by_role('button',name='Start interactieve rondleiding').click();self.page.locator('.tour-banner').wait_for();self.page.get_by_role('button',name='Volgende stap').click();self.page.locator('.plan-page').wait_for();self.assertIn('Stap 2',self.page.locator('.tour-banner').inner_text());self.page.get_by_role('button',name='Rondleiding sluiten').click();self.assertEqual(self.page.locator('.tour-banner').count(),0)
 def test_accounts_permissions_and_link(self):
  self.login();self.open('users');self.page.locator('#newUsername').fill('Fictieve gebruiker');self.page.locator('#newPassword').fill('FictiefBrowser123!');self.page.locator('#newEmployee').select_option('1');self.page.get_by_role('button',name='Account opslaan').click();self.page.locator('.finding').filter(has_text='Fictieve gebruiker').wait_for()
  row=self.page.locator('.finding').filter(has_text='Fictieve gebruiker');row.get_by_role('button',name='Rechten aanpassen').click();self.page.get_by_label('Documenten',exact=True).check();self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('users');row=self.page.locator('.finding').filter(has_text='Fictieve gebruiker');self.assertIn('Documenten',row.inner_text())
  row.get_by_role('button',name='Account beheren').click();self.page.locator('[name=active]').uncheck();self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.wait_for_selector('#modalbg',state='detached');self.open('users');self.assertIn('Geblokkeerd account',self.page.locator('.finding').filter(has_text='Fictieve gebruiker').inner_text())
 def test_csv_formula_guard(self):
  self.login();self.assertEqual(self.page.evaluate("csvCell('=SUM(A1)')"),'"\'=SUM(A1)"');self.assertEqual(self.page.evaluate("csvCell('Gewoon')"),'"Gewoon"')
if __name__=='__main__':unittest.main(verbosity=2)
