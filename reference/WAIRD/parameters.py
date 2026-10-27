'''
版权所有 (C) 2021. 华为技术有限公司.
本程序希望对您有用，但不提供任何担保，
甚至不包含适销性或特定用途适用性的默示担保。
'''

import warnings
import numpy as np
import multiprocessing
from PIL import Image
warnings.filterwarnings('ignore')  # 忽略所有警告信息

numCores = multiprocessing.cpu_count()        # 获取可用CPU核心数，用于并行生成数据。若内存或核心数有限可适当减小

# 生成数据集的参数
# carrierFreq = '28_0'                         # 载波频率，例如2_6表示2.6GHz，60_0表示60.0GHz
# BWGHz = 0.04608                              # 带宽，单位为GHz
# subcarriers = 384                            # 子载波数量
# carrierSampleInterval = 6                    # 子载波采样间隔，减小计算量
# Nt = [32, 1, 1]                              # 基站天线阵列在[x, y, z]轴的排列，例如[1, 8, 8]，[1, 32, 4]

# carrierFreq = '6_0'                            # 载波频率，例如2_6表示2.6GHz，60_0表示60.0GHz
# BWGHz = 0.02304                                # 带宽，单位为GHz
# subcarriers = 64*12                            # 子载波数量
# carrierSampleInterval = 12                     # 子载波采样间隔，减小计算量
# Nt = [1, 8, 4]                                 # 基站天线阵列在[x, y, z]轴的排列，例如[1, 8, 8]，[1, 32, 4]

carrierFreq = '2_6'                            # 载波频率，例如2_6表示2.6GHz，60_0表示60.0GHz
BWGHz = 0.02304                                # 带宽，单位为GHz
subcarriers = 64*12                            # 子载波数量
carrierSampleInterval = 12                     # 子载波采样间隔，减小计算量
Nt = [1, 8, 4]                                 # 基站天线阵列在[x, y, z]轴的排列，例如[1, 8, 8]，[1, 32, 4]


Nr = [2, 1, 1]                                 # 用户端天线阵列在[x, y, z]轴的排列，例如[2, 2, 1]，[4, 2, 1]
sampledCarriers = int(subcarriers/carrierSampleInterval)  # 采样后的子载波数量，用于深度学习
spacing_t = [0.5, 0.5, 0.5]                    # 发射端天线间距（以波长为单位）
spacing_r = [0.5, 0.5, 0.5]                    # 接收端天线间距（以波长为单位）
Pattern_t = {'Power':0}                        # 天线类型，默认全向天线，发射功率0 dBm
Basis_t = np.eye(3)                            # 发射端天线阵列旋转基，默认无旋转
Basis_r = np.eye(3)                            # 接收端天线阵列旋转基，默认无旋转
saveAsArray = False                            # 若为True，则将信道保存为numpy数组
saveAsImage = False                            # 若为True，则将信道保存为图片
maxPathNum = 1000                              # 每个基站-用户链路的最大路径数，建议大于0，1000表示基本无限制
scenario = 2                                   # 选择生成信道的场景，具体场景说明见下方
scenarioFolder = f'data/scenario_{scenario}/'  # 场景数据文件夹路径
generatedFolder = f'data/generated_{scenario}_{carrierFreq}_{maxPathNum}_{Nt[0]}_{Nt[1]}_{Nt[2]}_{Nr[0]}_{Nr[1]}_{Nr[2]}_{int(BWGHz*1000)}_{sampledCarriers}/'  # 生成数据保存路径

if scenario==1:
    # 场景1：在大量环境中稀疏投放用户
    # 最多可选10000个环境，每个环境可选5个基站和30个用户
    ENVnum = 10000                                 # 选取的环境数量，最大为10000
    BSlist = list(range(5))                    # 每个环境中基站索引范围0~4，例如[0]表示选基站0，[2,4]表示选基站2和4
    UElist = list(range(30))                   # 每个环境中用户索引范围0~29，例如[0]表示选用户0，[2,17,26]表示选用户2、17和26
    BSnum = len(BSlist)                        # 每个环境中的基站数量，最大为5
    UEnum = len(UElist)                        # 每个环境中的用户数量，最大为30
elif scenario==2:
    # 场景2：在部分环境中密集投放用户
    # 最多可选100个环境，每个环境可选1个基站和10000个用户
    ENVnum = 100                                # 选取的环境数量，最大为100
    BSlist = list(range(1))                    # 每个环境中基站索引范围0~0，例如[0]表示选基站0
    UElist = list(range(10000))                # 每个环境中用户索引范围0~9999，例如[0]表示选用户0，[2,170,2600]表示选用户2、170和2600
    BSnum = len(BSlist)                        # 每个环境中的基站数量，最大为1
    UEnum = len(UElist)                        # 每个环境中的用户数量，最大为10000
else:
    raise('更多场景正在准备中。')
