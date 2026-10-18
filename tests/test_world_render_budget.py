"""Actual WebGL render activity, reduced motion and wake-up after navigation."""
import json,unittest
from playwright.sync_api import expect
import test_world_browser as fixture
import test_cinematic_integration as integration
from support import ROOT

class WorldRenderBudget(unittest.TestCase):
    setUpClass=classmethod(fixture.WorldBrowser.setUpClass.__func__)
    tearDownClass=classmethod(fixture.WorldBrowser.tearDownClass.__func__)
    setUp=fixture.WorldBrowser.setUp
    tearDown=fixture.WorldBrowser.tearDown
    login=fixture.WorldBrowser.login
    enter=fixture.WorldBrowser.enter
    module=integration.CinematicIntegration.module

    def metrics(self):return self.page.evaluate('ROEFSSpatial.metrics()')

    def stationary_sample(self):
        self.page.wait_for_timeout(900)
        before=self.metrics();self.page.wait_for_timeout(1100);after=self.metrics()
        self.assertEqual(after['renderMode'],'on-demand')
        self.assertIsNone(after['fps'],'A stationary view must not report a misleading FPS')
        self.assertLessEqual(after['renderedFrames']-before['renderedFrames'],2)
        return {'before':before,'after':after}

    def test_stationary_scene_sleeps_and_real_customer_form_still_saves(self):
        self.page.emulate_media(reduced_motion='reduce');self.login();self.enter()
        overview=self.stationary_sample()
        self.page.get_by_role('button',name='Modules').click()
        self.page.locator('[data-world-module=customers]').focus()
        expect(self.page.locator('.world-object-label')).to_have_text('Klanten en relaties')
        self.assertGreater(self.metrics()['renderedFrames'],overview['after']['renderedFrames'])
        self.module('customers')
        inside=self.stationary_sample()
        self.page.locator('#content').get_by_role('button',name='Nieuw toevoegen').click()
        self.page.locator('#field-name').fill('Fictieve stille werkruimte')
        self.page.locator('#field-email').fill('stil@fictief.invalid')
        self.page.locator('#modalbg').get_by_role('button',name='Opslaan',exact=True).click()
        self.page.locator('#modalbg').wait_for(state='detached')
        expect(self.page.locator('#content')).to_contain_text('Fictieve stille werkruimte')
        self.page.reload()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','inside',timeout=30000)
        expect(self.page.locator('#content')).to_contain_text('Fictieve stille werkruimte')
        self.page.get_by_role('button',name='Terug naar wereld').click()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','overview')
        returned=self.stationary_sample()
        (ROOT/'reports/world-render-budget.json').write_text(json.dumps({'environment':'Chromium software WebGL; no physical GPU benchmark','overview':overview,'inside':inside,'returned':returned,'customerPersistedAfterReload':True},indent=2)+'\n')

    def test_motion_toggle_restarts_and_stops_actual_frames(self):
        self.page.emulate_media(reduced_motion='reduce');self.login();self.enter()
        self.stationary_sample()
        self.page.get_by_role('button',name='Beweging uit').click()
        self.page.wait_for_timeout(1200);before=self.metrics()
        self.page.wait_for_timeout(1200);after=self.metrics()
        self.assertEqual(after['renderMode'],'continuous')
        self.assertGreater(after['renderedFrames']-before['renderedFrames'],3)
        self.module('shifts');expect(self.page.locator('.plan-page')).to_be_visible()
        self.page.get_by_role('button',name='Terug naar wereld').click()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-stage','overview',timeout=20000)
        self.page.get_by_role('button',name='Beweging aan').click()
        self.stationary_sample()

if __name__=='__main__':unittest.main()
