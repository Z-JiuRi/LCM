# 一公里环境增强版本

日期：2026-10-26。新增版本，保留正式建筑基线；2km、4km未修改。665个建筑的位置XYZ、旋转、尺寸以及道路/公园/地块布局均不变。没有执行新RT或生成新CSI。

## 源资源审计结果

对根data/36下载场景的objects.json及vertices核查：36个terrain对象高程均为Z=0，**没有起伏地形资源**。不能为显得“有地形”而把合成坡地当作源数据。

只有Boston提供19个vegetation标签对象，均高25m、形状为简化体积，源面材料全部引用material_0（ITU Concrete）。这不是完整植物/树冠电磁模型，不能直接说是19棵真实树或给它们套混凝土就认为考虑了植被衰减。

## 本次新增

1. **统一连续地表**：覆盖1km²，Z=0，按道路、公园和其他地表分区，2973个三角；区间没有面积重叠或遗漏，不叠加36个共面源地面。
2. **地表材料关联**：道路关联源Taito的Asphalt_1GHz数值（新布局设计分配，频率适配待验证），公园和其他地表关联ITU Wet earth3.5GHz数值（不是新城实测地面）。
3. **源植被体保留**：Boston植被按相同保留组团变换旋转-12°和平移，5个满足新城建筑/道路避让检查；14个与建筑/道路冲突排除，原因逐对象记录。不缩放、不伪装成树木。
4. **合成公园种植**：155个新设计树模型，3种共享资产，高7/10/12m。确定性种子261026103，18m格点加少量抖动，树冠避让建筑、道路、绿廊路径和其他植被。来源标记synthetic-design。
5. **双版本查看**：一公里卡片可选择环境增强版与正式建筑基线，查看器可开关地表/植被和源/合成植被并点选属性。

## 电磁边界

所有植被rt_enabled=false；源简化体保留原混凝土绑定用于来源核查，合成树不捏造εr/σ，记录Foliage model pending。它们目前进入地图几何和信息层，尚未作为植被传播模型应用于RT。先前试算脚本仍采用原基线，不能声称它已经包含这次植被或地表分区。

这版环境增强不等于有高程山坡，也不等于所有源环境无损复原。根据审计维持平地是数据支持的选择；若下一步需要起伏实验，应另做明确的合成地形或引入真实DEM并设计建筑台地。

## 几何检查

- 建筑与原正式基线assets/instances逐项一致。
- 三角投影总面积与并集面积均1,000,000m²。
- 地表分区重叠/未覆盖面积约0（浮点误差级）。
- 植被体/树冠侵入建筑和道路均0，植被底部Z=0。
- 单元测试15项全部通过，包含地表覆盖、材料键、植被有效性和原快照校验；见[测试日志](generated/reports/environment-tests.log)。

- Chrome实际显示增强版地形2973三角/植被160实例，切换基线后植被0，再切回增强160；2km/4km建筑数量不变；PNG下载通过，pageerror0，见[浏览器记录](generated/browser/environment/acceptance.json)。
- [增强版三维截图](generated/browser/environment/enhanced-3d.png)、[增强版俯视截图](generated/browser/environment/enhanced-top.png)。

## 数据和工具

- [环境版场景](data/scenes/environment-cities/city-1km/assembled-city.scene.json.gz)
- [环境报告](data/scenes/environment-cities/city-1km/environment-report.json)：36来源对象高程范围、文件哈希、植被排除原因、种植数量和QA。
- [正式建筑基线](data/scenes/official-cities/city-1km/assembled-city.scene.json.gz)
- [构建工具](python/lcm_scene/city/enhance_environment.py)

```sh
conda activate lcm
python scene-studio/run.py enhance-environment --downloads ./data
python scene-studio/run.py build
python scene-studio/run.py test
python scene-studio/run.py serve --port 8767
```

重建增强版只覆盖环境版生成结果，不覆盖正式基线或其他城市。源数据许可仍适用；合成模型/地表材质分配必须与源记录区分。
