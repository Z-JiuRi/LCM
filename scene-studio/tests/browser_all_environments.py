"""Check all city environment variants in an already running local studio."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8772');args=p.parse_args()
    output=ROOT/'generated/browser/all-environments';output.mkdir(parents=True,exist_ok=True)
    errors=[];results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1100})
        page.on('pageerror',lambda e:errors.append(str(e)))
        for km,count,plants,triangles in [(1,665,160,2973),(2,2306,834,16154),(4,13838,2900,22379)]:
            page.goto(args.url,wait_until='networkidle')
            page.locator('#loading').wait_for(state='hidden',timeout=60000)
            page.locator(f'[data-scene="city-{km}km"]').click()
            page.locator('#loading').wait_for(state='hidden',timeout=60000)
            d=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            assert (d['instanceCount'],d['vegetationCount'],d['terrainTriangles'])==(count,plants,triangles),d
            page.locator('#top').click();page.screenshot(path=str(output/f'city-{km}km-top.png'))
            page.locator('#variant').select_option('baseline');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.vegetationCount')==0
            page.locator('#variant').select_option('environment');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.vegetationCount')==plants
            page.locator('#perspective').click();page.locator('#fit').click()
            with page.expect_download() as info:page.locator('#capture').click()
            info.value.save_as(str(output/f'city-{km}km-3d.png'))
            results.append(d)
        browser.close()
    report={'cities':results,'errors':errors,'version_switch_and_png_download':'passed'}
    (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
