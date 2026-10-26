# CSI 数据：统一预处理与验收

> 日期：2026-10-25。以下是项目候选预处理约定，适用于自己训练的压缩模型；不宣称兼容既有 CsiNet 预训练权重。FFT 数学行为可用合成数组检查，完整无线数据还需生成器实验。

## 1. 原始信道与目标分开

统一原始数据轴为 `[snapshot, rx_ant, tx_ant, subcarrier]`。本例只支持单天线 UE；多天线 UE 应另定契约，不能随意将 RX 轴并入 batch。

完美 CSI pilot 中，encoder 输入与重建目标均来自同一频域 CSI。加入估计噪声后，可选“压缩估计 CSI”或“同时去噪并恢复真值”，二者是不同学习任务，必须声明。若以真值监督适配，需要说明真实部署中高质量标签从何而来以及获取成本。

公式中 $\mathbf F$ 是单位化前向 DFT。本项目采用：

$$
\mathbf H_{\mathrm{ad}}=\mathbf F_{N_t}\mathbf H_f\mathbf F_{N_f}^{H},\qquad
\mathbf H_f=\mathbf F_{N_t}^{H}\mathbf H_{\mathrm{ad}}\mathbf F_{N_f}.
$$

单位化变换保持能量，可用于检查错误轴、缩放和逆变换。对于 UPA，空间变换应按两个阵列维度分别定义，不能将任意展平次序当成 ULA。

## 2. 可复用的 NumPy 示例

下面三个函数只完成变换、裁剪和逆变换，不包含模型、归一化拟合或仿真器。输入必须是完整且等间隔、有明确频率顺序的网格。

```python
import numpy as np

def to_angle_delay(H_true, keep_taps):
    H_true = np.asarray(H_true)
    if H_true.ndim != 4 or H_true.shape[1] != 1:
        raise ValueError("Expected [snapshot, 1, tx_ant, subcarrier]")
    if not np.isfinite(H_true).all():
        raise ValueError("Non-finite channel values")
    Hf = H_true[:, 0, :, :]
    if not 1 <= keep_taps <= Hf.shape[-1]:
        raise ValueError("Invalid delay crop length")
    Had = np.fft.ifft(np.fft.fft(Hf, axis=-2, norm="ortho"),
                      axis=-1, norm="ortho")
    total = np.sum(np.abs(Had) ** 2, axis=(-2, -1))
    if np.any(total <= 0):
        raise ValueError("Zero-power channels require an explicit outage policy")
    crop = Had[..., :keep_taps]
    retained = np.sum(np.abs(crop) ** 2, axis=(-2, -1)) / total
    return crop, retained

def from_angle_delay(crop, n_subcarriers):
    crop = np.asarray(crop)
    if crop.ndim != 3 or not 1 <= crop.shape[-1] <= n_subcarriers:
        raise ValueError("Expected [snapshot, tx_ant, kept_delay_tap]")
    Had = np.pad(crop, ((0, 0), (0, 0),
                       (0, n_subcarriers - crop.shape[-1])))
    Hf = np.fft.ifft(np.fft.fft(Had, axis=-1, norm="ortho"),
                     axis=-2, norm="ortho")
    return Hf[:, None, :, :]

def model_tensor(crop, train_scale):
    if not np.isfinite(train_scale) or train_scale <= 0:
        raise ValueError("Scale must be fitted on training data and frozen")
    return (np.stack([crop.real, crop.imag], axis=1)
            / train_scale).astype(np.float32)
```

这里推荐先用训练集固定的 RMS 尺度和线性输出头，例如：

$$
s_{\mathrm{train}}=\sqrt{\frac{1}{NN_tK}\sum_{i,a,k}|H_{\mathrm{ad},i,a,k}|^2}.
$$

它是新训练方案，不是原 CsiNet 的 $[0,1]$ 归一化复现。若保留原架构 sigmoid 输出，要另定映射、截断和 OOD 饱和检测；不要把旧代码的减 $0.5$ 操作直接套到新数据。

若选择每样本归一化，也要保存恢复所需尺度，说明 BS 如何取得它，并计入边信息位数。完整原始 CSI 始终保留，避免丢掉路径损耗导致错误的链路结论。

## 3. 必须通过的六项检查

| 检查 | 方法 | 能说明什么 |
|---|---|---|
| 形状和身份 | 核对轴、阵列坐标、UE/BS/轨迹 ID | 防止样本或天线错位 |
| 全 tap 往返 | $K=N_f$ 时，变换再逆变换应恢复原数组 | 仅验证数值处理，不验证信道真实性 |
| 裁剪下限 | 裁剪后直接补零逆变换，比较完整频域 NMSE | 得到不含模型误差的预处理下限 |
| 能量分布 | 按域报告 $\eta_K$ 的分位数与异常比例 | 检查 $K=32$ 是否足够 |
| 时间/空间连续性 | 距离、时间差及相邻快照相关性 | 发现随机重置或不合理拼接 |
| 划分审计 | 按区域、轨迹、realization 和噪声副本追踪组 | 防止训练/适配与最终测试泄漏 |

信道和噪声的随机种子分开，数据生成配置、预处理 hash 与模型权重一起锁定。无需将工具环境、地理坐标或隐藏场景标签全部提供给 Agent。

## 4. 与仓库旧 CsiNet 的关系

本地 `P22_CsiNet_community/channels_last/CsiNet_onlytest.py` 读取 `HT` 并 reshape 为两通道 $32\times32$，在评价时减 $0.5$；`HF_all` 另用于频域相关性。它还包含与特定数据契约绑定的补零长度和子载波选取。

[CsiNet 原论文](https://arxiv.org/html/1712.08919v4)的训练数据来自 COST 2100，完整频域维度与本方案不同。相同输入 shape 不能证明预处理、信道分布或预训练权重兼容。本次建议复用网络思想或另行重训练；若要复现原结果，应使用其匹配的数据和评价流程。

## 5. 误差与部署时间的定义

压缩重建质量评价使用 $t_{\mathrm{obs}}$ 的输入和对应重建；实际预编码/业务评价使用 $t_{\mathrm{apply}}$ 的真实信道。两者分开报告，否则会把 CSI 老化损失当成压缩误差或把延迟当零成本。

至少分项记录裁剪损失、压缩误差、量化误差、估计误差代理、反馈失效与 CSI 老化。不能用裁剪域的好 NMSE 直接声称吞吐或 BLER 改善。

## 6. 本次数值检查记录

2026-10-25 已对本页 NumPy 函数执行合成数组检查：已知空间/时延单 bin 定位、完整 FFT 往返、裁剪误差等于丢失能量比例、两通道 shape 和零功率拒绝均通过；单 bin 往返最大绝对误差约 $3.46\times10^{-15}$。两个 Python 示例的语法解析通过。以上不含生成器运行、真实场景或无线链路验证；MATLAB 示例只做源码接口核对。

[数据方案](../../分析文档/实验工具链/CSI压缩反馈数据生成方案.md) · [DeepMIMO 指南](DeepMIMO生成指南.md) · [QuaDRiGa 指南](QuaDRiGa生成指南.md)
