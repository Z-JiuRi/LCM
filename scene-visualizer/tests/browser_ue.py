"""Exercise existing viewer UE overlays. No server or RT is launched."""
import argparse
import json
from pathlib import Path
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8767');args=parser.parse_args()
    out=ROOT/'generated/browser/ue';out.mkdir(parents=True,exist_ok=True)
    errors=[];records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1800,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#city-1km');page.locator('#loading').wait_for(state='hidden',timeout=60000)
        for km,bs in [(1,6),(2,23),(4,72)]:
            page.locator(f'[data-scene="city-{km}km"]').click();page.locator('#loading').wait_for(state='hidden',timeout=60000)
            points=np.load(ROOT/f'data/scenes/ue-candidates/city-{km}km/ue_candidates.npy',allow_pickle=False)
            diag=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            assert diag['uePointCount']==len(points) and diag['ueVisible'],diag
            assert diag['bsSiteCount']==bs,diag
            np.testing.assert_array_equal(diag['uePositionsSample'],points[:3])
            assert '5 m' in page.locator('#ue-note').inner_text()
            assert '1.5 m' in page.locator('#ue-note').inner_text()
            page.locator('#top').click()
            page.wait_for_function('window.__LCM_SCENE_DIAGNOSTICS__.render.points > 0')
            with page.expect_download() as download:page.locator('#capture').click()
            download.value.save_as(str(out/f'city-{km}km-ue-top.png'))
            toggle=page.locator('[data-layer="ue"]');toggle.uncheck()
            page.wait_for_function('window.__LCM_SCENE_DIAGNOSTICS__.render.points === 0')
            assert not page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.ueVisible')
            toggle.check();page.wait_for_function('window.__LCM_SCENE_DIAGNOSTICS__.render.points > 0')
            page.locator('#perspective').click()
            before=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.camera')
            canvas=page.locator('#stage canvas');canvas.scroll_into_view_if_needed();b=canvas.bounding_box()
            page.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);page.mouse.down()
            page.mouse.move(b['x']+b['width']/2+65,b['y']+b['height']/2+30,steps=6);page.mouse.up()
            page.wait_for_function('(before)=>JSON.stringify(window.__LCM_SCENE_DIAGNOSTICS__.camera)!==JSON.stringify(before)',arg=before)
            page.locator('#variant').select_option('baseline');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.uePointCount')==0
            assert toggle.is_disabled()
            page.locator('#variant').select_option('environment');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.uePointCount')==len(points)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.ueVisible')
            records.append({'city_km':km,'ue_count':len(points),'bs_count':bs,'diagnostics':diag,'checks':'full count, coordinates, draw, toggle, camera, baseline switch'})
        # Rapid switch must not attach stale point buffers.
        page.locator('[data-scene="city-4km"]').click();page.locator('[data-scene="city-1km"]').click()
        page.wait_for_function('window.__LCM_SCENE_DIAGNOSTICS__.sceneId==="city-1km" && window.__LCM_SCENE_DIAGNOSTICS__.uePointCount===29726')
        page.locator('[data-scene="test-4buildings"]').click();page.locator('#loading').wait_for(state='hidden',timeout=60000)
        assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.uePointCount')==0
        assert page.locator('[data-layer="ue"]').is_disabled()
        browser.close()
    result={'url':args.url,'scenes':records,'errors':errors,'scope':'UE candidate display only; no RT'}
    (out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
