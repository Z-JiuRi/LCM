# DeepMIMO：CSI 压缩反馈数据生成指南

> 日期：2026-10-25。API 已对照官方 v4.0.5 源码核读；本页代码是按项目需求编写的候选示例，未在真实场景上运行。采用 Python 3.11+，不混用 v3 的字典结构和 v4 接口。

## 1. 版本与数据入口

本次核验的最新 GitHub release 为 [v4.0.5](https://github.com/DeepMIMO/DeepMIMO/releases/tag/v4.0.5)，对应 commit `48945c29b47c537bf2ea82a929c33bd6ff7aac31`。Python 要求来自该版本的[打包配置](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/pyproject.toml)。

建议在独立 Python 环境安装 `deepmimo==4.0.5`，固定依赖锁。已有场景可以直接下载并计算信道；创建新地图、改变散射体或运行动态射线追踪是另一条更重的工作流，首批数据不需要安装 Sionna RT、Blender 或购买 Wireless InSite。

代码 LICENSE 为 Apache-2.0，但同一 tag 的 `pyproject.toml` 和 PyPI 元数据仍标 GPL-2.0-or-later，存在不一致；记录实际分发版本和 LICENSE，不自行改写其许可结论。场景资产另查各自条款。证据见[资料记录](../../相关工作/CSI数据生成资料.md)。

## 2. 生成小批量频域 CSI

下面使用官方 quickstart 的 `asu_campus_3p5`。其示例为 TX set 1、RX set 0；下载后先用 `dm.info()` 核对。其他场景的 set ID 不应照抄。输出只用于格式检查，不能把前 $2{,}000$ 个点随机拆为最终实验的训练与测试。

```python
from pathlib import Path
from importlib.metadata import version
import json
import numpy as np
import deepmimo as dm

scenario = "asu_campus_3p5"
assert version("deepmimo") == "4.0.5"
dm.download(scenario)
dm.info(scenario)
# Select one BS-to-UE-grid link; IDs are scenario-specific.
ds = dm.load(scenario, tx_sets={1: [0]}, rx_sets={0: "all"}, max_paths=25)
if not isinstance(ds, dm.Dataset):
    raise TypeError("Select a single TX/RX dataset before generating channels")
source_ids = np.arange(min(2000, ds.n_ue))
ds = ds.trim(idxs=source_ids)

cp = dm.ChannelParameters()
cp.bs_antenna.shape = [32, 1]
cp.bs_antenna.spacing = 0.5
cp.bs_antenna.radiation_pattern = "isotropic"
cp.ue_antenna.shape = [1, 1]
cp.ue_antenna.radiation_pattern = "isotropic"
cp.freq_domain = True
cp.doppler = False
cp.num_paths = 25
cp.ofdm.bandwidth = 20e6
cp.ofdm.subcarriers = 256
cp.ofdm.selected_subcarriers = np.arange(256)
cp.ofdm.rx_filter = False
H = np.asarray(ds.compute_channels(cp), dtype=np.complex64)
assert H.shape == (len(source_ids), 1, 32, 256)
finite = np.isfinite(H).all(axis=(1, 2, 3))
nonzero = np.sum(np.abs(H) ** 2, axis=(1, 2, 3)) > 0
valid = finite & nonzero
if not np.any(valid):
    raise ValueError("No usable channels; inspect the selected scenario and link")

out = Path("data/csi/pilot_deepmimo")
out.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    out / "raw.npz", H_true=H[valid], user_id=source_ids[valid],
    rx_pos=np.asarray(ds.rx_pos)[valid], tx_pos=np.asarray(ds.tx_pos),
    valid_original=valid,
    frequency_offset_hz=np.arange(256) * (20e6 / 256),
)
metadata = {
    "generator": "DeepMIMO", "version": version("deepmimo"),
    "scenario": scenario, "tx_set": 1, "tx_idx": 0, "rx_set": 0,
    "axes": ["sample", "rx_ant", "tx_ant", "subcarrier"],
    "carrier_frequency_hz": 3.5e9, "bandwidth_hz": 20e6,
    "subcarrier_count": 256, "loaded_max_paths": 25,
    "channel_parameters": cp, "purpose": "format_smoke_only",
}
(out / "manifest.json").write_text(
    json.dumps(metadata, default=lambda x: x.tolist(), indent=2), encoding="utf-8"
)
```

示例不代替实验 manifest：扩展时还需加入原场景文件哈希、实际载频核对、阵元位置、相位/延迟参考、完整路径元数据、split ID 和数据条款记录。非零筛选数量也要报告；无路径/断链位置不能在生命周期评价中静默删除。

API 对照：[ChannelParameters](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/generator/channel.py)、[Dataset.compute_channels 与 trim](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/datasets/dataset.py)、[load 的 TX/RX 选择](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/datasets/load.py)。

## 3. 三个容易生成错的地方

**默认只生成一个频点。** v4.0.5 的 `selected_subcarriers` 默认是 `[0]`，必须显式选择完整网格。`freq_domain=False` 输出最后一维是路径，不是均匀时延采样的 CIR tap；不能直接对路径编号做 IFFT。

**场景与载频绑定。** `asu_campus_3p5` 的原始传播路径来自指定频率的射线追踪。改变阵列或 OFDM 网格不意味着可任意重用到另一个载频；新频段的材料和路径效应需要对应场景/重新追踪。

**留意时延窗口和尺度。** 该版本信道生成源码会处理超出 OFDM 窗口的路径；检查原始 delay 与 $N_f/B$ 的关系并记录被排除路径，不能让工具的处理悄悄改变研究问题。其频域路径幅度带有 OFDM 归一化；与 QuaDRiGa 比较原始功率前先做单路径校准。

## 4. 从静态点集扩成生命周期数据

按地图中的完整空间块选择训练/开发/适配/测试区域，保留块间隔；检查相邻样本相关性。固定同一 BS 先做跨区域，再把跨 BS/跨场景作为更强分布变化，避免一次改变所有因素。

[官方 Doppler 教程](https://www.deepmimo.net/docs/tutorials/5_doppler_mobility.html)可按速度或多径 Doppler 建立显式时间轴。固定几何下的相位演化不等于物体遮挡、反射面变化或路径生灭；后者参考[逐快照动态射线追踪](https://www.deepmimo.net/docs/applications/5_dynamic_rt.html)。

v4.0.5 的 `compute_channels(params, times=...)` 支持多个时间采样，额外时间轴位于末尾；适配到项目格式时显式移轴，不使用无条件 `squeeze()`。动态场景还需核对每帧 UE 身份、时间戳与路径连续性。

## 5. 数据量与内存

$10^5$ 个单 UE、$32\times256$ 信道的 complex64 数组约占 $6.55\,\mathrm{GB}$；若同时保存真值/估计值、FFT 临时数组和多个版本，内存与磁盘需求会进一步增加。不要第一次就计算整个地图的完整频域矩阵。

先小批生成并检查，再按空间块或轨迹分 shard，原始 CSI 使用 HDF5/Zarr 等支持分块的格式；小型 `npz` 只作 pilot。压缩后的 `[2,32,32]` float32 输入每 $10^5$ 个约 $0.82\,\mathrm{GB}$，但它不能替代完整 CSI 留档。

[总体数据方案](../../分析文档/实验工具链/CSI压缩反馈数据生成方案.md) · [预处理与验收](CSI预处理与验收.md)
