# DeepMIMO v4：从路径到CSI的源码审查

日期：2026-10-26。检出v4.0.5，提交48945c29b47c537bf2ea82a929c33bd6ff7aac31；同时对比origin/main提交45238f9a4c4311b8747dad2eefdebc8c74b1a104。仅静态阅读，没有安装依赖或运行大规模RT。官方工作树未修改；来源与许可冲突见[来源记录](<DeepMIMO-v4-SOURCE.md>)。

## 1. 两个独立阶段，不能混淆

**射线追踪：**几何、材料、TX/RX位置送给Sionna RT、Wireless InSite等后端，寻找路径并计算复增益、时延、到达/出发角和交互类型。

**CSI合成：**DeepMIMO读取已存路径，结合阵列、方向图、频点、时间计算复数H。`compute_channels()`不重新搜索路径，不会凭空增加缺失绕射/散射。

调用入口：[Dataset.compute_channels](<DeepMIMO-v4/deepmimo/datasets/dataset.py#L464-L534>)。先配置参数和时间、阵列响应，再调用`_generate_mimo_channel`。没有时间输入时t=0；多时间点另加时间轴。时域分支保留路径系数及路径轴，不是自动IFFT得到的均匀延迟采样CIR。

## 2. 频域公式（rx_filter关闭）

N为总OFDM子载波数，K为实际选择的频点数；k为选中的整数索引；B为带宽Hz；tau为秒；phi为路径初相度数；P_eff为经过TX/RX方向图增益后的线性路径功率数值。

$$
H_{u,r,t}[k,s]=\sum_p a_{r,u,p}a_{t,u,p}\sqrt{P_{\mathrm{eff},u,p}/N}
\exp(j\pi\phi_{u,p}/180+j2\pi f_{D,u,p}s)
\exp(-j2\pi\tau_{u,p}Bk/N).
$$

- [OFDMPathGenerator](<DeepMIMO-v4/deepmimo/generator/channel.py#L357-L433>)：Ts=1/B，delay_n=tau/Ts=tau*B；负号频率时延相位；除以sqrt(N)，**N是总子载波数，不是K**。
- [批处理实现](<DeepMIMO-v4/deepmimo/generator/channel.py#L543-L585>)使用相同公式并优化均匀频点的递推。
- 频率偏移约定是kB/N，非负索引，**不是自动fftshift到[-B/2,B/2)**。载频不再直接出现在该时延指数中，而由上游路径/角度/功率记录体现。
- [天线方向图功率](<DeepMIMO-v4/deepmimo/datasets/dataset.py#L1082-L1117>)先作用于路径功率，随后频域生成器合成H。
- 代码把功率dB数值转换为10^(power/10)。该版本有dBm/dBW注释冲突，不能称为已经一致校准的“dBm转W”；dBm转W须有-30偏移。跨后端比较绝对功率应核对各格式基准、发射功率和归一化，不只看字段名称。
- NaN路径功率是padding并置零；[超过延迟窗的路径裁剪](<DeepMIMO-v4/deepmimo/generator/channel.py#L552-L557>)：tau*B>=N时置零，即tau>=N/B。不是CP校验，也不是自动减去首径时延。静态同步脚本在生成H之后做时延补偿，不能恢复此前被裁掉的路径。
- 可选rx_filter=True使用有限窗sinc延迟滤波再投影频点；默认关闭。

## 3. 天线轴、间距、姿态

[阵元索引](<DeepMIMO-v4/deepmimo/generator/geometry.py#L125-L141>)：x恒0，shape第一维沿Y，第二维沿Z，第一维索引变化最快。因此[32,1]为Y方向ULA，[8,4]为8Y×4Z面阵。

[相位计算](<DeepMIMO-v4/deepmimo/generator/geometry.py#L105-L122>)使用sin(theta)cos(phi)、sin(theta)sin(phi)、cos(theta)：theta是从+Z算的极角，不能把字段el或文档的elevation字样直接当作“水平面以上仰角”。阵元响应为exp(+j2pi*spacing*index·direction)，spacing=0.5是**0.5波长，不是0.5m**。无1/sqrt(M)阵列归一化。

[角度旋转实现](<DeepMIMO-v4/deepmimo/generator/geometry.py#L322-L357>)将参数从度转弧度。该实现第三个rotation分量通过phi-gamma改变方位角；不能直接照搬Sionna的[azimuth,pitch,roll]弧度三元组。文档示例与源码命名存在混乱，转换时应以实现及单点方向测试核对。

## 4. 输出维度与默认值

[默认参数](<DeepMIMO-v4/deepmimo/generator/channel.py#L149-L175>)：BS[8,1]，UE[1,1]，spacing=.5，isotropic，freq_domain=True，总N512，B10MHz，selected=[0]，num_paths25。因此默认单Dataset输出[U,1,8,1] complex64，不是默认512个频点。

自定义BS32端口、UE1端口、选64频点：

```text
官方原始H：        [U,1,32,64] complex64
去除单RX轴：       [U,32,64] complex64
拆实部/虚部：      [U,2,32,64] float32（额外预处理，不是官方默认）
```

多个TX/RX配对是MacroDataset的多个子Dataset，通常返回列表，**不是自动一个物理站点轴**。[MacroDataset返回行为](<DeepMIMO-v4/deepmimo/datasets/dataset.py#L2470-L2494>)。多快照频域H是[U,M_rx,M_tx,K,N_time]。

## 5. UE撒点与RT采样预算

[gen_plane_grid / gen_rx_grid](<DeepMIMO-v4/deepmimo/pipelines/txrx_placement.py#L39-L106>)：arange(min,max+spacing,spacing)，meshgrid展平，X最快变化，固定Z。未整除时可能超上界小于一个spacing。标准管线在这里不筛建筑内部或植被；这不能反推“建筑内所有点必然全零”。[管线入口](<DeepMIMO-v4/scripts/pipelines/pipeline_runner.py#L57-L75>)直接把网格送入RT。

[真正的Sionna参数映射](<DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_raytracer.py#L152-L163>)：

```python
samples_per_src = rt_params['n_samples_per_src']
max_num_paths_per_src = rt_params['max_paths_per_src']
max_depth = rt_params['max_reflections']
diffuse_reflection = rt_params['ds_enable']
refraction = rt_params['refraction']
```

[RX分批](<DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_raytracer.py#L181-L233>)仅限制每批接收机数，所有批使用同一个solver kwargs字典。**没有samples_per_src除以或乘以RX数**。samples_per_src是每TX源的射线方向采样预算，不是一个可简单按RX均分的配额。本地生成器按chunk乘回射线数不是官方做法，也没有可据此保证每链路质量相同的依据。

后端支持机制不等于管线全部开启。v4.0.5的这个Sionna包装器映射diffuse/refraction，但没有把max_diffractions映射给PathSolver；配置里填写max_diffractions不能自动开启绕射。Sionna RT本身支持绕射，转换器也识别它。

## 6. 转换器做什么，以及版本陷阱

[Sionna路径转换](<DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L250-L280>)：a!=0为有效；幅度转20log10|a|、初相转度、角度从弧度转度、复制tau；[路径padding](<DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L42-L63>)用NaN。

Sionna交互值1/2/4/8分别映射DeepMIMO反射1、散射3、透射4、绕射2：[映射表](<DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L16-L33>)。数值编码不能混用。

**发布版v4.0.5问题：**它先取Sionna索引顺序的前25条非零路径，才按幅度排序，不是全体最强25条。当漫散射很多时，后面的强径可能丢失。当前main已经改为全体非零路径按幅度排序后取25，见[对比补丁](<DeepMIMO-v4-main-converter.diff>)。不要将发布版和main的行为混称“v4默认”。

**元数据问题：**[raytracer最后导出](<DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_raytracer.py#L235-L237>)传的是管线参数rt_params，而非实际映射的solver kwargs；[exporter](<DeepMIMO-v4/deepmimo/exporters/sionna_exporter.py#L228-L250>)把本地solver字段的默认值补上后再update。max_reflections、n_samples_per_src、ds_enable等管线字段不覆盖max_depth、samples_per_src、diffuse_reflection同义字段。因此部分自定义计算配置可能被错误记录为默认值；diffraction别名还硬编码False。不能只看params.json就证明某条管线实算配置。

RX坐标保留、NaN padding；num_active_points等统计并非人口/并发UE数，转换器的接收有效数主要按首TX统计，不应当作所有BS的覆盖并集或物理遮挡证明。

## 7. 对用户三个参考脚本的准确比较

| 实现 | TX/RX配置 | 频点 | 训练输出 | 归一化 |
|---|---|---|---|---|
| [generate5](<deepmimo/generate5.py#L53-L114>) | TX[8,4]=32，RX[2,1]=2 | N1024前64：k=0..63，20MHz | [N,2,64,64] | maxabs |
| [static_sync](<deepmimo/generate_static_sync_csi.py#L40-L45>) | TX[32,1]=32，RX[1,1]=1 | N1024隔16取64：k=0..1008，20MHz | [N,2,32,64] | 首显著径时延对齐+RMS |
| [WAIRD参数](<WAIRD/parameters.py#L28-L41>)及[生成器](<WAIRD/generator_v1.py#L55-L95>) | TX[1,8,4]=32，RX[2,1,1]=2 | linspace(fc-B/2,fc+B/2,64)，B23.04MHz | [N,2,64,64] | 数组RMS；可选PNG额外maxabs/8bit |

- generate5的频点间隔19.53125kHz，64点端点跨度1.23046875MHz；static_sync间隔312.5kHz，端点跨度19.6875MHz。两者虽都64点，但频域任务很不同。
- WAIRD虽然用768/12计算64点，实际生成使用linspace含两端点，频点间隔23.04MHz/63≈365.714kHz，不是隔12选离散FFT bins。
- reshape可逆，不会凭空丢失数值，但需要保留轴顺序。DeepMIMO原始为RX×TX，WAIRD为TX×RX，两者flatten后的64个通道顺序不同；RX阵列方向也不同。
- 纯实虚拆分与reshape可逆；丢掉RMS/maxabs系数、tau_ref、未选频点或8bit量化后，不能说完整信息完全等价。
- static_sync是用户参考脚本，不是官方；[其RMS与时延补偿](<deepmimo/generate_static_sync_csi.py#L148-L161>)是额外任务预处理。WAIRD保留其原版权和来源，不能整体声称是我们写的。

## 8. 审查时本地CSI生成器的问题（历史记录；后续已修正）

2026-10-26后续按用户授权完成脚本修正，使用方式和当前验证范围见[脚本说明](<../scripts/README.md>)。以下为本轮静态审查时发现的问题，保留作为修正依据，不再代表最新代码状态。新的生成器已提供固定每源预算、完整路径/CFR保存、服务扇区选择、时延对齐/RMS、训练数组及可追溯sidecar；只跑合成测试，没有重跑全城RT。

没有在本轮修改[本地生成器](<../scripts/generate_city_csi.py>)或重跑数据；本轮是源码审查。

- 它直接调用Sionna CFR并按所有扇区保存[sector,U,32,64] complex64，没有实现此前推荐的最强服务扇区关联、时延对齐/RMS、train/val/test输出[U,2,32,64]。
- [samples缩放](<../scripts/generate_city_csi.py#L192-L208>)不是官方固定每源射线预算。
- 将no-path归为确定几何遮挡不成立；应写“在该配置下没有找到有效路径”。此前试验没有证明收敛，也没有证明高样本异常根因是哈希碰撞或上游bug，应撤回这类推断。
- link_gain=sum(abs(H))不是功率，应定义mean(abs(H)^2)或逐径sum(abs(a)^2)等，并记录单位/归一化/天线功率基准。
- worker新增物理开关不等于CLI和driver都已暴露；不能承诺命令行已开启绕射/漫散射。
- [本地几何导出](<../scripts/city_geometry.py>)对潜在多材料资产用首面材料覆盖整资产、部分参数fallback不标假设等问题仍需修正；当前城市资产每个资产内材料键相同，不能泛称已有场景已因此丢材料。

**建议后续严格沿官方两阶段组织：固定每源射线预算与RX分批，保存CIR/时延/角度及实际求解参数；再以明确的天线端口顺序、频点和尺度合成CSI；最后单独生成带tau_ref/RMS/服务扇区/坐标/split记录的压缩训练格式。**不需要为做这个审查重新运行全城RT。
