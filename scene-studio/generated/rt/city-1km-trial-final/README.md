# 一公里城市场景稀疏RT/CSI试算

日期：2026-10-26。已实际执行 Sionna RT 2.2.0 / Mitsuba 3.9.1，Apple Metal 后端。不是下载原城市信道，也不是随机生成示例数值；在保存的整个1×1 km几何上重新求解路径。

## 输入与配置

- 原城市435个源资产、665个建筑实例均参与。源文件及SHA256见[几何记录](geometry.json)，原城市快照未修改。
- 建筑面经投影约束Delaunay三角化并映射回原三维顶点，保持源墙/屋顶winding；删除与平地共面的底面避免重复，得到9080个建筑三角。墙/屋顶没有非地面裂边，但底面开放，不称为水密实体。OBJ导出共享精确舍入顶点索引。
- 一个有限范围0–1000m平地，2三角；建筑和地面均假设ITU concrete，厚0.2m。没有源材料、植被、室内、道路/公园电磁细分，图面树点未加入。
- 人工部署1个TX，坐标约[467.1781,777.6820,25] m；32个真实合成道路中心线上的RX，高1.5m，并检查不在建筑内。
- 载频3.5 GHz、20 MHz带宽、64频点、TX为1×8阵列（半波长间距）、RX单天线；iso方向图、V极化，默认朝向[0,0,0]。
- synthetic_array=True：以阵列中心求路径并附加阵元相位，非每阵元独立追踪。
- LOS + 最多两次镜面反射，关闭绕射、透射/折射和漫反射。deterministic=True，seed=42，路径cap=200000。

## 实际结果

| 每源射线样本预算 | 找到的有效路径 | 非零CSI接收点 | 相邻预算全局CSI相对L2变化 |
|---:|---:|---:|---:|
| 20,000 | 49 | 14 / 32 | — |
| 100,000 | 58 | 15 / 32 | 4.40% |
| 1,000,000 | 60 | 16 / 32 | 1.42% |

最终10个RX有LOS，6个NLOS RX通过反射找到信道，16个RX未找到路径。零信道如实保留。提高预算后仍新增弱路径，因此全局1.42%变化不是收敛证明；逐RX变化在[结果记录](results.json)内，强LOS会掩盖弱NLOS变化。

最终本机运行总耗时约2.13秒（包含导出、导入和三预算求解；已有JIT缓存，不能解释为任意机器首运行耗时或全城密集计算基准）。

CSI为complex64，shape `[32,1,1,8,1,64]`，轴为 `[rx_position,rx_ant,tx,tx_ant,time_step,frequency]`。CIR shape `[32,1,1,8,12,1]`；12是路径槽最大数，不是每个RX都有12条路径。有效路径mask shape `[32,1,12]`，共60条。无效路径tau=-1、系数为0，必须结合mask读取。

独立CIR加频偏相位重建CSI相对误差约5.76×10⁻⁷。输出finite验证通过；新增测试与原测试合计9项全部通过。

## 文件

- [最终信道NPZ](samples.npz)，110660字节（约108 KiB）：CSI、CIR系数、时延、到达/离开角、交互类型、有效路径mask、LOS-only参照、波束增益和坐标。
- [逐点CSV](rx-summary.csv)：32个RX的距离、路径数、信道增益与最佳波束。
- [采样位置图](channel-sample-map.png)：散点，不是插值覆盖图。颜色为阵元/频点平均|H|²的dB，不是dBm。
- [完整配置与结果](results.json)、[几何与坐标记录](geometry.json)。
- [建筑OBJ](buildings.obj)、[地面OBJ](ground.obj)：本次RT输入，显示与电磁假设见上文。
- [20k预算NPZ](samples-20000.npz)、[100k预算NPZ](samples-100000.npz)、[1M预算NPZ](samples-1000000.npz)：方便比较采样敏感性。

`frequency_offsets_hz`是基带频偏，范围−10MHz到9.6875MHz、间隔312500Hz；绝对频率=carrier_frequency_hz+frequency_offsets_hz。`channel_valid`为非零信道mask，零信道的`best_beams=-1`，避免把argmax平局的0当作有效标签。

## 复现与读取

从仓库根运行；默认输出v2目录，可显式选择其他输出，避免覆盖本报告：

```sh
conda activate lcm
python scene-studio/run.py trial-city --output scene-studio/generated/rt/my-city-trial --budgets 20000 100000 1000000
```

```python
import numpy as np
p = 'scene-studio/generated/rt/city-1km-trial-final/samples.npz'
with np.load(p, allow_pickle=False) as d:
    H = d['csi'][:, 0, 0, :, 0, :]  # 32 RX × 8 TX antennas × 64 frequency bins
    valid = d['channel_valid']
    H_valid = H[valid]
```

## 适用边界

这次只证明：已有城市几何可以导入当前RT后端，配置少量TX/RX并产生可读路径与复数CSI。16个零信道表示当前≤2反射模型与采样预算未找到路径，不证明物理环境绝对无信号。尚未做多种子收敛、路径深度敏感性、绕射、材料真实性、测量匹配、密集多基站覆盖或移动相位连续性验证；没有转换为DeepMIMO标准格式。

先前trial/v2目录为调试中间产物；应以本final目录为推荐数据，避免使用旧频偏键或零信道beam0平局标签。网页工作台当前仍为几何浏览，未自动载入本轮无线结果。
