"""Verify the already-running Scene Studio URL; no server or RT started."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8767')
    args=parser.parse_args();out=ROOT/'generated/browser/bs';out.mkdir(parents=True,exist_ok=True)
    errors=[];records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1800,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.goto(args.url,wait_until='networkidle');page.locator('#loading').wait_for(state='hidden',timeout=60000)
        for km,count in [(1,6),(2,23),(4,72)]:
            page.locator(f'[data-scene="city-{km}km"]').click()
            page.locator('#loading').wait_for(state='hidden',timeout=60000)
            diag=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            assert diag['bsSiteCount']==count and diag['sectorCount']==count*3,diag
            text=page.locator('#scene-info').inner_text()
            assert '500 m' in text and '65%' in text and '35%' in text,text
            assert '未宣称满足' in text or '未满足' in text or '否' in text,text
            assert '200m格点' not in page.locator('body').inner_text()
            page.locator('#top').click();page.locator('#stage canvas').scroll_into_view_if_needed()
            with page.expect_download() as dl:page.locator('#capture').click()
            dl.value.save_as(str(out/f'city-{km}km-bs-top.png'))
            # Click a physical station from the saved plan, using the top
            # orthographic projection derived from viewer diagnostics/frame().
            diag=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__');bounds=page.locator('#stage canvas').bounding_box()
            radius=(diag['camera'][1]-diag['target'][1]-100)/3
            aspect=bounds['width']/bounds['height'];half=radius*1.12/min(1,aspect)
            radio=json.loads((ROOT/f'data/scenes/deployed-cities/city-{km}km/bs-deployment.json').read_text())
            selected=False
            for site in radio['sites']:
                x,y,_=site['position_m']; cx=diag['target'][0];cy=-diag['target'][2]
                sx=bounds['x']+bounds['width']*(.5+(x-cx)/(2*half*aspect))
                sy=bounds['y']+bounds['height']*(.5-(y-cy)/(2*half))
                page.mouse.click(sx,sy)
                if 'BS站点' in page.locator('#inspector').inner_text():selected=True;break
            assert selected,f'Could not pick BS in {km}km'
            picked=page.locator('#inspector').inner_text()
            assert '选址原因' in picked and '室外' in picked and '候选采样网格' in picked,picked
            for layer in ['bs','sectors']:
                page.locator(f'[data-layer="{layer}"]').uncheck();page.locator(f'[data-layer="{layer}"]').check()
            page.locator('#perspective').click();page.locator('#fit').click()
            with page.expect_download() as dl:page.locator('#capture').click()
            dl.value.save_as(str(out/f'city-{km}km-bs-3d.png'))
            before=page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__')
            box=page.locator('#stage canvas').bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
            page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+65,y+25,steps=8);page.mouse.up()
            page.wait_for_function('(c)=>JSON.stringify(window.__LCM_SCENE_DIAGNOSTICS__.camera)!==JSON.stringify(c)',arg=before['camera'])
            page.locator('#variant').select_option('baseline');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.bsSiteCount')==0
            page.locator('#variant').select_option('environment');page.locator('#loading').wait_for(state='hidden',timeout=60000)
            assert page.evaluate('window.__LCM_SCENE_DIAGNOSTICS__.bsSiteCount')==count
            records.append({'city_km':km,'sites':count,'sectors':count*3,'picked':picked,'diagnostics':diag,'toggles':'passed','baseline_no_bs':'passed','mouse_rotation':'passed','png_download':'passed'})
        browser.close()
    result={'url':args.url,'scenes':records,'errors':errors,'scope':'Replacement 500m-reference synthetic demand plan. No RF validation.'}
    (out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert not errors,errors
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
