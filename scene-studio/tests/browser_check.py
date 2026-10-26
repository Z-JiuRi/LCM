"""Read-only browser acceptance; saves screenshots/download evidence under generated.
Run: uv run --with playwright python scene-studio/tests/browser_check.py --url http://127.0.0.1:8767
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8767')
    args=parser.parse_args()
    output=ROOT/'generated/browser'
    output.mkdir(parents=True,exist_ok=True)
    errors=[]
    records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1600,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
        page.goto(args.url,wait_until='networkidle')
        page.locator('#loading').wait_for(state='hidden',timeout=60000)
        for scene,count in [('test-4buildings',4),('city-1km',665),('city-2km',2306),('city-4km',13838)]:
            page.locator(f'[data-scene="{scene}"]').click()
            page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert f'{count:,}' in page.locator('#stats').inner_text() or str(count) in page.locator('#stats').inner_text()
            page.locator('#top').click()
            page.screenshot(path=str(output/f'{scene}-top.png'))
            page.locator('#perspective').click()
            before=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            if scene!='test-4buildings':
                assert before['instanceCount']==count
                assert before['sourceTriangles']>0
                assert before['labelCount']<=80
            canvas=page.locator('#stage canvas')
            bounds=canvas.bounding_box()
            cx=bounds['x']+bounds['width']*.5
            cy=max(bounds['y']+30,min(bounds['y']+bounds['height']*.5,page.viewport_size['height']-80))
            page.mouse.move(cx,cy)
            page.mouse.down()
            page.mouse.move(cx+90,cy+30,steps=12)
            page.mouse.up()
            page.mouse.wheel(0,-200)
            page.mouse.move(cx,cy)
            page.mouse.down(button='right')
            page.mouse.move(cx+25,cy+20,steps=5)
            page.mouse.up(button='right')
            page.wait_for_function('(previous) => JSON.stringify(window.__LCM_SCENE_DIAGNOSTICS__.camera) !== JSON.stringify(previous)',arg=before['camera'],timeout=10000)
            after=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            assert before['camera']!=after['camera'],f'Camera did not respond in {scene}'
            page.locator('#fit').click()
            page.screenshot(path=str(output/f'{scene}-workspace.png'))
            page.screenshot(path=str(output/f'{scene}-3d.png'))
            # Top camera + grid scan locates a real building; selection must report height.
            page.locator('#top').click()
            selected=False
            for fx,fy in [(0.5,0.5),(.55,.5),(.4,.35),(.6,.4),(.35,.5),(.7,.7),(.3,.3),(.6,.65),(.5,.3),(.4,.7)]:
                page.mouse.click(bounds['x']+bounds['width']*fx,bounds['y']+bounds['height']*fy)
                if page.locator('#inspector dl').count():
                    selected=True
                    break
            assert selected,f'No picked building in {scene}'
            assert '高度' in page.locator('#inspector').inner_text()
            page.locator('#focus').click()
            if scene=='test-4buildings':
                assert page.locator('#timeline').is_visible()
                page.locator('#next').click()
                assert page.locator('#sample').inner_text().startswith('2 /')
                assert page.locator('#beam svg').count()==1
            else:
                assert not page.locator('#timeline').is_visible()
                assert not page.locator('#radio').is_visible()
            records.append({'scene':scene,'instances':count,'pick':page.locator('#inspector').inner_text(),'three_view_mouse_controls':'camera change verified','diagnostics':after})
        page.locator('#perspective').click()
        page.locator('#fit').click()
        with page.expect_download() as download_info:
            page.locator('#capture').click()
        download=download_info.value
        download.save_as(str(output/download.suggested_filename))
        assert (output/download.suggested_filename).stat().st_size>10000
        # Check compatibility pages remain usable.
        page.goto(args.url+'/editor.html',wait_until='networkidle')
        page.locator('#stage canvas').wait_for(timeout=30000)
        assert page.locator('#scene-count').inner_text()
        page.goto(args.url+'/deepmimo.html',wait_until='networkidle')
        page.locator('#stage canvas').wait_for(timeout=30000)
        # Small viewport: ensure the main scene remains available.
        page.set_viewport_size({'width':390,'height':844})
        page.goto(args.url+'/#city-1km',wait_until='networkidle')
        page.locator('#loading').wait_for(state='hidden',timeout=60000)
        page.locator('#stage canvas').scroll_into_view_if_needed()
        page.screenshot(path=str(output/'city-1km-mobile.png'))
        browser.close()
    result={'url':args.url,'scenes':records,'errors':errors,'screenshot_download':download.suggested_filename}
    (output/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
