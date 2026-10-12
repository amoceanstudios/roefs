import unittest
import test_enterprise_browser as fixtures
class V6Browser(unittest.TestCase):
 setUpClass=classmethod(fixtures.EnterpriseBrowser.setUpClass.__func__)
 tearDownClass=classmethod(fixtures.EnterpriseBrowser.tearDownClass.__func__)
 setUp=fixtures.EnterpriseBrowser.setUp
 tearDown=fixtures.EnterpriseBrowser.tearDown
 login=fixtures.EnterpriseBrowser.login
 open=fixtures.EnterpriseBrowser.open
 def test_series_form_persists_and_cancellation(self):
  self.login();self.open('calendar');self.page.get_by_role('button',name='Meerdaags en herhalen').click();self.page.get_by_role('button',name='Reeks maken',exact=True).click()
  for name,value in [('title','Fictieve browserreeks'),('start_date','2030-05-06'),('end_date','2030-05-08')]:self.page.locator('#v5-'+name).fill(value)
  self.page.locator('#v5-object_id').select_option('1');self.page.locator('#v5-employee_id').select_option('1');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  rows=self.s.request('/api/v5/planning/series',token=self.admin)[1]['items'];self.assertEqual(len(rows[0]['items']),3)
  self.page.reload();self.page.locator('.daily-home').wait_for();self.open('calendar');self.page.get_by_role('button',name='Meerdaags en herhalen').click();self.page.get_by_role('button',name='Reeks annuleren').click();self.page.locator('#v5-reason').fill('Fictieve sluiting');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  self.assertEqual(self.s.request('/api/v5/planning/series',token=self.admin)[1]['items'][0]['status'],'Geannuleerd')
 def test_rules_settings_saved_without_leaving_settings_and_numbering(self):
  self.login();self.page.evaluate("openPage('settingsv5')");self.page.get_by_role('button',name='Regelprofiel bewerken').click();self.page.locator('#v5-label').fill('Fictief testprofiel');self.page.locator('input[name=enabled]').check();self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached');self.page.get_by_role('button',name='Regelprofiel bewerken').wait_for()
  self.assertEqual(self.s.request('/api/v5/settings',token=self.admin)[1]['labor_rules']['label'],'Fictief testprofiel')
  self.page.get_by_role('button',name='Conceptnummerprofiel').click();self.page.locator('#v5-prefix').fill('DEMO');self.page.locator('input[name=enabled]').check();self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached')
  self.assertEqual(self.s.request('/api/v5/settings',token=self.admin)[1]['invoice_numbering']['prefix'],'DEMO')
