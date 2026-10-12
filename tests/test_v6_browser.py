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
 def test_script_csp_blocks_inline_handlers_and_command_injection(self):
  response=self.page.goto(self.s.url);policy=response.headers['content-security-policy'];self.assertIn("script-src 'self'",policy);self.assertNotIn("script-src 'self' 'unsafe-inline'",policy)
  self.page.evaluate("""() => {window.inlineExecuted=false;const button=document.createElement('button');button.id='unsafe-test';button.setAttribute('onclick','window.inlineExecuted=true');document.body.append(button);button.click()}""")
  self.assertFalse(self.page.evaluate('window.inlineExecuted'))
  self.page.evaluate("""() => {const button=document.createElement('button');button.id='command-test';button.setAttribute('data-roefs-click',"eval('window.inlineExecuted=true')");document.body.append(button);button.click()}""")
  self.assertFalse(self.page.evaluate('window.inlineExecuted'))
  self.login();self.open('calendar');self.assertEqual(self.page.locator('[onclick],[onsubmit],[onchange]').count(),0)
 def test_resize_keyboard_saves_actual_end_time(self):
  code,shift,_=self.s.request('/api/v5/shifts','POST',{'object_id':1,'employee_id':1,'date':'2030-04-01','start_time':'08:00','end_time':'12:00'},self.admin);self.assertEqual(code,200,shift)
  self.login();self.open('calendar');self.page.evaluate("plannerDate='2030-04-01';v5Calendar()")
  self.page.get_by_role('button',name='↕ Eindtijd aanpassen').first.click();slider=self.page.get_by_role('slider');slider.focus();slider.press('ArrowRight');self.assertEqual(self.page.locator('#v6resizeTime').inner_text(),'12:01')
  self.page.get_by_role('button',name='Tijdvak opslaan').click();self.page.locator('#modalbg').wait_for(state='detached')
  row=self.s.request('/api/records/shifts/'+str(shift['id']),token=self.admin)[1];self.assertEqual(row['end_time'],'12:01')
 def test_contract_location_and_renewal_forms_persist(self):
  code,contract,_=self.s.request('/api/v5/entities/contracts','POST',{'name':'Fictief browsercontract','customer_id':1,'object_id':1,'monthly_value':'100','start_date':'2030-01-01','end_date':'2030-12-31','status':'Actief'},self.admin);self.assertEqual(code,201,contract)
  self.login();self.open('contracts');self.page.locator('.v5-item').filter(has_text='Fictief browsercontract').get_by_role('button',name='Contractdossier').click()
  self.page.get_by_role('button',name='Locaties wijzigen').click();self.page.locator('input[name=frequency_1]').fill('Elke maandag');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.get_by_role('heading',name='Contractdossier · Fictief browsercontract').wait_for()
  self.page.get_by_role('button',name='Verlengen',exact=True).click();self.page.locator('#v5-reason').fill('Fictieve verlengingsafspraak');self.page.locator('#v5-end_date').fill('2031-12-31');self.page.locator('#v5-renewal_date').fill('2031-11-01');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.get_by_role('heading',name='Contractdossier · Fictief browsercontract').wait_for()
  saved=self.s.request('/api/v5/contracts/'+str(contract['id']),token=self.admin)[1];self.assertEqual(saved['locations'][0]['frequency'],'Elke maandag');self.assertEqual(saved['contract']['end_date'],'2031-12-31');self.assertEqual(saved['events'][0]['reason'],'Fictieve verlengingsafspraak')
 def test_clock_rejected_start_keeps_form_then_saved_cancel(self):
  code,work,_=self.s.request('/api/v5/workorders','POST',{'object_id':1,'description':'Fictieve browserklok','date':'2030-04-01','start_time':'08:00','end_time':'12:00'},self.admin);self.assertEqual(code,200,work)
  self.login();self.open('workorders');self.page.locator('.v5-item').filter(has_text='Fictieve browserklok').get_by_role('button',name='Opdracht openen').click();self.page.get_by_role('button',name='Inklokken',exact=True).click();self.page.locator('#v5-employee_id').select_option('1');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#v5error').filter(has_text='Klok in bij').wait_for();self.assertEqual(self.page.locator('#v5-employee_id').input_value(),'1');self.assertEqual(self.page.evaluate('v5tab'),'workorders')
  self.s.request('/api/v5/shifts','POST',{'object_id':1,'employee_id':1,'date':work['date'],'start_time':'08:00','end_time':'12:00','workorder_id':work['id']},self.admin)
  for state in ('Gepland','Toegewezen'):
   code,work,_=self.s.request('/api/v5/workorders/'+str(work['id'])+'/transition','POST',{'version':work['version'],'state':state},self.admin);self.assertEqual(code,200,work)
  self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.get_by_role('button',name='Klok annuleren',exact=True).wait_for();self.assertEqual(len(self.s.request('/api/v5/clock',token=self.admin)[1]),1)
  self.page.get_by_role('button',name='Klok annuleren',exact=True).click();self.page.locator('#v5-reason').fill('Fictieve verkeerde start');self.page.get_by_role('button',name='Opslaan',exact=True).click();self.page.locator('#modalbg').wait_for(state='detached');self.assertEqual(self.s.request('/api/v5/clock',token=self.admin)[1],[])
