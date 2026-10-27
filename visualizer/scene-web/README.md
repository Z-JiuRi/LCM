# 三城可视化

只读显示 1 / 2 / 4 km 城市的建筑、地表、植被、BS/扇区和 UE 候选点。支持旋转、缩放、俯视、图层开关、对象属性和 PNG 导出。不下载、不规划、不编辑场景、不计算信道。

## 启动（仓库根目录）

```sh
conda activate lcm
python scripts/visualizer/run.py
```

打开 http://127.0.0.1:8767/ 。首次缺少构建时自动构建；修改前端后运行：

```sh
python scripts/visualizer/run.py build
```

Python 统一使用 Conda `lcm`（NumPy 用于读取 UE 数组）；前端构建使用 Node.js/npm。没有独立 Python 包或 `.venv`。

## 结构

- [src](<src/>)：页面、城市渲染、类型与样式。
- [index.html](<index.html>)：唯一页面入口。
- [package.json](<package.json>)、[tsconfig.json](<tsconfig.json>)、[vite.config.ts](<vite.config.ts>)：前端依赖、类型检查与构建配置。
- `node_modules/`：npm 安装的构建依赖；`dist/`：可重新生成的网页构建。两者不作为源码维护。
- [启动/构建入口](<../../scripts/visualizer/run.py>) 位于仓库脚本目录。
- [data/cities](<../../data/cities/>)：唯一当前场景数据，服务直接读取，不复制到前端构建中。

三城建筑数为 665 / 2,306 / 13,838；BS 为 6 / 23 / 72；UE 为 29,726 / 114,688 / 449,988。UE 网格间距 5 m、高度 1.5 m、建筑净距 2 m、植被净距 1 m，不是实际订户或同时在线用户。BS 为合成规划，扇区箭头不是覆盖范围；这里没有已验证的城市信道。

建筑和源材料来自 [DeepMIMO](https://www.deepmimo.net)，资产内保留来源标记，原始条款仍适用；合成布局不代表真实城市复原。渲染使用 Three.js（MIT），构建时从 npm 安装的 Three.js 包复制许可证到构建目录，不依赖额外的根目录许可证副本。无原始资产所有权或无限制再分发授权声明。
