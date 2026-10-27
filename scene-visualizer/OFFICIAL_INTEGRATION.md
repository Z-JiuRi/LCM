# 三城市正式资源整合

日期：2026-10-26。读取用户已下载的根data/36来源，核验文件哈希和对象格式，匹配至现有合成城市；没有移动、缩放或新增建筑，没有重新计算信道。

## 实际整合结果

| 城市 | 正式几何匹配资产 | 建筑实例（原布局不变） | 来源 | 带命名空间的材料记录 |
|---|---:|---:|---:|---:|
| 1×1 km | 435 / 435 | 665 | 30 | 30 |
| 2×2 km | 890 / 890 | 2,306 | 32 | 32 |
| 4×4 km | 1,317 / 1,317 | 13,838 | 36 | 36 |

正式下载资源合计7,073,019字节（约7.07MB），36来源108个几何/参数文件。匹配最大顶点误差8.3773×10⁻⁵m，约0.084mm；容差2mm。全部面顺序和每面点序与原预览对应一致，原source_object_index经几何验证后均对应正式objects数组索引。原预览快照与测试数据保持不变。

正式源数据含重复对象，几何唯一匹配率1km约14.71%、2km19.55%、4km14.20%；重复对象的顶点、面拓扑和材料完全一致。整合并未假装唯一辨认：保留几何验证后的原索引，并在official_geometry_duplicate_ids记录全部等价ID。严格1mm舍入hash会因格边界产生假不一致，实际采用双向最近顶点距离及有序面验证。

三城正式整合版本导出二维复检均为重叠0、城市越界0、地块越界0、道路侵入0、公园侵入0。官方面片相较舍入轮廓存在微小投影差，逐资产值记录在报告；这不是新布局设计。

## 存放位置

原合成预览快照继续保存在data/deepmimo-scenes/city-design，不覆盖。新增整合版本：

- [一公里版本](data/scenes/official-cities/city-1km/assembled-city.scene.json.gz)、[匹配报告](data/scenes/official-cities/city-1km/integration-report.json)
- [两公里版本](data/scenes/official-cities/city-2km/assembled-city.scene.json.gz)、[匹配报告](data/scenes/official-cities/city-2km/integration-report.json)
- [四公里版本](data/scenes/official-cities/city-4km/assembled-city.scene.json.gz)、[匹配报告](data/scenes/official-cities/city-4km/integration-report.json)
- [整合总表](data/scenes/official-cities/integration-summary.json)

每资产增加official_object_id/index/name、正式faces、face_material_keys、误差和等价ID；保留原asset id、source_origin_m、source_object_index及轮廓。每实例rotation/position/parcel/role均不变。

每材料使用source:material_ID命名空间，保留params原记录及参考频率。每来源记录版本、objects/params/vertices哈希、原RT参数与源场景元数据，不自动引入原TX/RX或信道。

## 材料含义

所有实际选用建筑面引用各来源material_0，名称为ITU Concrete 3.5GHz；这里是真实下载包的材料记录，不是凭图颜色猜测。它仍是源仿真材质，不是建筑实测材质。

不同来源不可抹平成同一个默认值：Boston scattering_model=none，其他35来源directive；MAT来源sigma=.08987，NPZ来源sigma=.089875。还保留εr、厚度、粗糙度、散射/交叉极化等原字段。网页属性可检查记录，但渲染颜色仍为高度示意，未宣称已把这些材料转换为Sionna可运行电磁材质。

原源地形/植被不移植到新布局；合成道路、公园与平地保持原设计，地面材料还需新场景配置。部分源建筑base_z非零，按原保存的source_origin归一化后放到新城市z=0，既有行为没有改变。

## 查看和复现

正式整合版本是工作台的建筑基线；当前默认入口还叠加[环境增强](<ENVIRONMENT_CITIES.md>)与[BS 规划](<BS_DEPLOYMENT.md>)，可切回正式建筑基线。已构建后刷新页面，点击建筑可看到正式ID、原预览索引、来源版本和材料记录。四建筑测试不变。旧一公里RT试算使用原预览和假设材料，仅保留历史结果，未关联为本版本信道。

```sh
conda activate lcm
python scene-visualizer/run.py integrate-city --downloads ./data
python scene-visualizer/run.py build
python scene-visualizer/run.py test
python scene-visualizer/run.py serve --port 8767
```

[整合工具](python/lcm_scene/city/integrate_official.py)仅本地处理，无联网下载。默认新增版本到data/scenes/official-cities；原快照不覆盖。重新生成布局不会自动改变整合版本，需重新执行整合并构建。

## 验证记录

- TypeScript/Vite生产构建通过。
- 14项Python测试全部通过，含正式面材料关联、布局不变、源快照校验；见[测试日志](generated/reports/official-tests.log)。
- 三城市浏览器派生数据中的assets/materials/instances已逐项核对，与正式整合场景文件一致。
- Chrome实际检查四场景相机响应、建筑点选、官方对象ID与源材料字段、截图下载及移动布局，控制台错误0；见[浏览器日志](generated/reports/official-browser-check.log)。
- 测试服务已停止，用户自行启动即可，不需再次构建。

## 边界

几何匹配和二维放置检查不等于水密/流形/外法线、电磁材料映射、传播收敛或许可证审查完成。没有源信道下载或新RT，源文件再分发仍受原条款约束。下一步RT应明确选用正式版本并完成材料/网格适配，不能直接把旧试算结果当作已重算。
