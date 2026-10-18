"""Real WebGL, raycasting, persistence, conflict, drag/drop and fallback tests."""
import unittest
import io
from PIL import Image
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from support import LiveServer, ROOT

class SpatialBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play=sync_playwright().start()
        cls.browser=cls.play.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--enable-unsafe-swiftshader'])
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.play.stop()
    def setUp(self):
        self.s=LiveServer();self.admin=self.s.login()
        mobile='mobile' in self._testMethodName
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},has_touch=mobile,is_mobile=mobile)
        self.page=self.context.new_page();self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.s.request('/api/v5/entities/customers','POST',{'name':'Fictieve Ruimteklant','email':'ruimte@example.invalid'},self.admin)
        self.work=self.s.request('/api/v5/workorders','POST',{'object_id':'1','description':'Fictieve ruimtetaak','date':'2030-01-07','start_time':'08:00','end_time':'10:00'},self.admin)[1]
        self.task=self.s.request(f"/api/v5/workorders/{self.work['id']}/checklist",'POST',{'title':'Vloer controleren'},self.admin)[1]
    def tearDown(self):
        self.context.close();self.s.close();self.assertEqual(self.errors,[])
    def enter(self):
        self.page.goto(self.s.url)
        self.page.locator('#username').fill('Roefs');self.page.locator('#password').fill('Amocean1!')
        self.page.get_by_role('button',name='Veilig inloggen').click()
        self.page.locator('.daily-home').wait_for()
        self.page.locator('.daily-actions').get_by_role('button',name='Ruimtelijke werkplek',exact=True).click()
        self.page.locator('[data-loading]').wait_for(state='detached')
    def open_node(self,text):
        self.page.get_by_role('searchbox',name='Zoek ruimtelijke gegevens').fill(text)
        self.page.locator('[data-results] button').first.click()
        self.page.locator('.spatial-panel [data-detail] input,.spatial-board').first.wait_for()
    def test_desktop_canvas_raycast_customer_storage_conflict_and_cleanup(self):
        self.enter()
        canvas=self.page.locator('.spatial-canvas');expect(canvas).to_be_visible()
        # Read WebGL pixels immediately after a render; prove visible non-background geometry.
        self.page.wait_for_timeout(1200)
        # Browser screenshot reads the composited canvas despite WebGL buffer discard.
        image=Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
        pixels=sum(1 for r,g,b in image.get_flattened_data() if max(r,g,b)>75)
        self.assertGreater(pixels,100)
        (ROOT/'reports').mkdir(exist_ok=True)
        self.page.screenshot(path=str(ROOT/'reports/spatial-desktop.png'))
        # A camera drag that ends at its starting point must not become a click.
        self.page.mouse.move(600,450);self.page.mouse.down();self.page.mouse.move(660,450,steps=5);self.page.mouse.move(600,450,steps=5);self.page.mouse.up()
        self.assertEqual(self.page.locator('.spatial-panel').count(),0)
        self.page.get_by_role('button',name='Overzicht',exact=True).click();self.page.wait_for_timeout(1100)
        # Use projected world label coordinates, then click the canvas itself (raycast).
        point=self.page.locator('.spatial-node-label').first.evaluate('el=>{const r=el.getBoundingClientRect();return {x:r.x+45,y:r.y-20}}')
        self.page.mouse.click(point['x'],point['y'])
        expect(self.page.locator('.spatial-panel')).to_be_visible()
        self.open_node('Fictieve Ruimteklant')
        self.page.locator('[name=phone]').fill('0400000123')
        self.page.get_by_role('button',name='Wijzigingen opslaan').click()
        expect(self.page.locator('[data-feedback]')).to_have_text('Klantgegevens opgeslagen')
        rows=self.s.request('/api/v5/entities/customers?q=Fictieve%20Ruimteklant',token=self.admin)[1]['items'];row=rows[0]
        self.assertEqual(row['phone'],'0400000123')
        self.s.request(f"/api/v5/entities/customers/{row['id']}",'PUT',{'phone':'0409999999','version':row['version']},self.admin)
        self.page.locator('[name=phone]').fill('0401111111')
        self.page.get_by_role('button',name='Wijzigingen opslaan').click()
        expect(self.page.locator('[data-error]')).not_to_be_empty()
        persisted=self.s.request(f"/api/v5/entities/customers/{row['id']}",token=self.admin)[1]
        self.assertEqual(persisted['phone'],'0409999999')
        self.page.get_by_role('button',name='Sluiten',exact=True).first.click()
        expect(self.page.locator('.daily-home')).to_be_visible()
        self.assertEqual(self.page.locator('.spatial-host').count(),0)
        self.page.reload();self.page.locator('.daily-home').wait_for()
        self.page.locator('.daily-actions').get_by_role('button',name='Ruimtelijke werkplek',exact=True).click()
        self.page.locator('[data-loading]').wait_for(state='detached');self.open_node('Fictieve Ruimteklant')
        expect(self.page.locator('[name=phone]')).to_have_value('0409999999')
    def test_mobile_tasks_drag_drop_and_touch_alternative(self):
        self.page.set_viewport_size({'width':390,'height':844});self.enter()
        self.page.wait_for_timeout(1200);self.page.screenshot(path=str(ROOT/'reports/spatial-mobile.png'))
        image=Image.open(io.BytesIO(self.page.locator('.spatial-canvas').screenshot())).convert('RGB')
        self.assertGreater(sum(1 for r,g,b in image.get_flattened_data() if max(r,g,b)>75),30)
        self.open_node('Fictieve ruimtetaak')
        self.page.locator('[data-task]').drag_to(self.page.locator('[data-done=true]'))
        expect(self.page.locator('[data-done=true] [data-task]')).to_have_count(1)
        self.page.locator('[data-task]').tap()
        expect(self.page.locator('[data-done=false] [data-task]')).to_have_count(1)
        self.page.locator('[name=title]').fill('Ramen controleren')
        self.page.get_by_role('button',name='Taak opslaan',exact=True).click()
        expect(self.page.locator('[data-feedback]')).to_have_text('Taak opgeslagen')
        detail=self.s.request(f"/api/v5/workorders/{self.work['id']}",token=self.admin)[1]
        self.assertEqual(len(detail['checklist']),2);self.assertFalse(detail['checklist'][0]['done'])
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        bounds=self.page.locator('.spatial-panel').bounding_box();self.assertGreaterEqual(bounds['x'],0);self.assertLessEqual(bounds['x']+bounds['width'],390)
        self.page.screenshot(path=str(ROOT/'reports/spatial-mobile-panel.png'))
    def test_webgl_unavailable_still_edits_real_records(self):
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,args){return String(args[0]).includes('webgl')?null:Reflect.apply(t,s,args)}})")
        self.enter();expect(self.page.locator('[data-instructions]')).to_contain_text('3D is hier niet beschikbaar')
        self.open_node('Fictieve Ruimteklant');self.page.locator('[name=contact]').fill('Fictieve contactpersoon')
        self.page.get_by_role('button',name='Wijzigingen opslaan').click()
        expect(self.page.locator('[data-feedback]')).to_have_text('Klantgegevens opgeslagen')

    def test_employee_cannot_enter_or_read_customers(self):
        self.page.goto(self.s.url)
        self.page.locator('#username').fill('Bart van Aalde');self.page.locator('#password').fill('Amocean2!')
        self.page.get_by_role('button',name='Veilig inloggen').click();self.page.locator('.daily-home').wait_for()
        self.assertEqual(self.page.locator('.daily-actions').get_by_role('button',name='Ruimtelijke werkplek',exact=True).count(),0)
        self.page.evaluate("openPage('spatial')")
        self.assertEqual(self.page.locator('.spatial-host').count(),0)
        status=self.page.evaluate("async()=> (await fetch('/api/v5/entities/customers')).status")
        self.assertEqual(status,403)

if __name__=='__main__':unittest.main()
