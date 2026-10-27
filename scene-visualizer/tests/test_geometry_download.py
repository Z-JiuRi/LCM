import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from lcm_scene.sources.download_city_geometry import RangeFile,selected,safe_target


class GeometryDownloadTests(unittest.TestCase):
    def test_allowlist_excludes_channels(self):
        for name in ['objects.json','params.json','vertices.npz','vertices_t001.mat','materials.json']:
            self.assertTrue(selected('scene/'+name),name)
        for name in ['power_t001_tx000_r000.npz','phase.mat','channel.npy','inter_loc.npz','rx_pos_r000.npz']:
            self.assertFalse(selected(name),name)
        self.assertTrue(selected('rx_pos_r000.npz',True))

    def test_safe_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertEqual(safe_target(root,'scene/objects.json'),(root/'scene/objects.json').resolve())
            for name in ['../x','/tmp/x','a/../../b','C:/x','a\\b']:
                with self.assertRaises(ValueError): safe_target(root,name)

    def test_http_range_zip_and_crc(self):
        storage=io.BytesIO()
        with zipfile.ZipFile(storage,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('scene/objects.json','{"faces":[]}')
            z.writestr('scene/power.npz',b'x'*100000)
        data=storage.getvalue()
        class Reply(io.BytesIO):
            def __init__(self,body,start,end):
                super().__init__(body)
                self.status=206
                self.url='https://example.invalid/test.zip'
                self.headers={'Content-Range':f'bytes {start}-{end}/{len(data)}'}
        def fake(url,headers):
            start,end=map(int,headers['Range'].removeprefix('bytes=').split('-'))
            return Reply(data[start:end+1],start,end)
        with patch('lcm_scene.sources.download_city_geometry.response',fake):
            remote=RangeFile('https://example.invalid/test.zip',len(data))
            with zipfile.ZipFile(remote) as z:
                self.assertEqual(z.read('scene/objects.json'),b'{"faces":[]}')
            self.assertGreater(remote.network_bytes,0)

    def test_server_without_range_is_rejected(self):
        class Reply(io.BytesIO):
            status=200
            headers={}
        with patch('lcm_scene.sources.download_city_geometry.response',lambda *args:Reply(b'full zip')):
            with self.assertRaises(ValueError): RangeFile('https://example.invalid',100).read(10)


if __name__=='__main__':
    unittest.main()
