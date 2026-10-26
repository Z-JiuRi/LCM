# 一公里城市所用 DeepMIMO 几何下载

日期：2026-10-26。读取当前一公里构建清单的30个实际来源，不下载未使用场景，也不下载源城市的信道矩阵。原城市已能进行假设材料下的RT试算，此下载用于补全正式几何/材料元数据，不是计算重组城市信道的必要前置。

## 实测存储量

已逐一取得30个官方ZIP目录，均包含objects.json、params.json、vertices文件，共90个文件：25个vertices.mat、5个vertices.npz。

| 内容 | 实测逻辑字节数 | 十进制大小 |
|---|---:|---:|
| 30个完整ZIP（含源路径数据，不建议全下） | 1,027,407,069 | 1.027 GB |
| 默认所选几何/参数的ZIP压缩成员总量 | 660,548 | 0.661 MB |
| 默认所选文件解压后的合计大小 | 6,112,454 | 6.112 MB |

脚本直接解压保存，不保留完整ZIP。因此默认新增磁盘占用约6.1MB，加计划JSON、哈希和文件系统分配开销，建议预留20–50MB。正式几何后续转换OBJ/PLY、材质处理和RT输出另计；当前665建筑简单OBJ仅约0.38MB，但不能代表更精细模型。

HTTP读取还包含ZIP尾目录、局部文件头和64KiB块预读，实际网络传输会大于0.661MB，通常为数MB量级；网站可能按完整包大小扣下载授权额度，不能把选择性传输量当作额度使用量。官网限额/授权条款必须遵守。

数据依据：[下载计划](data/deepmimo-scenes/source/city-1km-official/download-plan.json)、[目录探测日志](generated/reports/city-1km-download-probe.log)。大小对应本次官方版本，后续版本可能变化。

## 使用

在仓库根目录：

```sh
conda activate lcm
# 离线读取本地已统计大小，无网络请求
python scene-studio/run.py download-city --size 1000
# 新机器探测官方ZIP目录，可能消耗官网授权额度
python scene-studio/run.py download-city --size 1000 --probe
# 下载30来源的几何与参数，跳过已验证完成文件
python scene-studio/run.py download-city --size 1000 --download
# 只先下载Boston作测试
python scene-studio/run.py download-city --size 1000 --download --only boston5g_3p5
```

也可直接运行[完整Python脚本](python/lcm_scene/sources/download_city_geometry.py)：

```sh
python scene-studio/python/lcm_scene/sources/download_city_geometry.py --size 1000 --download
```

仅需Python3.11标准库，不需DeepMIMO包。默认输出[官方数据目录](data/deepmimo-scenes/source/city-1km-official/)，每来源一个子目录，另有download-plan.json。`--output`可指定其他位置；换目录后需要重新取得目录信息。

可用`--include-positions`额外取原TX/RX位置（默认不取，存储量需重新统计）；原坐标只作参考，不能直接当作新城市部署。`--max-scene-mib`默认512，用于拒绝意外大文件。

## 下载与续跑行为

- 采用HTTP Range和Python zipfile，支持ZIP64及CRC检查；如果服务器未正确返回206/Content-Range，立即拒绝，不退化成完整包下载。
- 保留每完成文件SHA256，重跑会验证并跳过。中途未完成的.partial文件重新读取该成员，不进行ZIP压缩流字节级续传。
- 403/429和传输错误会停止并记录原因（退出码2），不会轮换网络/身份、绕过限额或关闭TLS验证。网络恢复/额度恢复后重跑。
- 同目录已有非脚本验证的正式文件时不会覆盖。源名字、重音字符自动URL编码；拒绝路径穿越。
- 默认只取对象/顶点/参数及单独材料或许可文件（若存在），不取power/phase/delay/aoa/aod/inter/channel。未提供原RT工程时不声称获得完整源工程。

本轮30包目录探测成功；随后真实成员下载曾遇到远端ZIP内容异常和TLS EOF，已安全停止，不能把目录探测成功写成全部下载完成。4项下载单元测试与原有9项测试均通过。可用计划中的status/sha256检查哪些文件实际完成。

## 注意

正式对象ID与原预览索引需通过几何匹配核验；下载完成不自动替换当前城市。材料需要检查params.json里的内容和频率响应，不保证每包都有独立材质文件或完整电磁参数。源城市原信道不能用于拼接后城市，需要在新布局重新RT。来源许可与再分发条件仍适用。
