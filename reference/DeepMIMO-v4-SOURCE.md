# DeepMIMO v4 官方源码来源

下载/核对日期：2026-10-26。

- 官方仓库：https://github.com/DeepMIMO/DeepMIMO.git
- 本地工作树：[DeepMIMO-v4](<DeepMIMO-v4/>)，浅克隆，检出发布标签 `v4.0.5`。
- 标签对应提交：`48945c29b47c537bf2ea82a929c33bd6ff7aac31`，提交时间2026-08-25。
- 同时抓取当前 `origin/main`：`45238f9a4c4311b8747dad2eefdebc8c74b1a104`，提交时间2026-10-13；没有切换或修改v4.0.5工作树。
- [main与发布版路径转换差异](<DeepMIMO-v4-main-converter.diff>)保存供审查：main修正了“先取前25条再排序”的问题。
- [审查说明](<DeepMIMO-v4-CSI-REVIEW.md>)。
- 用户已有的[生成脚本目录](<deepmimo/>)和[WAIRD参考目录](<WAIRD/>)未覆盖。

## 许可与依赖注意

保留上游原始[LICENSE](<DeepMIMO-v4/LICENSE>)和[pyproject.toml](<DeepMIMO-v4/pyproject.toml>)。该提交的LICENSE正文为Apache-2.0，但pyproject.toml的license字段写GPL-2.0-or-later；这是上游声明冲突，不能自行替上游裁定。使用/分发前需要确认。

v4.0.5声明Python>=3.11、NumPy<2.3；Sionna额外依赖固定Mitsuba3.8.0、Dr.Jit1.3.1。目前本地lcm环境使用的NumPy/Mitsuba/Dr.Jit版本不同，因此本轮仅下载和静态阅读，没有安装该仓库到现有环境，避免改动依赖。
