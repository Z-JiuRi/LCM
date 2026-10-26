# 1×1 km 与 2×2 km 城市设计

日期：2026-10-26。根据[原四公里设计](README.md)的建筑资产、非等距街坊理念和高度配色，新建两种尺度的独立米制布局。不是原图裁切或缩放，原四公里文件保留。

## 两版设计

| 参数 | 1×1 km | 2×2 km |
|---|---:|---:|
| 总面积 | 1 km² | 4 km² |
| 建筑几何实例 | 665 | 2,306 |
| 实际使用来源组数 | 30 | 32 |
| 实际使用源资产 | 435 | 890 |
| 地块数 | 61 | 200 |
| 建筑基底面积 | 0.1678 km² | 0.7829 km² |
| 建筑基底占全域 | 16.78% | 19.57% |
| 道路车行面并集 | 0.1808 km² | 0.7051 km² |
| 公园绿廊扣除车行面 | 0.0806 km² | 0.3490 km² |
| 种子 | 26102601 | 26102602 |

其余面积包含院落、退界、步行空间和未填满地块。规划功能是设计分配，不能当作源建筑真实用途。

### 1×1 km：紧凑混合城区

中部偏东布置紧凑商务核心，西侧低层生活街区、南侧混合商业街、北侧中高层住宅；西北与南部设置社区公园，东侧连续绿廊。主干道宽22米，集散路16–18米，新增街坊道路9–11米。

Boston 全组团原尺寸约占700米量级，若直接放进一公里城区会过度挤压其他片区。因此选择目标窗口内完整落入的11个建筑，仅整体旋转和平移，不截断或缩放单栋建筑；这是保留相对排列的子集，而不是完整Boston场景。

- [高清带注记图](city-1km/city-topview.png)
- [无标注地图](city-1km/city-topview-clean.png)
- [预览图](city-1km/city-topview-preview.png)
- [几何来源与构建清单](city-1km/assembled-city-manifest.json)
- [导出几何复检](city-1km/export-validation.json)
- [交互查看器](city-1km/city-viewer.html)
- [实例化三维面与布局数据](city-1km/assembled-city.scene.json.gz)

### 2×2 km：大学与商务双核心城区

中心为Boston商务核心，西北为大学／研究园区，东北为城市公园与次级商业中心，西南低层社区、东南中高层住宅，东侧连续绿廊形成过渡。主干道24–26米，集散路18–22米，新增街坊道路9–11米。

完整保留筛选后Boston 53个与ASU 31个建筑的组内相对排列，只整体旋转和平移。筛除不适用对象的规则沿用原生成器，不是源场景无损复原。

- [高清带注记图](city-2km/city-topview.png)
- [无标注地图](city-2km/city-topview-clean.png)
- [预览图](city-2km/city-topview-preview.png)
- [几何来源与构建清单](city-2km/assembled-city-manifest.json)
- [导出几何复检](city-2km/export-validation.json)
- [交互查看器](city-2km/city-viewer.html)
- [实例化三维面与布局数据](city-2km/assembled-city.scene.json.gz)

## 图像与验证

两版带注记图均4250×4550像素，无标注地图4000×4000像素，预览1495×1600像素。北向上，坐标为米制X东、Y北、Z上，地面Z=0。建筑始终保持源尺寸，无缩放。

两版生成前精度与导出舍入后的二维复检均为：建筑投影重叠对0、越出城市0、越出地块0、侵入道路车行面0、侵入公园0。导出复检面积阈值0.01 m²，边界容差0.002 m。建筑基底计入孔洞；地图树点、阴影及公园小径仅用于显示，不是三维场景对象。保留组团内部通道由间隙推断，不是已验证现实道路。

**限制：**建筑来自2026-10-25官方预览缓存，原始来源条款仍适用，完整源工程、材质和再分发许可审查未完成。道路、公园、地块、平地、实例位置均为合成设计；无源地形、材料、TX/RX或信道。尚未验证道路连通路由、建筑入口、三维水密网格或电磁材料，尚未执行新场景射线追踪与信道计算。

本次读取缓存得到1,526个候选资产（原四公里README历史记录为1,317个）；这里只陈述当前实际读取和实例使用结果，不将历史构建计数当作本次输入数量，也未修改原版。

## 复现

在仓库根目录运行：

```sh
uv run --with numpy --with scipy --with pillow --with shapely python output/deepmimo-scenes/city-design/design_city_variants.py
uv run --with numpy --with scipy --with pillow --with shapely python output/deepmimo-scenes/city-design/validate_city_variants.py
```

可使用`--size 1000`或`--size 2000`仅构建某一版。渲染需macOS Hiragino Sans GB字体。不同依赖版本可能影响几何与像素结果。

生成工具：[布局与场景构建](design_city_variants.py)、[地图渲染](render_city_variants.py)、[独立导出检查](validate_city_variants.py)。

交互查看器需HTTP方式加载同目录JSON；可在仓库根目录自行运行`python3 -m http.server 8766 --bind 127.0.0.1`，访问`http://127.0.0.1:8766/output/deepmimo-scenes/city-design/city-1km/city-viewer.html`或对应`city-2km`路径。当前未启动额外服务，浏览器交互未作自动化验证。
