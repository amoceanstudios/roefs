"""Phase 1: module catalogue, live canvas, effects, fallbacks and original routes."""
import io,json,unittest
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from support import LiveServer,ROOT

class WorldBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play=sync_playwright().start()
        cls.browser=cls.play.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--enable-unsafe-swiftshader'])
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.play.stop()
    def setUp(self):
        self.s=LiveServer();self.context=self.browser.new_context(viewport={'width':1440,'height':1000},has_touch=True)
        self.page=self.context.new_page();self.errors=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('console',lambda m:self.errors.append(m.text) if m.type=='error' and ('WebGLProgram' in m.text or 'Shader Error' in m.text) else None)
    def tearDown(self):self.context.close();self.s.close();self.assertEqual(self.errors,[])
    def login(self,employee=False):
        self.page.goto(self.s.url);self.page.locator('#username').fill('Bart van Aalde' if employee else 'Roefs');self.page.locator('#password').fill('Amocean2!' if employee else 'Amocean1!')
        self.page.get_by_role('button',name='Veilig inloggen').click();self.page.locator('.daily-home').wait_for()
    def enter(self):
        self.page.locator('.daily-actions').get_by_role('button',name='3D-portaal',exact=True).click()
        self.page.locator('.world-ready').wait_for(timeout=30000)
    def screenshot_and_pixels(self,name):
        self.page.wait_for_timeout(1800)
        self.page.screenshot(path=str(ROOT/'reports'/f'world-{name}.png'))
        image=Image.open(io.BytesIO(self.page.locator('.cinema-world canvas').screenshot())).convert('RGB')
        self.assertGreater(sum(1 for r,g,b in image.get_flattened_data() if max(r,g,b)>65),300)
    def test_desktop_all_modules_live_scene_and_unchanged_route(self):
        self.login();before=self.page.url
        expected=self.page.evaluate("[...new Set(Object.values(GROUPS).flat())].filter(canView)")
        writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
        self.enter();expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','active')
        self.assertIn('ruimte=1',self.page.url);self.assertTrue(self.page.locator('#root').evaluate('e=>e.inert'))
        self.screenshot_and_pixels('desktop')
        timing=self.page.evaluate('''async()=>{const samples=[];let previous=performance.now();await new Promise(resolve=>{const tick=now=>{samples.push(now-previous);previous=now;samples.length<36?requestAnimationFrame(tick):resolve()};requestAnimationFrame(tick)});samples.shift();samples.sort((a,b)=>a-b);return {renderer:'Chromium software WebGL',quality:document.querySelector('.cinema-world').dataset.quality,medianFrameMs:samples[Math.floor(samples.length/2)],p95FrameMs:samples[Math.floor(samples.length*.95)]}}''')
        (ROOT/'reports/world-frame-sample.json').write_text(json.dumps(timing,indent=2)+'\n')
        self.page.get_by_role('button',name='Modules').click()
        actual=self.page.locator('[data-world-module]').evaluate_all('els=>els.map(e=>e.dataset.worldModule)')
        self.assertEqual(actual,expected);self.assertEqual(writes,[])
        self.page.locator('[data-world-module=shifts]').focus();expect(self.page.locator('.world-hover strong')).to_have_text('Planning')
        self.page.locator('[data-world-module=shifts]').click()
        self.page.locator('.plan-page').wait_for()
        self.assertTrue(self.page.url.endswith('#shifts'));self.assertFalse(self.page.locator('#root').evaluate('e=>e.inert'))
        self.assertEqual(self.page.locator('.cinema-mount').count(),1)
    def test_slow_bundle_cookie_reload_adds_entries_once(self):
        self.login()
        import time
        def delayed(route):
            time.sleep(.8);route.continue_()
        self.page.route('**/spatial.js',delayed)
        self.page.reload();self.page.locator('.daily-home').wait_for()
        expect(self.page.locator('[data-spatial-entry=world]')).to_have_count(1)
        expect(self.page.locator('[data-spatial-entry=data]')).to_have_count(1)
        self.page.evaluate('v5Start()')
        expect(self.page.locator('[data-spatial-entry=world]')).to_have_count(1)
        expect(self.page.locator('[data-spatial-entry=data]')).to_have_count(1)
    def test_canvas_module_opens_original_screen(self):
        self.login();self.enter();self.page.wait_for_timeout(1800)
        self.page.mouse.move(940,680)
        expect(self.page.locator('.world-object-label')).to_be_visible()
        label=self.page.locator('.world-object-label').inner_text()
        route=self.page.evaluate('(label)=>Object.keys(NAMES).find(k=>NAMES[k]===label)',label)
        self.page.mouse.click(940,680)
        self.page.wait_for_function('(route)=>location.hash==="#"+route',arg=route)
        self.assertEqual(self.page.locator('.cinema-mount').count(),1)
        (ROOT/'reports/world-raycast-check.json').write_text(json.dumps({'actualCanvasClick':True,'label':label,'route':route},indent=2)+'\n')
    def test_mobile_reduced_motion_touch_and_cleanup(self):
        self.page.set_viewport_size({'width':390,'height':844});self.page.emulate_media(reduced_motion='reduce');self.login();self.enter()
        expect(self.page.get_by_role('button',name='Beweging uit')).to_have_attribute('aria-pressed','true')
        self.screenshot_and_pixels('mobile')
        canvas=self.page.locator('.cinema-world canvas');first=Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
        self.page.wait_for_timeout(250);second=Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
        self.assertEqual(first.tobytes(),second.tobytes(),'Reduced motion must produce a stationary scene')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.page.get_by_role('button',name='Modules').tap();self.page.get_by_role('searchbox',name='Zoek een module').fill('facturatie')
        expect(self.page.locator('[data-world-module=invoices]')).to_be_visible()
        self.page.keyboard.press('Escape');self.assertEqual(self.page.locator('.cinema-mount').count(),0)
        self.assertFalse(self.page.locator('#root').evaluate('e=>e.inert'))
        self.enter();self.page.get_by_role('button',name='Sluit 3D-portaal').tap();self.assertEqual(self.page.locator('.cinema-mount').count(),0)
    def test_no_webgl_and_employee_catalogue_keep_original_access(self):
        self.page.add_init_script("HTMLCanvasElement.prototype.getContext=new Proxy(HTMLCanvasElement.prototype.getContext,{apply(t,s,args){return String(args[0]).includes('webgl')?null:Reflect.apply(t,s,args)}})")
        self.login(employee=True);expected=self.page.evaluate("[...new Set(Object.values(GROUPS).flat())].filter(canView)");self.enter()
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','fallback')
        actual=self.page.locator('[data-world-module]').evaluate_all('els=>els.map(e=>e.dataset.worldModule)')
        self.assertEqual(actual,expected);self.assertNotIn('migration',actual)
        self.page.locator('[data-world-module=employeeportal]').click();self.page.locator('#content').wait_for()
        self.assertEqual(self.page.locator('.cinema-mount').count(),1)
        self.assertTrue(self.page.url.endswith('#employeeportal'))
    def test_full_effect_stack_compiles_and_draws(self):
        self.page.set_viewport_size({'width':640,'height':480});self.login();self.enter()
        self.page.get_by_role('combobox',name='Weergavekwaliteit').select_option('high')
        self.page.wait_for_timeout(1500)
        expect(self.page.locator('.cinema-world')).to_have_attribute('data-webgl','active')
        self.screenshot_and_pixels('effects')
        self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
