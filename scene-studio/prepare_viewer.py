"""Export frozen local scene snapshots; never regenerate placements or channels."""
import gzip
import hashlib
import json
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
DATA = STUDIO / 'data'
PUBLIC = STUDIO / 'web/public/scenes'


def prepare():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    catalog = []
    inventory = []
    test_path = PUBLIC / 'verified-street.json'
    test = json.loads(test_path.read_text())
    catalog.append(dict(id='test-4buildings', title='四建筑接缝测试', extent_m=[-40,-25,40,25],
                        instance_count=len(test['buildings']), asset_count=4, source_count=0,
                        data_url='/scenes/verified-street.json', kind='verified', status='已有小规模RT/CSI测试结果'))
    inventory.append(dict(path=str(test_path.relative_to(STUDIO)), sha256=hashlib.sha256(test_path.read_bytes()).hexdigest()))
    city = DATA / 'deepmimo-scenes/city-design'
    for km, title in [(1,'一公里紧凑混合城区'),(2,'两公里大学与商务城区'),(4,'四公里完整混合城区')]:
        folder = city / f'city-{km}km' if km != 4 else city
        source = folder / 'assembled-city.scene.json.gz'
        integrated = DATA / f'scenes/official-cities/city-{km}km'
        resource_folder = integrated if (integrated/'assembled-city.scene.json.gz').is_file() else folder
        scene = json.loads(gzip.decompress((resource_folder/'assembled-city.scene.json.gz').read_bytes()))
        view = json.loads((resource_folder/'assembled-city.view.json').read_text())
        scene['labels'] = view['labels']
        target = PUBLIC / f'city-{km}km.json'
        target.write_text(json.dumps(scene, ensure_ascii=False, separators=(',',':'))+'\n')
        manifest = scene['manifest']
        catalog.append(dict(id=f'city-{km}km', title=title, extent_m=manifest['extent_m'],
                            instance_count=len(scene['instances']), asset_count=len(scene['assets']),
                            source_count=len(manifest['source_usage']), data_url=f'/scenes/city-{km}km.json',
                            kind='city', resource_kind=manifest.get('resource_kind','preview'),
                             status='正式几何与源材料已整合；未重算信道' if resource_folder==integrated else '预览来源合成几何；未计算信道'))
        enhanced = DATA / f'scenes/environment-cities/city-{km}km'
        if (enhanced/'assembled-city.scene.json.gz').is_file():
            (PUBLIC/f'city-{km}km-baseline.json').write_text(json.dumps(scene,ensure_ascii=False,separators=(',',':'))+'\n')
            env=json.loads(gzip.decompress((enhanced/'assembled-city.scene.json.gz').read_bytes()))
            env['labels']=view['labels']
            (PUBLIC/f'city-{km}km-environment.json').write_text(json.dumps(env,ensure_ascii=False,separators=(',',':'))+'\n')
            catalog[-1].update(data_url=f'/scenes/city-{km}km-environment.json',resource_kind='environment-enhanced',
                status='环境增强：平地分区＋源植被体／合成树；未重算信道',
                variants=[{'id':'environment','title':'环境增强版','data_url':f'/scenes/city-{km}km-environment.json'},
                          {'id':'baseline','title':'正式建筑基线','data_url':f'/scenes/city-{km}km-baseline.json'}])
        for name in ['assembled-city.scene.json.gz','assembled-city-manifest.json','assembled-city.view.json']:
            path = folder/name
            inventory.append(dict(path=str(path.relative_to(STUDIO)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for name in ['city-topview.png','city-topview-clean.png','city-topview-preview.png']:
            path = folder/name
            inventory.append(dict(path=str(path.relative_to(STUDIO)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    test_data = DATA / 'scenes/test-4buildings'
    for name in ['samples.npz','results.json']:
        path = test_data/name
        inventory.append(dict(path=str(path.relative_to(STUDIO)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (PUBLIC/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    reports = STUDIO/'generated/reports'
    reports.mkdir(parents=True,exist_ok=True)
    record = reports/'migration-snapshots.json'
    # Preserve the original checksum baseline on repeated exports.
    if not record.exists():
        record.write_text(json.dumps({'date':'2026-10-26','scope':'Scene snapshots and test results retained during consolidation. Code relocation tracked separately.','files':inventory},ensure_ascii=False,indent=2)+'\n')
    print('Prepared four browser scenes:', ', '.join(entry['id'] for entry in catalog))
    return catalog


if __name__ == '__main__':
    prepare()
