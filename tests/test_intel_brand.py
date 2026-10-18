"""Self-hosted design assets, current product identity and readable destinations."""
import unittest
import urllib.parse
from playwright.sync_api import expect
import test_world_browser as fixture
from support import ROOT

class IntelBrandBrowser(unittest.TestCase):
    setUpClass=classmethod(fixture.WorldBrowser.setUpClass.__func__)
    tearDownClass=classmethod(fixture.WorldBrowser.tearDownClass.__func__)
    setUp=fixture.WorldBrowser.setUp
    tearDown=fixture.WorldBrowser.tearDown
    login=fixture.WorldBrowser.login

    def font_loaded(self,selector):
        self.assertTrue(self.page.evaluate("async()=>{await document.fonts.ready;return document.fonts.check('24px AmoceanScreen')}"))
        self.assertIn('AmoceanScreen',self.page.locator(selector).evaluate('e=>getComputedStyle(e).fontFamily'))

    def test_assets_are_local_decodable_and_only_explicit_files_are_exposed(self):
        for path,mime,minimum in [('amocean-display.ttf','font/ttf',90000),('amocean-night.webp','image/webp',50000)]:
            status,body,headers=self.s.request('/assets/'+path)
            self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],mime);self.assertEqual(headers['X-Content-Type-Options'],'nosniff');self.assertGreater(len(body),minimum)
        token=self.s.login()
        for path in ('/assets/../server.py','/assets/unknown.webp','/assets/AMOCEAN-DISPLAY-OFL.txt'):
            self.assertEqual(self.s.request(path,token=token)[0],404)
        self.page.goto(self.s.url)
        self.assertGreater(self.page.evaluate("async()=>{const image=new Image();image.src='/assets/amocean-night.webp';await image.decode();return image.naturalWidth}"),1000)

    def test_login_choice_and_old_portal_identity_with_loaded_title_font(self):
        self.page.goto(self.s.url);expect(self.page.locator('.loginbox h1')).to_have_text('AMOCEAN INTEL')
        self.font_loaded('.loginbox h1');self.page.locator('.splash').wait_for(state='hidden');self.page.screenshot(path=str(ROOT/'reports/intel-login.png'))
        self.page.locator('#password').fill('Amocean1!');self.page.get_by_role('button',name='Veilig inloggen').click()
        expect(self.page.get_by_role('dialog',name='Kies je portaal')).to_be_visible()
        expect(self.page.locator('.portal-choice-brand')).to_contain_text('AMOCEAN INTEL')
        self.font_loaded('#portal-choice-title');self.page.screenshot(path=str(ROOT/'reports/intel-choice-desktop.png'))
        for width in (320,390,768):
            self.page.set_viewport_size({'width':width,'height':844})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            for mode in ('old','new'):
                box=self.page.locator('[data-portal-choice='+mode+']').bounding_box();self.assertLessEqual(box['x']+box['width'],width)
        self.page.set_viewport_size({'width':390,'height':844});self.page.screenshot(path=str(ROOT/'reports/intel-choice-mobile.png'))
        self.page.get_by_role('button',name='Oud Portaal',exact=True).tap()
        expect(self.page.locator('.daily-home')).to_be_visible();self.assertIn('AMOCEAN INTEL',self.page.title())
        self.page.locator('.mobile-menu').tap();expect(self.page.locator('.side .brand')).to_contain_text('AMOCEAN INTEL')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)

    def test_new_world_brand_font_and_photographic_texture_load(self):
        self.page.emulate_media(reduced_motion='reduce');self.login(portal='new')
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','active',timeout=30000)
        self.page.locator('.world-ready').wait_for(timeout=30000)
        expect(self.page.locator('.world-brand')).to_contain_text('AMOCEAN INTEL');self.font_loaded('.world-intro h1')
        self.page.wait_for_timeout(500);self.page.screenshot(path=str(ROOT/'reports/intel-world.png'))
        self.assertNotIn('ROEFS ONE',self.page.locator('.cinema-world').inner_text())
        for width in (320,390):
            self.page.set_viewport_size({'width':width,'height':844})
            for name in ('Modules','Sluit 3D-portaal'):
                box=self.page.get_by_role('button',name=name).bounding_box();self.assertGreaterEqual(box['x'],0);self.assertLessEqual(box['x']+box['width'],width)
            audio=self.page.get_by_role('button',name='Geluid uit',exact=True).bounding_box();intro=self.page.locator('.world-intro').bounding_box()
            self.assertLessEqual(audio['y']+audio['height'],intro['y'],'Mobile audio controls must not overlap titles or footer')
        self.page.screenshot(path=str(ROOT/'reports/intel-world-mobile.png'))
        self.page.get_by_role('button',name='Sluit 3D-portaal').click();expect(self.page.locator('.daily-home')).to_be_visible()

    def test_export_and_new_authenticator_setup_use_current_product_name(self):
        token=self.s.login()
        status,pdf,_=self.s.request('/api/v5/reports/management/pdf?section=customers&from=2030-01-01&to=2030-12-31',token=token)
        self.assertEqual(status,200);self.assertTrue(pdf.startswith(b'%PDF-1.4'));self.assertIn(b'AMOCEAN INTEL',pdf);self.assertNotIn(b'ROEFS ONE',pdf)
        status,setup,_=self.s.request('/api/v5/security/mfa/setup','POST',{'password':'Amocean1!'},token)
        self.assertEqual(status,200)
        uri=urllib.parse.urlsplit(setup['uri']);self.assertEqual(urllib.parse.parse_qs(uri.query)['issuer'],['AMOCEAN INTEL'])

if __name__=='__main__':unittest.main()
