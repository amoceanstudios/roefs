"""The two actual post-login destinations, session lifecycle and accessibility."""
import time,unittest
from playwright.sync_api import expect
import test_world_browser as fixture
import test_cinematic_integration as integration
from support import ROOT

class PortalChoiceBrowser(unittest.TestCase):
    setUpClass=classmethod(fixture.WorldBrowser.setUpClass.__func__)
    tearDownClass=classmethod(fixture.WorldBrowser.tearDownClass.__func__)
    setUp=fixture.WorldBrowser.setUp
    tearDown=fixture.WorldBrowser.tearDown
    login=fixture.WorldBrowser.login
    module=integration.CinematicIntegration.module

    def test_old_portal_keyboard_choice_reload_and_switch(self):
        writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') and not r.url.endswith('/api/login') else None)
        self.login(portal=None)
        dialog=self.page.get_by_role('dialog',name='Kies je portaal');expect(dialog).to_be_visible()
        expect(self.page.get_by_role('button',name='Oud Portaal',exact=True)).to_be_focused()
        self.assertTrue(self.page.locator('#root').evaluate('e=>e.inert'))
        self.assertFalse(self.page.locator('.daily-home').is_visible())
        self.page.screenshot(path=str(ROOT/'reports/portal-choice-desktop.png'))
        self.page.keyboard.press('Shift+Tab');expect(self.page.get_by_role('button',name='Uitloggen',exact=True)).to_be_focused()
        self.page.keyboard.press('Tab');self.page.keyboard.press('Enter')
        expect(dialog).to_have_count(0);expect(self.page.locator('.daily-home')).to_be_visible()
        expect(self.page.locator('.daily-core')).to_contain_text('Hoi Beheerder')
        self.assertFalse(self.page.locator('#root').evaluate('e=>e.inert'))
        self.assertIsNone(self.page.locator('#root').get_attribute('aria-hidden'))
        self.page.reload();expect(self.page.locator('.daily-home')).to_be_visible();expect(dialog).to_have_count(0)
        self.page.get_by_role('button',name='Portaal kiezen',exact=True).click();expect(dialog).to_be_visible()
        self.page.get_by_role('button',name='Oud Portaal',exact=True).click()
        self.assertEqual(writes,[],'A portal choice must not modify business data')

    def test_new_portal_real_webgl_module_and_return_to_old_portal(self):
        self.page.emulate_media(reduced_motion='reduce');self.login(portal='new')
        world=self.page.locator('.cinema-world');expect(world).to_have_attribute('data-webgl','active',timeout=30000)
        self.assertIn('ruimte=1#start',self.page.url);expect(self.page.locator('.portal-choice-screen')).to_have_count(0)
        self.module('shifts');expect(self.page.locator('.plan-page')).to_be_visible()
        self.page.get_by_role('button',name='Terug naar wereld').click();expect(world).to_have_attribute('data-stage','overview')
        self.page.get_by_role('button',name='Sluit 3D-portaal').click();expect(self.page.locator('.daily-home')).to_be_visible()
        self.page.reload();expect(self.page.locator('.daily-home')).to_be_visible();expect(world).to_have_count(0)

    def test_failed_login_logout_and_other_account_require_fresh_choice(self):
        self.page.goto(self.s.url);self.page.locator('#password').fill('FoutFictiefWachtwoord')
        self.page.get_by_role('button',name='Veilig inloggen').click();expect(self.page.locator('#loginerr')).not_to_be_empty()
        expect(self.page.locator('.portal-choice-screen')).to_have_count(0)
        self.page.locator('#password').fill('Amocean1!');self.page.get_by_role('button',name='Veilig inloggen').click()
        self.page.get_by_role('button',name='Oud Portaal',exact=True).click();self.page.evaluate('logout()')
        self.page.locator('#username').wait_for();self.page.locator('#username').fill('Bart van Aalde');self.page.locator('#password').fill('Amocean2!')
        self.page.get_by_role('button',name='Veilig inloggen').click();expect(self.page.get_by_role('dialog',name='Kies je portaal')).to_be_visible()
        self.page.get_by_role('button',name='Oud Portaal',exact=True).click();expect(self.page.locator('.daily-core')).to_contain_text('Hoi Bart')
        self.assertEqual(self.page.evaluate("async()=>(await fetch('/api/v5/entities/customers')).status"),403)
        self.page.get_by_role('button',name='Portaal kiezen',exact=True).click();self.page.get_by_role('button',name='Uitloggen',exact=True).click()
        self.page.locator('#username').wait_for();expect(self.page.locator('.portal-choice-screen')).to_have_count(0)
        self.assertFalse(self.page.locator('#root').evaluate('e=>e.inert'))

    def test_mobile_choice_and_new_portal_fallback_keep_employee_permissions(self):
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,a){return String(a[0]).includes('webgl')?null:Reflect.apply(t,s,a)}})")
        self.page.set_viewport_size({'width':390,'height':844});self.login(employee=True,portal=None)
        expect(self.page.get_by_role('dialog',name='Kies je portaal')).to_be_visible()
        for width in (320,390,768):
            self.page.set_viewport_size({'width':width,'height':844})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            for mode in ('old','new'):
                box=self.page.locator('[data-portal-choice='+mode+']').bounding_box();self.assertGreaterEqual(box['x'],0);self.assertLessEqual(box['x']+box['width'],width)
        self.page.set_viewport_size({'width':390,'height':844});self.page.screenshot(path=str(ROOT/'reports/portal-choice-mobile.png'),full_page=True)
        self.page.get_by_role('button',name='Nieuw Portaal',exact=True).tap()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','fallback')
        expect(self.page.locator('[data-world-module=customers]')).to_have_count(0)
        self.module('hours');expect(self.page.locator('#content')).to_be_visible()

    def test_restored_cookie_with_slow_bundle_shows_choice_once(self):
        self.login();self.page.evaluate("sessionStorage.removeItem('roefsPortalChoice')")
        def delayed(route):time.sleep(.7);route.continue_()
        self.page.route('**/spatial.js',delayed);self.page.reload()
        expect(self.page.get_by_role('dialog',name='Kies je portaal')).to_be_visible()
        expect(self.page.locator('.portal-choice-screen')).to_have_count(1)
        self.page.get_by_role('button',name='Oud Portaal',exact=True).click()
        self.page.evaluate('v5Start()');expect(self.page.locator('.portal-choice-screen')).to_have_count(0)
        expect(self.page.locator('[data-spatial-entry=choice]')).to_have_count(1)

    def test_authenticated_direct_module_link_keeps_its_destination(self):
        self.page.emulate_media(reduced_motion='reduce');self.login()
        self.page.goto(self.s.url+'/?ruimte=1#invoices')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=30000)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','invoices')
        expect(self.page.locator('.portal-choice-screen')).to_have_count(0)

    def test_choice_does_not_wait_for_dashboard_widgets(self):
        pending=[]
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,a){return String(a[0]).includes('webgl')?null:Reflect.apply(t,s,a)}})")
        self.page.route('**/api/v5/home',lambda route:pending.append(route))
        self.login(portal=None)
        expect(self.page.get_by_role('dialog',name='Kies je portaal')).to_be_visible()
        self.assertFalse(self.page.locator('.daily-home').is_visible())
        self.assertEqual(len(pending),1,'Home widgets must still be waiting for their genuine server response')
        self.page.get_by_role('button',name='Nieuw Portaal',exact=True).click()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','fallback')
        self.module('hours')
        for route in pending:route.continue_()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-module','hours')
        expect(self.page.locator('.portal-choice-screen')).to_have_count(0)

if __name__=='__main__':unittest.main()
