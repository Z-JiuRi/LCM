# 地图合并与 CSI 生成最小核验

日期：2026-10-25。

状态：官方源码核验及本地小规模功能测试通过。这里保存独立验证脚本与真实输出，不属于 LCMAgent 运行时，也不代表城市规模数据管线已完成。

## 本地实际验证

使用 Python 3.11、Sionna RT 2.2.0、Mitsuba 3.9.1、macOS Apple Silicon Metal 后端。

1. 分别建立两个 $40\times50\,\mathrm{m}$ 的场景，每个含地面和两栋长方体建筑。
2. 从第二个场景移除三个几何对象及其材料，平移 $40\,\mathrm{m}$ 后加入第一个场景，得到 $80\times50\,\mathrm{m}$ 的统一场景。接缝位于 $x=0$，地面没有面积重叠。
3. 以 $3.5\,\mathrm{GHz}$、8 阵元发射阵列、单天线 UE、32 个频点生成接缝两侧 8 个静态位置的复数 CSI；所有位置输出有限且非零。
4. 将同一 UE 从 $x=-1\,\mathrm{m}$ 移至 $x=1\,\mathrm{m}$，在 9 个位置分别重算路径并得到复数 CSI。
5. 用归一化的 8 波束 DFT 码本计算每个轨迹位置的宽带平均波束增益和最佳波束索引。
6. 回到轨迹中间同一位置，确定性求解器重算结果的最大绝对差为 0。
7. 添加可移动遮挡物。只启用直达路径的专项检查中，移动遮挡物到传播路径后，信道能量从 `5.81539461563807e-06` 降为 0。该数值是数组平方模之和，不是以瓦特标定的接收功率。

`results.json` 为原始运行摘要；`samples.npz` 保存静态位置、静态 CSI、轨迹位置、轨迹 CSI、波束增益及索引。CSI 轴为 `[rx_position, rx_ant, tx, tx_ant, time_step, frequency]`；轨迹结果沿位置轴拼接，每个位置只有一个时间快照。

## 适用边界

- 未导入 Boston5G 原始几何，未运行多张城市地图的显存、内存与耗时基准。
- 此测试采用 0.25 m 的轨迹位置间隔，验证路径重算和数据生成接口，没有验证高时间分辨率的相位连续性、速度和 Doppler 拼接。
- 几何拼接不等于对原有 CSI 进行拼接。运行使用合并后的完整几何重新求解路径。
- 仅测试直达和最多两次镜面反射；未验证绕射、透射、漫反射及实测一致性，也未进行采样预算收敛检查。
- 未验证 DeepMIMO 导出、协议级波束管理、CSI 压缩模型、模型更新或 AutoML。
- 同位置结果一致仅验证本次确定性重算，不等于所有移动信道的连续性已经证明。

## 复现

在仓库根目录运行（当前脚本固定使用本次验证的 Metal 后端）：

```bash
uv run --python 3.11 --with 'sionna-rt==2.2.0' python output/verification/map-stitching/verify.py
```

脚本会在所在目录生成合成 OBJ 文件，并更新 `results.json` 和 `samples.npz`。依赖由 uv 隔离管理；没有增加项目级依赖文件。此次在临时目录运行后，将原样脚本和实际输出保存到这里。

## 官方证据与来源

以下是源码/文档证据，与上述本地执行结果分别记录：

- [Sionna RT 2.2.0 发布说明](https://github.com/NVlabs/sionna-rt/releases/tag/v2.2.0)，发布于 2026-09-29：明确支持对象移除后重新加入或用于另一个场景，支持列表形式添加/移除几何对象。
- [固定版本 Scene 源码](https://github.com/NVlabs/sionna-rt/blob/v2.2.0/src/sionna/rt/scene.py)：`Scene.add`、`Scene.remove`、`Scene.edit` 负责对象管理与 Mitsuba 场景重建。
- [固定版本 SceneObject 源码](https://github.com/NVlabs/sionna-rt/blob/v2.2.0/src/sionna/rt/scene_object.py)：支持 OBJ/PLY 网格加载、位置与朝向变换、克隆。
- [官方移动性教程](https://nvlabs.github.io/sionna/rt/tutorials/Mobility.html)：区分沿位置重算路径与短距离 Doppler 演化；短距离适用性仍需按场景验证。

Sionna RT、Mitsuba、Dr.Jit 是外部项目，本次仅调用它们的公开 API；软件成果及许可归各自项目。验证脚本为本次编写的最小检查，没有复制第三方库实现。
