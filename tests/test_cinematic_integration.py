"""Flights, existing live DOM forms, history/deep links, sound and fallbacks."""
import json,unittest
from playwright.sync_api import expect
import test_world_browser as fixture
from support import ROOT

class CinematicIntegration(unittest.TestCase):
    setUpClass=classmethod(fixture.WorldBrowser.setUpClass.__func__)
    tearDownClass=classmethod(fixture.WorldBrowser.tearDownClass.__func__)
    setUp=fixture.WorldBrowser.setUp
    tearDown=fixture.WorldBrowser.tearDown
    login=fixture.WorldBrowser.login
    enter=fixture.WorldBrowser.enter
    def module(self,id):
        if not self.page.locator('#world-directory').is_visible():self.page.get_by_role('button',name='Modules').click()
        self.page.locator('[data-world-module='+id+']').click()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module',id,timeout=20000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
    def test_flight_original_customer_crud_modal_pointer_and_history(self):
        self.login();self.enter();self.module('customers')
        self.assertIn('ruimte=1#customers',self.page.url)
        self.assertEqual(self.page.locator('.world-module-ui #root').count(),1)
        self.page.locator('#content').get_by_role('button',name='Nieuw toevoegen').click()
        self.page.locator('#field-name').fill('Fictieve ruimtelijke klant')
        self.page.locator('#field-email').fill('ruimtelijk@fictief.invalid')
        self.page.locator('#modalbg').get_by_role('button',name='Opslaan',exact=True).click()
        self.page.locator('#modalbg').wait_for(state='detached')
        expect(self.page.locator('#content')).to_contain_text('Fictieve ruimtelijke klant')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','customers')
        self.page.screenshot(path=str(ROOT/'reports/world-integrated-customers.png'))
        self.page.go_back();expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','overview',timeout=20000)
        self.page.go_forward();expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        expect(self.page.locator('#content')).to_contain_text('Fictieve ruimtelijke klant')
        self.page.get_by_role('button',name='Sluit 3D-portaal').click()
        self.assertEqual(self.page.locator('.cinema-mount').count(),0)
        self.assertNotIn('ruimte=',self.page.url)
        expect(self.page.locator('#content')).to_contain_text('Fictieve ruimtelijke klant')
    def test_deep_link_cookie_reload_and_last_navigation_wins(self):
        self.login();self.page.goto(self.s.url+'/?ruimte=1#invoices')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','invoices',timeout=20000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        self.page.reload();expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','invoices')
        self.page.evaluate("openPage('customers');openPage('shifts');openPage('documents')")
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','documents',timeout=20000)
        self.assertTrue(self.page.url.endswith('#documents'))
        expect(self.page.locator('#content h1')).to_contain_text('Documenten')
        self.page.evaluate("location.hash='hours'")
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','hours',timeout=20000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
    def test_workorder_checklist_persists_through_existing_workspace(self):
        token=self.s.login()
        work=self.s.request('/api/v5/workorders','POST',{'object_id':'1','description':'Fictieve 3D uitvoering','date':'2030-01-07','start_time':'08:00','end_time':'10:00'},token)[1]
        self.login();self.enter();self.page.evaluate("v5Select('workorders')")
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        self.page.locator('.v5-item').filter(has_text='Fictieve 3D uitvoering').get_by_role('button',name='Opdracht openen').click()
        self.page.locator('#modalbg input[name=title]').fill('Vloer schoonmaken')
        self.page.get_by_role('button',name='Taak toevoegen',exact=True).click()
        self.page.get_by_label('Vloer schoonmaken',exact=True).check()
        expect(self.page.get_by_label('Vloer schoonmaken',exact=True)).to_be_checked()
        detail=self.s.request('/api/v5/workorders/'+str(work['id']),token=token)[1]
        self.assertTrue(detail['checklist'][0]['done'])
        self.page.keyboard.press('Escape');self.page.locator('#modalbg').wait_for(state='detached')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside')
    def test_mobile_fallback_sound_reduced_motion_and_back(self):
        self.page.set_viewport_size({'width':390,'height':844});self.page.emulate_media(reduced_motion='reduce')
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,args){return String(args[0]).includes('webgl')?null:Reflect.apply(t,s,args)}})")
        self.login();self.enter();self.module('customers')
        self.page.screenshot(path=str(ROOT/'reports/world-integrated-mobile-fallback.png'))
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.page.evaluate("window.worldSounds=[];window.addEventListener('roefs:world-sound',e=>worldSounds.push(e.detail))")
        self.page.get_by_role('button',name='Geluid uit',exact=True).click()
        expect(self.page.get_by_role('button',name='Geluid aan',exact=True)).to_have_attribute('aria-pressed','true')
        self.module('invoices')
        sounds=self.page.evaluate('worldSounds.filter(e=>e.enabled).map(e=>e.kind)');self.assertIn('flight',sounds);self.assertIn('arrival',sounds)
        self.page.get_by_role('button',name='Geluid aan',exact=True).click()
        self.page.get_by_role('button',name='Terug naar wereld').click()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','overview')
        self.assertEqual(self.page.locator('.world-flash').count(),0)
    def test_all_existing_modules_inside_same_world(self):
        self.page.emulate_media(reduced_motion='reduce');self.login();self.enter()
        ids=self.page.locator('[data-world-module]').evaluate_all('els=>els.map(e=>e.dataset.worldModule)')
        visited=[]
        for id in ids:
            self.page.evaluate('(id)=>openPage(id)',id)
            expect(self.page.locator('.cinema-world')).to_have_attribute('data-module',id,timeout=20000)
            expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
            self.assertEqual(self.page.locator('.world-module-ui #root').count(),1,id)
            self.assertFalse(self.page.locator('#root').evaluate('el=>el.inert'),id)
            visited.append(id)
        (ROOT/'reports/world-module-coverage.json').write_text(json.dumps({'count':len(visited),'modules':visited},indent=2)+'\n')
    def test_mobile_webgl_panel_and_high_quality_refraction(self):
        self.page.set_viewport_size({'width':390,'height':844});self.login();self.enter();self.module('customers')
        self.page.wait_for_timeout(600);self.page.screenshot(path=str(ROOT/'reports/world-integrated-mobile.png'))
        box=self.page.locator('.world-module-panel').bounding_box();self.assertGreaterEqual(box['x'],-1);self.assertLessEqual(box['x']+box['width'],391)
        self.page.get_by_role('button',name='Sluit 3D-portaal').click()
        self.page.set_viewport_size({'width':640,'height':700});self.page.evaluate("openPage('start')");self.enter();self.module('invoices');self.page.get_by_role('combobox',name='Weergavekwaliteit').select_option('high')
        self.page.wait_for_timeout(700);self.page.screenshot(path=str(ROOT/'reports/world-integrated-glass.png'))
        self.assertEqual(self.errors,[])
    def test_original_planning_drag_drop_and_close_during_flight(self):
        token=self.s.login();code,shift,_=self.s.request('/api/v5/shifts','POST',{'object_id':'1','employee_id':'1','date':'2030-04-01','start_time':'08:00','end_time':'09:00','status':'Gepland'},token)
        self.assertIn(code,(200,201),shift)
        self.login();self.enter();self.page.evaluate("v5tab='calendar';plannerDate='2030-04-01';v5period='week';v5group='date';openPage('enterprise')")
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        target=self.page.locator('.v5-day').nth(1);self.page.locator('.v5-shift').first.drag_to(target)
        expect(target.locator('.v5-shift')).to_have_count(1)
        persisted=self.s.request('/api/v5/entities/shifts/'+str(shift['id']),token=token)[1];self.assertEqual(persisted['date'],'2030-04-02')
        self.page.evaluate("openPage('documents')");self.page.get_by_role('button',name='Sluit 3D-portaal').click()
        self.page.locator('.cinema-mount').wait_for(state='detached')
        expect(self.page.locator('#content h1')).to_contain_text('Documenten',timeout=20000)
        self.assertNotIn('ruimte=',self.page.url)
    def test_employee_denied_deep_link_and_logout_cleanup(self):
        self.page.goto(self.s.url+'/?ruimte=1#migration')
        self.page.locator('#username').fill('Bart van Aalde');self.page.locator('#password').fill('Amocean2!');self.page.get_by_role('button',name='Veilig inloggen').click();self.page.locator('.daily-home').wait_for()
        expect(self.page.locator('.toast')).to_contain_text('Geen toegang')
        self.assertEqual(self.page.locator('.cinema-mount').count(),0)
        self.assertEqual(self.page.evaluate("async()=> (await fetch('/api/v5/entities/customers')).status"),403)
        self.page.goto(self.s.url+'/?ruimte=1#hours');expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=20000)
        self.page.locator('.world-module-ui .logout').click();self.page.locator('.loginbox').wait_for()
        self.assertEqual(self.page.locator('.cinema-mount,.world-drag-ghost').count(),0)
        self.assertFalse(self.page.locator('#root').evaluate('e=>e.inert'))
    def test_logout_during_pending_navigation_does_not_restore_private_ui(self):
        import time
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,args){return String(args[0]).includes('webgl')?null:Reflect.apply(t,s,args)}})")
        self.login();self.enter();delayed=[]
        def pause(route):
            response=route.fetch();delayed.append(True);time.sleep(.3);route.fulfill(response=response)
        self.page.route('**/api/records/documents?*',pause)
        self.page.evaluate("async()=>{const pending=openPage('documents');await new Promise(r=>setTimeout(r,100));await logout();await pending;}")
        self.page.locator('.loginbox').wait_for();self.assertTrue(delayed,'A real private response must have been delayed')
        expect(self.page.locator('.loginbox')).to_be_visible()
        self.assertEqual(self.page.locator('.cinema-mount,.world-drag-ghost,#content').count(),0)
        self.assertEqual(self.page.evaluate("async()=> (await fetch('/api/me')).status"),401)

if __name__=='__main__':unittest.main()
