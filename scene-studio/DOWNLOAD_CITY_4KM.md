# 四公里城市：仅下载几何与材料参数

日期：2026-10-26。当前脚本默认size=4000，按四公里构建清单的36个实际来源获取数据。已移除完整ZIP下载模式；不提供--full选项。

## 为什么不需要源信道

源城市的power/phase/delay/AoA/AoD/inter/channel数据对应原布局和TX/RX，不能用于重组城市直接拼接。我们将在新几何、材料和部署下自行运行RT。所需数据是objects.json（对象/面索引）、vertices.mat或vertices.npz（顶点）、params.json及materials文件（若存在），以及许可记录。下载几何不自动证明网格闭合或材料真实性，也不自动替换当前预览资产；还需对象匹配、网格检查和电磁材料配置。

## 命令

在仓库根目录运行：

```sh
conda activate lcm
# 离线大小报告，默认四公里
python scene-studio/run.py download-city
# 获取尚未统计来源的ZIP目录
python scene-studio/run.py download-city --size 4000 --probe
# 只下载所选几何/参数，不下载信道矩阵或完整ZIP
python scene-studio/run.py download-city --size 4000 --download
# 单场景测试
python scene-studio/run.py download-city --size 4000 --download --only asu_campus_3p5
# 仍支持一公里和两公里
python scene-studio/run.py download-city --size 1000 --download
python scene-studio/run.py download-city --size 2000 --download
```

[脚本](python/lcm_scene/sources/download_city_geometry.py)仅需Python3.11标准库，默认输出[data/deepmimo-scenes/source/city-4km-official](data/deepmimo-scenes/source/city-4km-official/)。按来源保存文件，download-plan.json记录大小/状态/哈希。

## 存储估算与实测边界

4km的36来源包含1km全部30来源，新增6来源：asu_campus_3p5、city_19_oklahoma_3p5、city_32_sydney_3p5、city_4_phoenix_3p5、city_5_philadelphia_3p5、city_90_nanjing_3p5。

已取得的30来源实测几何压缩成员合计660548字节（0.661MB），解压6112454字节（6.112MB）。新增6来源目录请求在官网重定向处出现TLS EOF/非ZIP内容，脚本安全停止，因此36来源完整精确总数尚未知。

按30来源平均大小外推36来源：压缩成员约0.793MB，解压约7.335MB。保守预算可按压缩1–2MB、解压8–15MB准备；这是规划估算，不是新6来源的实测上限。建议预留50–100MB，包括元数据与后续简单网格处理；密集RT/CSI输出需另计。

HTTP目录、局部文件头和块预读会增加传输量，实际网络下载预计数MB，不能把压缩成员总和当作严格网络流量。网站可能按整个ZIP授权大小计额度，必须遵守其规则；不绕过限额。

统计见[四公里下载计划](data/deepmimo-scenes/source/city-4km-official/download-plan.json)、[探测日志](generated/reports/city-4km-download-probe.log)、[新增来源探测](generated/reports/city-4km-extra-probe.log)。30来源完整包合计1.027GB只是对照，脚本不会下载它们。

## 安全与复跑

仅白名单文件被解压写盘，不保存原信道矩阵。Range不正确时拒绝读取，不退化成完整包。已完成文件CRC/SHA256校验后跳过；未完成.partial成员重跑该成员。403/429/TLS或ZIP异常时停止并记录（退出码2）；恢复网络或额度后重跑，不关闭TLS或绕过官方限额。

这轮更新只做目录探测，不下载全部几何。下载完成不等于源RT工程、许可审查、源对象映射和材料配置完成。
