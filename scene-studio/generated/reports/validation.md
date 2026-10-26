# 四场景工作台整合验证

日期：2026-10-26。

## 已执行

- 13个原Python实现迁入统一包；旧入口改为轻量兼容脚本。
- 原工具目录、城市数据目录及四建筑验证目录实体迁入scene-studio，旧位置为兼容符号链接。
- 四种场景使用现有快照，不重新布置建筑，不重新计算信道。
- 21个城市场景/清单/二维图及原测试结果文件SHA256保持不变，见[迁移校验基线](migration-snapshots.json)。
- TypeScript检查及Vite生产构建通过，三个入口：四场景首页、原四建筑编辑器、原DeepMIMO选型页。
- Python unittest 7项全部通过、无跳过；覆盖独立工作目录、包/文件/旧脚本入口、导入无副作用、数据校验与快照一致性。
- 三座城市导出舍入几何复检通过，建筑实例数665、2306、13838。建筑重叠、城市越界、地块越界、道路车行面侵入、公园侵入均为0。范围仅二维，面积阈值0.01 m²、边界容差0.002 m。
- Chrome/Playwright实际加载四种场景并检查透视/正交俯视、鼠标旋转缩放平移、点选建筑高度与来源、选择聚焦、四建筑位置步进及真实波束摘要。
- 三个城市未展示核验轨迹、设备或信道结果。
- PNG截图下载实际落盘；原编辑器和DeepMIMO辅助页能打开三维画布；390px小屏页面加载正常（场景卡片和图层在画布上方，需滚动）。
- 初次浏览器验收未出现pageerror或console.error。详细复验结果见[浏览器验收JSON](../browser/acceptance.json)。

## 执行命令

```sh
python3 scene-studio/run.py build
uv run --with numpy --with scipy --with pillow --with shapely python scene-studio/run.py test
uv run --with numpy --with scipy --with pillow --with shapely python scene-studio/run.py validate
python3 scene-studio/run.py serve --port 8767
uv run --with playwright python scene-studio/tests/browser_check.py --url http://127.0.0.1:8767
```

## 构建提示与边界

Vite报告共享Three.js/OrbitControls构建块超过500kB（压缩约144kB）；属于体积提示，生产构建成功，不是运行错误。未做跨浏览器/全平台性能基准，不承诺特定帧率。浏览器面片三角化、显示层高度偏移和渲染材质不构成RT网格或电磁材料验证。

本次未运行城市RT、未生成新CSI、未联网下载DeepMIMO完整包、未改变现有城市实例位置；四建筑RT证据仍为原有小规模核验。
