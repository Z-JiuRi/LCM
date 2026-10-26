"""Browser checks for 1km environment/baseline switching; no RT invocation."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8770');args=parser.parse_args()
    output=ROOT/'generated/browser/environment';output.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1600,'height':1100})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url+'/#city-1km',wait_until='networkidle')
        page.locator('#loading').wait_for(state='hidden',timeout=60000)
        d=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
        assert d['instanceCount']==665 and d['vegetationCount']==160 and d['terrainTriangles']==2973,d
        page.screenshot(path=str(output/'enhanced-workspace.png'))
        page.locator('#top').click()
        page.screenshot(path=str(output/'enhanced-top.png'))
        page.locator('[data-layer="vegetation"]').uncheck()
        page.locator('[data-layer="vegetation"]').check()
        page.locator('#variant').select_option('baseline')
        page.locator('#loading').wait_for(state='hidden',timeout=60000)
        baseline=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
        assert baseline['instanceCount']==665 and baseline['vegetationCount']==0,baseline
        page.locator('#variant').select_option('environment')
        page.locator('#loading').wait_for(state='hidden',timeout=60000)
        assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.vegetationCount')==160
        page.locator('#perspective').click();page.locator('#fit').click()
        with page.expect_download() as info:page.locator('#capture').click()
        download=info.value;download.save_as(str(output/'enhanced-3d.png'))
        page.locator('[data-scene="city-2km"]').click();page.locator('#loading').wait_for(state='hidden',timeout=60000)
        assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.instanceCount')==2306
        page.locator('[data-scene="city-4km"]').click();page.locator('#loading').wait_for(state='hidden',timeout=60000)
        assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.instanceCount')==13838
        browser.close()
    report={'enhanced':d,'baseline':baseline,'errors':errors,'version_switch':'passed','other_cities':'unchanged counts'}
    (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
