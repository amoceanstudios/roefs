import csv,io,unittest
from playwright.sync_api import expect
import test_enterprise_browser as fixtures
from services.spreadsheets import xlsx
class MigrationBrowser(unittest.TestCase):
 setUpClass=classmethod(fixtures.EnterpriseBrowser.setUpClass.__func__)
 tearDownClass=classmethod(fixtures.EnterpriseBrowser.tearDownClass.__func__)
 setUp=fixtures.EnterpriseBrowser.setUp
 tearDown=fixtures.EnterpriseBrowser.tearDown
 login=fixtures.EnterpriseBrowser.login
 def wizard(self,filename,data,name):
  self.page.evaluate("openPage('migration')");self.page.get_by_role('button',name='+ Nieuwe gegevens importeren',exact=True).click();self.page.locator('input[name=source]').fill('Fictieve browserexport');self.page.locator('#migrationCategory').select_option('customers');self.page.locator('#migrationFile').set_input_files({'name':filename,'mimeType':'application/octet-stream','buffer':data});self.page.get_by_role('button',name='Bestand controleren en kolommen koppelen').click();self.page.locator('select[name=map_0]').select_option('external_id');self.page.get_by_role('button',name='Testmigratie uitvoeren',exact=True).click();self.page.get_by_role('button',name='Definitief importeren',exact=True).wait_for()
  before=self.s.request('/api/v5/entities/customers?q='+name,token=self.admin)[1];self.assertEqual(before['total'],0)
  self.page.locator('input[name=confirmed]').check();self.page.get_by_role('button',name='Definitief importeren',exact=True).click();expect(self.page.locator('#content')).to_contain_text('Voltooid');self.assertEqual(self.s.request('/api/v5/entities/customers?q='+name,token=self.admin)[1]['total'],1)
  self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),391)
 def test_csv_mapping_preview_real_import_report_and_reload(self):
  self.login();self.wizard('<img src=x>.csv',b'External Reference;Bedrijfsnaam\n0007;FictieveBrowserCSV\n','FictieveBrowserCSV')
  self.assertEqual(self.page.locator('.headline img').count(),0,'Bestandsnaam mag geen HTML-element worden')
  with self.page.expect_download() as event:self.page.get_by_role('button',name='Verslag / fouten downloaden').click()
  self.assertEqual(event.value.failure(),None)
  self.page.reload();self.page.locator('.daily-home').wait_for();self.page.evaluate("openPage('migration')");expect(self.page.locator('#content')).to_contain_text('<img src=x>.csv')
 def test_xlsx_template_download_and_import(self):
  self.login();self.page.evaluate("openPage('migration')");self.page.get_by_role('button',name='+ Nieuwe gegevens importeren',exact=True).click()
  with self.page.expect_download() as event:self.page.get_by_role('button',name='Download Excel-template',exact=True).click()
  self.assertEqual(event.value.failure(),None);self.page.evaluate('closeModal()')
  data=xlsx([('Gegevens',[['External Reference','Bedrijfsnaam'],['0008','FictieveBrowserXLSX']])]);self.wizard('fictief.xlsx',data,'FictieveBrowserXLSX')
 def test_school_demo_persisted_service_form(self):
  self.login();self.page.evaluate("openPage('settingsv5')");self.page.get_by_role('button',name='Fictief schoolvoorbeeld openen / toevoegen').click();expect(self.page.locator('#modalbg')).to_contain_text('460.0 afgesproken uren');expect(self.page.locator('#modalbg')).to_contain_text('4 bezoeken afgesproken; 0 datums gekozen')
  self.page.get_by_role('button',name='Afspraken bekijken / wijzigen').first.click();self.page.locator('input[name=hours_4]').fill('3');self.page.get_by_role('button',name='Afspraken opslaan').click();expect(self.page.locator('#modalbg')).to_contain_text('480 afgesproken uren')
  self.page.reload();self.page.locator('.daily-home').wait_for();self.page.evaluate("openPage('settingsv5')");self.page.get_by_role('button',name='Fictief schoolvoorbeeld openen / toevoegen').click();expect(self.page.locator('#modalbg')).to_contain_text('480 afgesproken uren')
 def test_onboarding_accounting_and_scope_admin_forms(self):
  self.login();self.page.evaluate("openPage('onboarding')");self.page.get_by_role('button',name='Stap bijwerken').first.click();self.page.locator('[name=status]').select_option('Goedgekeurd');self.page.locator('[name=owner]').fill('Fictieve acceptant');self.page.locator('[name=evidence]').fill('Fictief bewijs');self.page.get_by_role('button',name='Stap opslaan').click();expect(self.page.locator('#content')).to_contain_text('Fictieve acceptant')
  with self.page.expect_download() as event:self.page.get_by_role('button',name='Onboardingrapport downloaden').click()
  self.assertIsNone(event.value.failure())
  self.page.evaluate("openPage('accounting')");self.page.locator('[name=provider]').select_option('exact');self.page.locator('[name=administration]').fill('Fictieve administratie');self.page.get_by_role('button',name='Configuratie opslaan').click();expect(self.page.locator('[name=administration]')).to_have_value('Fictieve administratie');self.page.get_by_role('button',name='Verbinding testen').click();expect(self.page.locator('#content')).to_contain_text('Verbindingstest mislukt')
  self.page.evaluate("openPage('scopes')");self.page.get_by_role('button',name='Beleid wijzigen').first.click();self.page.locator('[name=enabled]').check();self.page.locator('[name=departments]').fill('Fictieve afdeling');self.page.locator('[name=default_department]').fill('Fictieve afdeling');self.page.get_by_role('button',name='Beleid opslaan').click();expect(self.page.locator('#content')).to_contain_text('Fictieve afdeling');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),391)
