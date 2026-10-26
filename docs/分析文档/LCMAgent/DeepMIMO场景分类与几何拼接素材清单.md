# DeepMIMO 场景分类与几何拼接素材清单

核验日期：2026-10-25。目录快照 SHA-256：`fab7fa73aca4e8a7fddb8cfb9f083fa886efb1f3f6c392055bf796a9579ec0b2`。

> 本清单服务于**几何拼接后重新计算信道**。没有新增拼接地图、没有重新仿真信道，也没有验证 LCMAgent 收益。UMa-like/UMi-like 是本项目的素材与原部署近似分类，不是 DeepMIMO 官方标签或 3GPP 符合性认证。

## 1. 核验范围与关键结论

- 官方目录共 **233 条记录**，按 `(subMenu, linkName)` 去重后 **228 个条目**：v4 为 196 个，旧版为 32 个；这不是 228 张独立几何地图。
- 逐项读取目录参数；取得 **170 个 v4 场景预览**，读取站点位置、地形、建筑对象与网格范围；**20 个 v4 条目**读取了一个原始路径矩阵并统计 LoS/NLoS/无记录路径。没有将部分条目的核验写成全库核验。
- 原始城市系列主要是低位部署，不能统称 UMa。`city_0_newyork_3p5` 的已读站点为 6 m；同名 `_s` 变体的预览站点为 z=20 m。**变体不仅可能改变频段，也可能改变追踪器、站点和几何表达。**
- 上海样例原站 z=10 m，应归 UMi-like；ASU 校园原站 z=22 m，可作为 UMa-like 候选。几何拼接后重新布置站点时，分类需要重新确定。
- 当前没有确认到一套明确按标准 RMa 或 InF 配置的现成条目；低层住宅、Florida villa 不能仅因建筑稀疏就叫 RMa。

## 2. 分类规则

1. **环境与部署**：I1/I2/I3、Office Floor 1 归 InH-like；飞行 RIS/无人机单列；室外依原站高、地形和部署说明分组。低位城市站高不超过 15 m 暂归 UMi-like；约 20 m 级及以上（本表启发式阈值 18 m）暂归 UMa-like；中间高度或证据缺失保留待定。这些阈值是项目筛选规则，不是 3GPP 的类别判据。
2. **站高来源**：优先用预览 TX 坐标减去其垂足处最高地形表面高程；地形平坦时等价于减去平面高程。地形投影采用面片三角化，仅用于本次素材筛选，不是另一个经过验证的射线追踪器。无法取得地面时，不把世界坐标 z 自动当 AGL。旧版有明确高度文字时单独采用。
3. **LoS/NLoS**：只在原始 `inter` 矩阵的有效路径上判断；出现交互码 0 记 LoS，有有效路径但无 0 记 NLoS，全无有效路径另记无记录路径。NaN 不当作零；无直达记录也可能受原始射线追踪范围和路径截断影响。
4. **统计单位**：一个明确列名的 TX/RX 网格、一个快照，不是整个场景所有站点的聚合比例。多站场景可同时包含 LoS 与 NLoS，表中应读作 `UMi-LoS 子集 + UMi-NLoS 子集`，不能给整图强贴一个 LoS 标签。
5. **未核验不填值**：HTTP 429、HTTP 500、缺失几何或不支持的归档格式均保留为未核验。官网 `environment` 把部分 I1/I2/I3 条目标成 outdoor，与室内说明冲突；本表采用实际场景身份而不是盲信筛选字段。

## 3. 用于拼接的场景族

| 场景族 | 本次分类 | 拼接素材用途与证据边界 |
|---|---|---|
| ASU Campus；`asu_campus_3p5` | UMa-like；LoS 与 NLoS 原始子集已确认 | 校园、中等高度楼群和开阔空间；22 m 站点。`_10cm` 未因同族而继承统计 |
| `city_0…19_*_3p5_s`，共 20 个 Sionna 变体 | UMa-like 候选 | 已取得各自预览；选中 TX 的 z=20 m，局部地面约 0.3 m；与不带 `_s` 的原始低站版本分开 |
| `city_0_newyork_new` | UMa-like 候选 | 20 m 站点的派生城市几何；不是默认 New York 条目的别名 |
| 城市系列默认版本、28 GHz 版本及 `_lwm` | 以 UMi-like 为主，逐项见全表 | 初始城市组常为 6 m 站点，后续城市组常为 10 m；不同频段及追踪设置不能互相继承路径比例 |
| Boston5G；`boston5g_*`；Boston5G RIS | UMi-like | 原站 15 m，适合高楼街道几何；RIS 原说明有 NLoS 用户，但不等于全部用户 NLoS |
| O1 / `o1_*`；O1 Blockage / `o1b_*` | UMi-like／相应候选 | 街道、路口与显式遮挡面；现有变体下载限流者保留未核验 |
| O2 Dynamic；Dynamic Doppler DD1 | UMi-like，动态街道 | 旧版说明为移动交通；前者 6 m，后者 4.5 m 基站；适合后续动态遮挡素材，不冒充已读全部时序 |
| I1、I2、I3；Office Floor 1 | InH-like | 会议室、走廊与办公室；I2 是显式直达遮挡布局，不据此判整个网格全 NLoS |
| Florida villa 系列 | 低层住宅几何；已取得低位站高者归 UMi-like | 多个派生/试验性条目；大网格不代表丰富建筑，更不自动等于 RMa |
| `asu_campus_3p5_dyn` | 混合：低位移动 TX + 高位固定 TX | 先前原包抽查的两个 TX 分别在 z=3 m 与 z=20 m；不是已验证的移动建筑遮挡 |
| O1 Drone / `o1_drone_200` | 空地/RIS | 单列，不套地面 UMa/UMi；只有需要无人机扩展时才纳入 |

## 4. 原始路径核验结果

下表的数量是原始文件中接收位置数，不是同时在线 UE 数，也不是重新仿真的结果。已读文件的名称、选择方法、dtype、SHA-256、TX 坐标和完整掩码说明见 [path-states.json](../../../output/deepmimo-scenes/classification/path-states.json)。不把下表比例外推到同族其他频段或其他 TX。

| 条目 | LoS | NLoS | 无记录路径 | 网格位置总数 | 原始成员 |
|---|---:|---:|---:|---:|---|
| `asu_campus_3p5` | 25,998 | 59,159 | 46,774 | 131,931 | `inter_t001_tx000_r000.mat` |
| `city_0_newyork_3p5` | 4,467 | 11,836 | 15,416 | 31,719 | `inter_t001_tx000_r000.mat` |
| `city_10_austin_3p5` | 8,802 | 17,878 | 8,255 | 34,935 | `inter_t001_tx000_r000.mat` |
| `city_12_fortworth_3p5` | 3,378 | 20,511 | 14,417 | 38,306 | `inter_t001_tx000_r000.mat` |
| `city_13_columbus_28` | 2,060 | 8,432 | 32,228 | 42,720 | `inter_t001_tx000_r000.mat` |
| `city_13_columbus_3p5` | 2,060 | 5,295 | 35,365 | 42,720 | `inter_t001_tx000_r000.mat` |
| `city_14_charlotte_3p5` | 13,697 | 19,119 | 5,416 | 38,232 | `inter_t001_tx000_r000.mat` |
| `city_15_indianapolis_3p5` | 12,983 | 15,076 | 11,141 | 39,200 | `inter_t001_tx000_r000.mat` |
| `city_17_seattle_3p5` | 10,680 | 8,454 | 18,791 | 37,925 | `inter_t001_tx000_r000.mat` |
| `city_19_oklahoma_3p5` | 6,746 | 20,600 | 11,006 | 38,352 | `inter_t001_tx000_r000.mat` |
| `city_1_losangeles_3p5` | 4,090 | 15,821 | 8,631 | 28,542 | `inter_t001_tx000_r000.mat` |
| `city_2_chicago_28` | 3,609 | 6,842 | 17,349 | 27,800 | `inter_t001_tx000_r000.mat` |
| `city_2_chicago_3p5` | 3,609 | 6,842 | 17,349 | 27,800 | `inter_t001_tx000_r000.mat` |
| `city_3_houston_3p5` | 5,912 | 13,490 | 11,706 | 31,108 | `inter_t001_tx000_r000.mat` |
| `city_4_phoenix_3p5` | 2,227 | 11,262 | 28,883 | 42,372 | `inter_t001_tx000_r000.mat` |
| `city_5_philadelphia_3p5` | 3,139 | 8,332 | 27,725 | 39,196 | `inter_t001_tx000_r000.mat` |
| `city_6_miami_3p5` | 6,739 | 20,322 | 15,923 | 42,984 | `inter_t001_tx000_r000.mat` |
| `city_7_sandiego_3p5` | 8,737 | 13,896 | 13,799 | 36,432 | `inter_t001_tx000_r000.mat` |
| `city_8_dallas_3p5` | 6,877 | 21,902 | 10,551 | 39,330 | `inter_t001_tx000_r000.mat` |
| `city_99_shanghai_3p5` | 55,519 | 20,960 | 19,881 | 96,360 | `inter_t001_tx000_r000.npz` |

## 5. 全量逐项分类

`P`=取得官方预览；`R`=读取所列原始路径矩阵；`D`=仅目录或旧版文字。`L+N` 表示在该文件中确实发现两种子集，`待核验`不表示不存在。几何尺寸是预览建筑与地形的 XY 外包范围，不是有效用户区、覆盖半径或可直接拼接的矩形边界。完整参数见 [classification.json](../../../output/deepmimo-scenes/classification/classification.json)。

### v2（8 项）

| 场景 | 部署归类 | 原站 z / AGL（m） | LoS/NLoS | 预览几何宽×深（m） | 证据 |
|---|---|---|---|---|---|
| `O1` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `O1 Blockage` | UMi-like | 说明高度 6 | 遮挡布局；子集待核验 | 未取得 | D |
| `O1 Drone` | 空地/RIS | 说明高度 6 | 待核验 | 未取得 | D |
| `O2 Dynamic` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `i1` | InH-like | 待核验 | 待核验 | 未取得 | D |
| `i2` | InH-like | 待核验 | 遮挡布局；子集待核验 | 未取得 | D |
| `i3` | InH-like | 待核验 | 待核验 | 未取得 | D |
| `Boston5G` | UMi-like | 说明高度 15 | 待核验 | 未取得 | D |

### v3（4 项）

| 场景 | 部署归类 | 原站 z / AGL（m） | LoS/NLoS | 预览几何宽×深（m） | 证据 |
|---|---|---|---|---|---|
| `Boston5G RIS` | UMi-like | 说明高度 15 | 待核验 | 未取得 | D |
| `Dynamic Doppler DD1` | UMi-like | 说明高度 4.5 | 待核验 | 未取得 | D |
| `ASU Campus` | UMa-like | 说明高度 22 | LoS+NLoS（旧版说明） | 未取得 | D |
| `Office Floor 1` | InH-like | 说明高度 3 | 待核验 | 未取得 | D |

### v3/city_series（20 项）

| 场景 | 部署归类 | 原站 z / AGL（m） | LoS/NLoS | 预览几何宽×深（m） | 证据 |
|---|---|---|---|---|---|
| `New York` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Los Angeles` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Chicago` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Houston` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Phoenix` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Philadelphia` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Miami` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `San Diego` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Dallas` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `San Francisco` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Austin` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Santa Clara` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Fort Worth` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Columbus` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Charlotte` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Indianapolis` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `San Francisco 2` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Seattle` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Denver` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |
| `Oklahoma` | UMi-like | 说明高度 6 | 待核验 | 未取得 | D |

### v4（196 项）

| 场景 | 部署归类 | 原站 z / AGL（m） | LoS/NLoS | 预览几何宽×深（m） | 证据 |
|---|---|---|---|---|---|
| `asu_campus_3p5` | UMa-like | 22 / 22 | LoS+NLoS（R） | 681.5×525.5 | P+R |
| `city_0_newyork_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 617.3×825.3 | P+R |
| `city_1_losangeles_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 500.3×437.8 | P+R |
| `city_2_chicago_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 332.1×391.0 | P+R |
| `city_3_houston_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 792.8×888.8 | P+R |
| `city_4_phoenix_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 450.0×800.4 | P+R |
| `city_5_philadelphia_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 1135.2×496.2 | P+R |
| `city_6_miami_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 812.0×797.4 | P+R |
| `city_7_sandiego_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 716.1×638.7 | P+R |
| `city_8_dallas_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 1955.9×1496.7 | P+R |
| `city_9_sanfrancisco_3p5` | UMi-like | 6 / 6 | 待核验 | 428.0×434.2 | P |
| `city_10_austin_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 499.7×789.5 | P+R |
| `city_11_santaclara_3p5` | UMi-like | 6 / 6 | 待核验 | 1260.0×1244.3 | P |
| `city_12_fortworth_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 1636.5×768.4 | P+R |
| `city_13_columbus_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 405.0×327.2 | P+R |
| `city_14_charlotte_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 1040.9×636.0 | P+R |
| `city_15_indianapolis_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 1037.2×1235.7 | P+R |
| `city_16_sanfrancisco_3p5` | UMi-like | 6 / 6 | 待核验 | 1549.6×2284.0 | P |
| `city_17_seattle_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 328.4×545.0 | P+R |
| `city_18_denver_3p5` | UMi-like | 6 / 6 | 待核验 | 996.4×819.6 | P |
| `city_19_oklahoma_3p5` | UMi-like | 6 / 6 | LoS+NLoS（R） | 952.1×380.5 | P+R |
| `i1_2p5` | InH-like | 待核验 | 待核验 | 未取得 | D |
| `i2_28b` | InH-like | z=2；AGL 未知 | 遮挡布局；子集待核验 | 未取得 | P |
| `city_0_newyork_28` | UMi-like | 6 / 6 | 待核验 | 617.3×825.3 | P |
| `city_1_losangeles_28` | UMi-like | 6 / 6 | 待核验 | 500.3×437.8 | P |
| `city_2_chicago_28` | UMi-like | 6 / 6 | LoS+NLoS（R） | 332.1×391.0 | P+R |
| `city_3_houston_28` | UMi-like | 6 / 6 | 待核验 | 792.8×888.8 | P |
| `city_4_phoenix_28` | UMi-like | 6 / 6 | 待核验 | 450.0×800.4 | P |
| `city_5_philadelphia_28` | UMi-like | 6 / 6 | 待核验 | 1135.2×496.2 | P |
| `city_7_sandiego_28` | UMi-like | 6 / 6 | 待核验 | 716.1×638.7 | P |
| `city_6_miami_28` | UMi-like | 6 / 6 | 待核验 | 812.0×797.4 | P |
| `city_8_dallas_28` | UMi-like | 6 / 6 | 待核验 | 1955.9×1496.7 | P |
| `city_9_sanfrancisco_28` | UMi-like | 6 / 6 | 待核验 | 428.0×434.2 | P |
| `city_10_austin_28` | UMi-like | 6 / 6 | 待核验 | 499.7×789.5 | P |
| `city_11_santaclara_28` | UMi-like | 6 / 6 | 待核验 | 1260.0×1244.3 | P |
| `city_12_fortworth_28` | UMi-like | 6 / 6 | 待核验 | 1636.5×768.4 | P |
| `city_13_columbus_28` | UMi-like | 6 / 6 | LoS+NLoS（R） | 405.0×327.2 | P+R |
| `city_14_charlotte_28` | UMi-like | 6 / 6 | 待核验 | 1040.9×636.0 | P |
| `city_15_indianapolis_28` | UMi-like | 6 / 6 | 待核验 | 1037.2×1235.7 | P |
| `city_16_sanfrancisco_28` | UMi-like | 6 / 6 | 待核验 | 1549.6×2284.0 | P |
| `city_17_seattle_28` | UMi-like | 6 / 6 | 待核验 | 328.4×545.0 | P |
| `city_18_denver_28` | UMi-like | 6 / 6 | 待核验 | 996.4×819.6 | P |
| `city_19_oklahoma_28` | UMi-like | 6 / 6 | 待核验 | 952.1×380.5 | P |
| `o1_3p5` | UMi-like候选 | 待核验 | 待核验 | 未取得 | D |
| `o1_3p4` | UMi-like候选 | 待核验 | 待核验 | 未取得 | D |
| `o1b_3p5` | UMi-like候选 | 待核验 | 遮挡布局；子集待核验 | 未取得 | D |
| `o1b_28` | UMi-like候选 | 待核验 | 遮挡布局；子集待核验 | 未取得 | D |
| `o1_drone_200` | 空地/RIS | 6 / 6 | 待核验 | 503.3×650.4 | P |
| `o1_140` | UMi-like候选 | 待核验 | 待核验 | 未取得 | D |
| `i1_2p4` | InH-like | 待核验 | 待核验 | 未取得 | D |
| `o1_28` | UMi-like候选 | 待核验 | 待核验 | 未取得 | D |
| `o1_60` | UMi-like候选 | 待核验 | 待核验 | 未取得 | D |
| `boston5g_3p5` | UMi-like | 15 / 15 | 待核验 | 799.3×648.9 | P |
| `boston5g_28` | UMi-like | 15 / 15 | 待核验 | 799.3×648.9 | P |
| `city_21_taito_city_3p5` | UMi-like | 10 / 10 | 待核验 | 683.5×625.5 | P |
| `city_22_rome_3p5` | UMi-like | 10 / 10 | 待核验 | 502.1×538.0 | P |
| `city_23_beijing_3p5` | UMi-like | 10 / 10 | 待核验 | 622.1×566.2 | P |
| `city_24_cairo_3p5` | UMi-like | 10 / 10 | 待核验 | 1133.5×1056.2 | P |
| `city_26_dubai_3p5` | UMi-like | 10 / 10 | 待核验 | 1082.8×1374.6 | P |
| `city_27_rio_de_janeiro_3p5` | UMi-like | 10 / 10 | 待核验 | 2058.3×2375.7 | P |
| `city_28_mumbai_3p5` | UMi-like | 10 / 10 | 待核验 | 585.3×756.9 | P |
| `city_29_centro_3p5` | UMi-like | 10 / 10 | 待核验 | 1350.9×608.7 | P |
| `city_30_singapore_3p5` | UMi-like | 10 / 10 | 待核验 | 672.8×743.7 | P |
| `city_31_barcelona_3p5` | UMi-like | 10 / 10 | 待核验 | 1217.1×1123.5 | P |
| `city_32_sydney_3p5` | UMi-like | 10 / 10 | 待核验 | 380.5×765.4 | P |
| `city_33_hong_kong_3p5` | UMi-like | 10 / 10 | 待核验 | 487.9×565.4 | P |
| `city_34_amsterdam_3p5` | UMi-like | 10 / 10 | 待核验 | 792.1×1476.7 | P |
| `city_35_san_francisco_3p5` | UMi-like | 10 / 10 | 待核验 | 569.6×526.0 | P |
| `city_36_bangkok_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_37_seoul_3p5` | UMi-like | 10 / 10 | 待核验 | 499.7×728.0 | P |
| `city_38_toronto_3p5` | UMi-like | 10 / 10 | 待核验 | 864.4×732.8 | P |
| `city_39_jerusalem_3p5` | UMi-like | 10 / 10 | 待核验 | 514.5×706.7 | P |
| `city_40_prague_3p5` | UMi-like | 10 / 10 | 待核验 | 504.9×559.0 | P |
| `city_41_kyoto_3p5` | UMi-like | 10 / 10 | 待核验 | 6544.5×9218.7 | P |
| `city_42_san_nicolas_3p5` | UMi-like | 10 / 10 | 待核验 | 1397.5×1468.2 | P |
| `city_43_cape_town_3p5` | UMi-like | 10 / 10 | 待核验 | 514.2×520.8 | P |
| `city_44_lisboa_3p5` | UMi-like | 10 / 10 | 待核验 | 524.5×437.0 | P |
| `city_45_stockholm_3p5` | UMi-like | 10 / 10 | 待核验 | 293.7×494.4 | P |
| `city_46_la_habana_3p5` | UMi-like | 10 / 10 | 待核验 | 3471.2×1372.7 | P |
| `city_47_chicago_3p5` | UMi-like | 10 / 10 | 待核验 | 484.6×3226.6 | P |
| `city_48_gurbchen_3p5` | UMi-like | 10 / 10 | 待核验 | 295.2×385.2 | P |
| `city_25_instanbul_3p5` | UMi-like | 10 / 10 | 待核验 | 777.4×948.1 | P |
| `city_49_new_delhi_3p5` | UMi-like | 10 / 10 | 待核验 | 838.4×642.3 | P |
| `city_50_edinburgh_3p5` | UMi-like | 10 / 10 | 待核验 | 508.9×531.7 | P |
| `city_51_firenze_3p5` | UMi-like | 10 / 10 | 待核验 | 436.8×685.3 | P |
| `city_52_marrakesh_3p5` | UMi-like | 10 / 10 | 待核验 | 1528.7×1180.1 | P |
| `city_53_sankt-peterburg_3p5` | UMi-like | 10 / 10 | 待核验 | 470.5×490.7 | P |
| `city_54_north_jakarta_3p5` | UMi-like | 10 / 10 | 待核验 | 503.2×452.2 | P |
| `city_55_madrid_3p5` | UMi-like | 10 / 10 | 待核验 | 604.6×458.2 | P |
| `city_56_montreal_3p5` | UMi-like | 10 / 10 | 待核验 | 520.7×601.0 | P |
| `city_57_taipei_3p5` | UMi-like | 10 / 10 | 待核验 | 687.4×648.9 | P |
| `city_58_sumida_city_3p5` | UMi-like | 10 / 10 | 待核验 | 3012.0×1940.4 | P |
| `city_59_roma_3p5` | UMi-like | 10 / 10 | 待核验 | 484.1×888.2 | P |
| `city_60_toronto_3p5` | UMi-like | 10 / 10 | 待核验 | 864.4×732.8 | P |
| `city_61_hatsukaichi_3p5` | UMi-like | 10 / 10 | 待核验 | 7926.4×8199.6 | P |
| `city_62_santiago_3p5` | UMi-like | 10 / 10 | 待核验 | 776.7×1174.9 | P |
| `city_63_athens_3p5` | UMi-like | 10 / 10 | 待核验 | 751.4×578.6 | P |
| `city_64_new_york_3p5` | UMi-like | 10 / 10 | 待核验 | 564.8×557.2 | P |
| `city_65_granada_3p5` | UMi-like | 10 / 10 | 待核验 | 826.6×687.0 | P |
| `city_66_bruxelles_3p5` | UMi-like | 10 / 10 | 待核验 | 389.2×512.2 | P |
| `city_67_fujiyoshida_3p5` | UMi-like | 10 / 10 | 待核验 | 1397.5×1468.2 | P |
| `city_68_reykjavik_3p5` | UMi-like | 10 / 10 | 待核验 | 383.1×469.2 | P |
| `city_69_warszawa_3p5` | UMi-like | 10 / 10 | 待核验 | 443.4×527.5 | P |
| `city_70_stockholm_3p5` | UMi-like | 10 / 10 | 待核验 | 334.4×445.1 | P |
| `city_71_helsinki_3p5` | UMi-like | 10 / 10 | 待核验 | 1131.4×761.1 | P |
| `city_0_newyork_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 352.2×196.7 | P |
| `city_11_santaclara_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 395.6×175.0 | P |
| `city_1_losangeles_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 280.1×193.6 | P |
| `city_19_oklahoma_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 234.0×275.1 | P |
| `city_18_denver_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 255.6×254.7 | P |
| `city_17_seattle_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 247.6×242.7 | P |
| `city_16_sanfrancisco_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 251.0×239.5 | P |
| `city_9_sanfrancisco_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 252.7×234.2 | P |
| `city_13_columbus_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 287.5×266.5 | P |
| `city_2_chicago_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 284.5×172.0 | P |
| `city_8_dallas_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 242.1×246.0 | P |
| `city_5_philadelphia_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 217.1×348.8 | P |
| `city_7_sandiego_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 247.2×232.3 | P |
| `city_3_houston_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 246.0×190.1 | P |
| `city_14_charlotte_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 254.4×272.2 | P |
| `city_4_phoenix_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 253.0×240.4 | P |
| `city_15_indianapolis_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 250.3×257.7 | P |
| `city_6_miami_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 280.5×237.7 | P |
| `city_10_austin_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 226.3×321.7 | P |
| `city_12_fortworth_3p5_s` | UMa-like | 20 / 19.7 | 待核验 | 233.3×257.2 | P |
| `city_19_oklahoma_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 952.1×380.5 | P |
| `city_0_newyork_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 617.3×825.3 | P |
| `city_1_losangeles_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 500.3×437.8 | P |
| `city_2_chicago_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 332.1×391.0 | P |
| `city_3_houston_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 792.8×888.8 | P |
| `city_4_phoenix_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 450.0×800.4 | P |
| `city_5_philadelphia_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1135.2×496.2 | P |
| `city_6_miami_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 812.0×797.4 | P |
| `city_7_sandiego_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 716.1×638.7 | P |
| `city_8_dallas_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1955.9×1496.7 | P |
| `city_9_sanfrancisco_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 428.0×434.2 | P |
| `city_10_austin_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 499.7×789.5 | P |
| `city_11_santaclara_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1260.0×1244.3 | P |
| `city_12_fortworth_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1636.5×768.4 | P |
| `city_13_columbus_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 405.0×327.2 | P |
| `city_14_charlotte_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1040.9×636.0 | P |
| `city_15_indianapolis_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1037.2×1235.7 | P |
| `city_16_sanfrancisco_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 1549.6×2284.0 | P |
| `city_17_seattle_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 328.4×417.4 | P |
| `city_18_denver_3p5_lwm` | UMi-like | 6 / 6 | 待核验 | 996.4×819.6 | P |
| `i3_60` | InH-like | z=2；AGL 未知 | 待核验 | 未取得 | P |
| `i3_2p4` | InH-like | z=2；AGL 未知 | 待核验 | 未取得 | P |
| `city_01_villas_florida` | 低层住宅/待定 | 待核验 | 待核验 | 未取得 | D |
| `city_0_newyork_new` | UMa-like | 20 / 20 | 待核验 | 349.9×144.3 | P |
| `asu_campus_3p5_10cm` | UMa-like候选 | 待核验 | 待核验 | 未取得 | D |
| `asu_campus_3p5_dyn` | 混合部署 | 待核验 | 待核验 | 未取得 | D |
| `city_01_villas_florida_1gp` | UMi-like | 9.99816 / 9.998 | 待核验 | 1245.2×5518.3 | P |
| `city_01_villas_florida_2gp` | UMi-like | 9.99816 / 9.998 | 待核验 | 896.6×448.1 | P |
| `city_10_florida_villa_2gp` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_19_oklahoma_3p68_gc2` | UMi-like | 10 / 10 | 待核验 | 949.4×271.7 | P |
| `city_10_florida_villa_7gp` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_10_florida_villa_8gp_1758135830233` | UMi-like | 10 / 10 | 待核验 | 1150.7×1917.4 | P |
| `city_83_tempe_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_19_oklahoma_3p68_gc2_1_1758623064948` | UMi-like | 10 / 10 | 待核验 | 949.4×271.7 | P |
| `tempe2_1758180768765` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_11_villa_florida_1gp_1758180246123` | UMi-like | 10 / 10 | 待核验 | 2899.1×2023.1 | P |
| `city_10_florida_villa_7gp_1758096510611` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_10_florida_villa_7gp_1758095156175` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_10_florida_villa_7gp_1758092194311` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_10_florida_villa_7gp_1758026450854` | UMi-like | 10 / 10 | 待核验 | 2761.7×1306.4 | P |
| `city_81_seoul_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_80_philadelphia_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_79_parow_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_78_newtaipei_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_77_melbourne_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_76_houston_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_73_casablanca_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_72_capetown_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_74_chiyoda_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_75_dongcheng_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_82_shibuya_3p5` | 城市几何/部署待定 | 待核验 | 待核验 | 未取得 | D |
| `city_84_baoding_3p5` | UMi-like | 10 / 10 | 待核验 | 325.9×594.1 | P |
| `city_86_ankara_3p5` | UMi-like | 10 / 10 | 待核验 | 459.1×437.8 | P |
| `city_85_fuyang_3p5` | UMi-like | 10 / 10 | 待核验 | 572.1×399.5 | P |
| `city_87_jinan_3p5` | UMi-like | 10 / 10 | 待核验 | 328.0×401.4 | P |
| `city_88_tongshan_3p5` | UMi-like | 10 / 10 | 待核验 | 335.6×415.6 | P |
| `city_89_nairobi_3p5` | UMi-like | 10 / 10 | 待核验 | 444.8×421.5 | P |
| `city_91_xiangyang_3p5` | UMi-like | 10 / 10 | 待核验 | 396.7×395.5 | P |
| `city_92_sãopaulo_3p5` | UMi-like | 10 / 10 | 待核验 | 370.8×408.8 | P |
| `city_90_nanjing_3p5` | UMi-like | 10 / 10 | 待核验 | 478.9×509.5 | P |
| `city_93_rangoon_3p5` | UMi-like | 10 / 10 | 待核验 | 437.6×387.6 | P |
| `city_94_monterrey_3p5` | UMi-like | 10 / 10 | 待核验 | 364.4×402.0 | P |
| `city_95_delhi_3p5` | UMi-like | 10 / 10 | 待核验 | 413.1×398.0 | P |
| `city_94_zhanjiang_3p5` | UMi-like | 10 / 10 | 待核验 | 405.8×390.8 | P |
| `city_96_osaka_3p5` | UMi-like | 10 / 10 | 待核验 | 372.1×429.3 | P |
| `city_102_huanggang_3p5` | UMi-like | 10 / 10 | 待核验 | 371.8×387.1 | P |
| `city_97_chennai_3p5` | UMi-like | 10 / 10 | 待核验 | 503.6×829.2 | P |
| `city_98_guangzhou_3p5` | UMi-like | 10 / 10 | 待核验 | 400.4×482.4 | P |
| `city_99_shanghai_3p5` | UMi-like | 10 / 10 | LoS+NLoS（R） | 383.8×439.8 | P+R |
| `city_100_bogotá_3p5` | UMi-like | 10 / 10 | 待核验 | 392.3×424.8 | P |
| `city_101_jakarta_3p5` | UMi-like | 10 / 10 | 待核验 | 393.2×390.7 | P |

## 6. 重复、缺失与使用限制

- `i1_2p5`：2 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。
- `i2_28b`：2 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。
- `city_40_prague_3p5`：2 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。
- `city_48_gurbchen_3p5`：2 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。
- `city_50_edinburgh_3p5`：2 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。
- 未取得预览的 26 个 v4 条目：`i1_2p5`、`o1_3p5`、`o1_3p4`、`o1b_3p5`、`o1b_28`、`o1_140`、`i1_2p4`、`o1_28`、`o1_60`、`city_36_bangkok_3p5`、`city_01_villas_florida`、`asu_campus_3p5_10cm`、`asu_campus_3p5_dyn`、`city_83_tempe_3p5`、`tempe2_1758180768765`、`city_81_seoul_3p5`、`city_80_philadelphia_3p5`、`city_79_parow_3p5`、`city_78_newtaipei_3p5`、`city_77_melbourne_3p5`、`city_76_houston_3p5`、`city_73_casablanca_3p5`、`city_72_capetown_3p5`、`city_74_chiyoda_3p5`、`city_75_dongcheng_3p5`、`city_82_shibuya_3p5`。
- 目录中的 `hasRtSource`、预览几何、已下载的路径数组是不同证据层级；本次未逐包确认完整可重放的射线追踪工程。
- 原始材料为第三方数据。目录、下载记录、版本、原始命名与文件哈希均保留；项目脚本不是 DeepMIMO 或射线追踪器的原创替代。
- 对几何拼接，应按建筑/道路形态选素材，再统一部署宏站、微站和室内站点。不要因原数据被归 UMi-like 就排除其作为未来 UMa 几何素材。

## 7. 来源与复核入口

- [DeepMIMO 官方场景目录](https://www.deepmimo.net/scenarios)；[本次使用的官方目录 API](https://www.deepmimo.net/api/scenarios)。
- [DeepMIMO 官方数据格式：交互码与文件组织](https://deepmimo.github.io/DeepMIMO/resources/specs.html)。
- [3GPP TR 38.901 V19.1.0 / ETSI TR 138 901：场景与信道条件](https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/19.01.00_60/tr_138901v190100p.pdf)。本表没有运行标准模型校准。
- [源目录快照](../../../output/deepmimo-scenes/classification/catalog.json)、[逐项结构化证据](../../../output/deepmimo-scenes/classification/classification.json)、[原始路径统计](../../../output/deepmimo-scenes/classification/path-states.json)。
- [此前动态 ASU 抽查记录](DeepMIMO场景选型.md#动态-asu-的实际核验)。

复核命令（不会启动新的射线追踪）：

```bash
python3 tools/scene-studio/scripts/audit_deepmimo_scenarios.py --report-only
uv run --with numpy --with scipy python tools/scene-studio/scripts/audit_deepmimo_path_states.py --cache-only
```

联网重取预览使用第一个脚本的 `--fetch-previews`；原始路径脚本建议用 `--names` 显式限定条目。请求受官网可用性和限流影响，不保证所有条目可下载。
