# QuaDRiGa：CSI 压缩反馈的轨迹数据生成指南

> 日期：2026-10-25。状态：官方 2.8.1 系列源码/教程核验后的示例；尚未在 MATLAB/Octave 运行。固定官方 commit `277866650eb115adb5b3e8ac252b0d1df073596d`，对应仓库所附 2.8.1-0 文档。

## 1. 先从什么场景开始

建议先选 `3GPP_38.901_UMi_LOS` / `3GPP_38.901_UMi_NLOS`，固定 $3.5\,\mathrm{GHz}$、单站、单 UE 和 $32$ 阵元。先分别生成稳定场景，再增加同一条轨迹上的场景过渡。室内扩展使用仓库已有的 `3GPP_38.901_Indoor_LOS` / `Indoor_NLOS` 配置。

QuaDRiGa 可运行于 MATLAB 或 Octave；首版只需 CPU，不以 CUDA 为前置条件。源码采用专门的非商业用途许可，研究使用和再发布分别记录其条件；见[官方 LICENSE](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/QuaDRiGa_License.txt)。

## 2. 最小连续轨迹示例

下面新建的是单链路静态 BS + 移动 UE，不是城市地图的确定性射线追踪复刻。生成器本身先输出多径系数与时延，然后 `fr()` 才得到频域 CSI。

```matlab
% Start from the official QuaDRiGa checkout directory.
addpath(genpath('quadriga_src'));
rng(20261025, 'twister');
fc = 3.5e9;
B = 20e6;
Nf = 256;
Nt = 32;
v_mps = 10;

l = qd_layout;
l.simpar.center_frequency = fc;
l.simpar.use_absolute_delays = 1;
l.simpar.show_progress_bars = 0;
l.tx_position = [0; 0; 10];
l.tx_array = qd_arrayant('3gpp-3d', 1, Nt, fc, 1, 0, 0.5);
l.rx_array = qd_arrayant('omni');
l.rx_track = qd_track('linear', 50, pi/2);
l.rx_track.initial_position = [20; 30; 1.5];
l.rx_track.interpolate_positions(100); % 100 positions per meter
l.rx_track.scenario = '3GPP_38.901_UMi_NLOS';
c = l.get_channels;
c = c(1,1,1);

% Scalar Nf uses the generator's non-centered frequency convention.
Hq = c.fr(B, Nf);
% qd_channel.fr axes: RX, TX, frequency, snapshot.
H_true = single(permute(Hq, [4,1,2,3]));
assert(size(H_true,2) == 1 && size(H_true,3) == Nt);
assert(size(H_true,4) == Nf);
rx_positions = l.rx_track.positions + l.rx_track.initial_position;
delta = diff(rx_positions, 1, 2);
distance_m = [0, cumsum(sqrt(sum(delta.^2, 1)))];
t_seconds = distance_m / v_mps;
assert(size(H_true,1) == numel(t_seconds));
frequency_offset_hz = (0:Nf-1) * (B/Nf);
save('quadriga_raw.mat', 'H_true', 'rx_positions', 't_seconds', ...
    'frequency_offset_hz', 'fc', 'B', 'Nt', 'Nf', '-v7.3');
```

阵列模型在这里使用 3GPP 元件方向图，与 DeepMIMO 示例的 isotropic 元件不同；该差异必须记录，跨工具校准时需统一方向图/阵列坐标，或明确把它作为域差异，不把两个示例当成参数完全相同的复现。

API 依据：[空间一致性教程](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/tutorials/t13_spatial_consistency.m)、[阵列构造](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_arrayant/generate.m)、[布局生成](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_layout/get_channels.m)、[频响输出](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_channel/fr.m)。

## 3. 时间、采样和频率不能猜

`interpolate_positions(100)` 的参数是每米采样点数；示例约每 $0.01\,\mathrm m$ 一点。配合 $v=10\,\mathrm{m/s}$，对应约 $1\,\mathrm{ms}$ 一帧。实际时间由导出的轨迹距离计算，不能把快照编号直接当毫秒。

若改变速度，应重新检查空间采样和输出时间间隔；需要固定时间网格或双端移动时，使用官方 `set_speed`、track/channel 插值或 layout 的时间采样接口，并核对更新后的时间戳。先生成足够密的底层信道，再按反馈周期取样。

`fr(B, Nf)` 不是默认以载频为中心的对称频带：该版本源码用从零开始的相对频率网格。若需要中心对称网格，应显式传入 carrier positions，并同步调整 FFT 顺序；不能在下游随意 `fftshift` 后仍使用旧预处理契约。

MATLAB `-v7.3` 文件是 HDF5；Python 读取时检查复数表示及维度顺序，不直接套用对普通 MAT 文件的读取假设。推荐同时保存一个已知索引的复数元素和数组 shape，跨语言核对。

## 4. 如何制造模型需要更新的情况

| 变化 | 建议构造方式 | 需要避免的混淆 |
|---|---|---|
| 地理移动 | 在同一 layout 内沿连续轨迹前进 | 每帧重建独立 layout 会破坏连续性 |
| LOS/NLOS 转换 | 按 track 的 `segment_index` 和 `scenario` 配置分段 | 单纯拼接两条独立随机序列只能算突变压力夹具 |
| 统计场景变化 | 分别控制 DS、角扩展、K-factor 等候选参数 | 修改参数后重新检查合理性，不能把任意值称为 3GPP 默认 |
| 速度变化 | 保持运动/时间映射与信道演化一致 | 只修改速度标签不改变相位或采样时间 |
| CSI 过期 | 保存 $t_{\mathrm{obs}}$ 与 $t_{\mathrm{apply}}$，按真实时间取目标信道 | 评价仍用旧时刻 CSI 会掩盖反馈时延损失 |

场景分段、簇生灭与合并可参考[时间演化教程](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/tutorials/t08_time_evolution.m)。该教程中的具体配置和参数只是示范，不直接作为本项目全部设置。

先保留默认场景参数做基准，再引入单因素变化；每个域用多条轨迹和多个独立 realization，按组划分。空间一致性实验还应对共享散射 realization 的轨迹统一归组。

## 5. 数据验收与边界

必须检查路径功率、时延范围、频率选择性、相邻快照相关性、位置/时间单调性和场景边界；若模型更新前后真实信道被人为重置，无法归因管理策略收益。

训练/适配用的数据和指标只来自当时已可获得的测量。仿真器可保存完整真值给评价器，但在线 Agent 不能免费读取真实重建 NMSE。压缩质量证据可通过有成本的全量反馈/补测获得，成本另行记录。

[总体方案](../../分析文档/实验工具链/CSI压缩反馈数据生成方案.md) · [统一预处理](CSI预处理与验收.md) · [来源记录](../../相关工作/CSI数据生成资料.md)
