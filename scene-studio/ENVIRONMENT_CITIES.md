# 三尺度环境增强版本

日期：2026-10-26。将一公里规则扩展至两公里和四公里，保持原正式建筑基线、建筑XYZ/旋转/尺寸、道路、公园和地块布局不变；没有新RT或CSI。

| 地图 | 建筑实例 | 地表三角 | 源Boston植被体保留 | 源植被排除 | 合成树 |
|---|---:|---:|---:|---:|---:|
| 1×1 km | 665 | 2,973 | 5 | 14 | 155 |
| 2×2 km | 2,306 | 16,154 | 7 | 12 | 827 |
| 4×4 km | 13,838 | 22,379 | 7 | 12 | 2,893 |

## 共用规则

- 36下载terrain均为Z=0，因此各版使用连续平地，不虚构源地形起伏。
- 地表按道路、公园和其他地表分区，三角投影覆盖完整面积，分区无面积重叠。地表材料分别关联Asphalt_1GHz和ITU Wet earth3.5GHz源数字，属于新布局设计分配，频率适配尚待验证。
- Boston的19个vegetation对象按各城市Boston保留组团的旋转/平移变换，不缩放。检查建筑、道路、城市边界和植被冲突；保留7个与新增楼/路不冲突的对象，其余记录排除原因。
- Boston源植被是25m简化体积，不是现实单株树模型，源材质标记concrete；保留用于可追溯几何展示，不据此宣称已考虑植被电磁传播。
- 公园/绿廊合成种植使用相同7/10/12m三种共享资产，18m格点+确定性抖动。种子1km261026103、2km261026104、4km261026106，各城市独立布置，不缩放一公里树阵。
- 植被底部Z=0，建筑/道路避让；合成格点最小间距约12m，大于最大树冠直径8m加1m间隔。源植被额外做相交检查。
- 全部植被RT禁用。合成树不捏造电磁参数，记录待选植被传播模型。

## 数据

新增版本位于：

- [一公里环境版](data/scenes/environment-cities/city-1km/assembled-city.scene.json.gz)
- [两公里环境版](data/scenes/environment-cities/city-2km/assembled-city.scene.json.gz)、[报告](data/scenes/environment-cities/city-2km/environment-report.json)
- [四公里环境版](data/scenes/environment-cities/city-4km/assembled-city.scene.json.gz)、[报告](data/scenes/environment-cities/city-4km/environment-report.json)

每份包含地表顶点/三角/材质键/分类、植被共享资产和实例、源资源审计、排除原因。原正式基线在official-cities保留，原预览快照也不覆盖。

## 查看与复现

三种城市卡片默认环境增强版，顶部版本选择器可切到正式建筑基线。地形、道路、公园、源植被与合成植被可分别开关；鼠标中键/右键平移保留。

```sh
conda activate lcm
python scene-studio/run.py enhance-environment --size 2000
python scene-studio/run.py enhance-environment --size 4000
python scene-studio/run.py build
python scene-studio/run.py test
python scene-studio/run.py serve --port 8767
```

验证：生产构建通过；15项Python测试通过，环境测试现在覆盖1/2/4km地表覆盖面积、平地高程、材料引用、基线资产/实例一致性；见[测试日志](generated/reports/environment-all-tests.log)。构建脚本对植被和建筑/道路冲突进行检查。浏览器验收结果见[记录](generated/browser/all-environments/acceptance.json)。

此版本只扩展环境几何与来源信息层，不将旧RT试算关联到增强版。下一步应选择/验证地表与植被电磁适配，然后在相同TX/RX下做基线对照RT。
