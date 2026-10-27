'''
版权所有 (C) 2021. 华为技术有限公司.
本程序希望对您有用，但不提供任何担保，
甚至没有适销性或特定用途的隐含担保。
'''

import os
from util import *
from tqdm import tqdm
from parameters import *
from torch.utils.data import Dataset,DataLoader

class DoraSet(Dataset):
    def __init__(self):        
        # 载波频率（GHz），将字符串中的下划线替换为小数点
        self.fcGHz = float(carrierFreq.replace('_','.'))
        # 采样的子载波频率范围（GHz）
        self.fGHz  = np.linspace(-0.5*BWGHz,0.5*BWGHz,sampledCarriers)+self.fcGHz
        self.Hs = {}   # 存储信道矩阵
        self.Ps = {}   # 存储路径信息
        self.envs = [] # 环境编号列表
        path_list = os.listdir(scenarioFolder) # 获取所有环境文件夹
        path_list.sort(key=lambda x:int(x))    # 按数字排序
        # 遍历指定数量的环境
        for i in tqdm(path_list[:ENVnum]):
            self.envs.append(i)
            envPath = os.path.join(scenarioFolder, i)
            # 加载信道矩阵
            H = np.load(os.path.join(envPath, f'H_{carrierFreq}_G.npy'),allow_pickle=True,encoding='latin1')
            self.Hs[len(self.envs)-1] = H.item()
            # 加载路径信息
            P = np.load(os.path.join(envPath, 'Path.npy'),allow_pickle=True,encoding='latin1')
            self.Ps[len(self.envs)-1] = P.item()
            # 如果需要保存为数组，则创建对应文件夹
            if saveAsArray:
                arrayFolder = os.path.join(generatedFolder, i, 'array')
                if not os.path.exists(arrayFolder):
                    os.makedirs(arrayFolder)
            # 如果需要保存为图片，则创建对应文件夹
            if saveAsImage:
                imageFolder = os.path.join(generatedFolder, i, 'image')
                if not os.path.exists(imageFolder):
                    os.makedirs(imageFolder)
        
    def __getitem__(self, idx):
        # 根据索引计算当前环境、基站和用户编号
        curEnv = idx//(BSnum*UEnum)
        curLink = idx%(BSnum*UEnum)
        bsIdx = curLink//UEnum
        ueIdx = curLink%UEnum
        # 构造链路字符串
        linkStr = f'bs{BSlist[bsIdx]}_' + (f'ue{UElist[ueIdx]}' if scenario==1 else f'ue{UElist[ueIdx]:05d}')
        # 获取信道矩阵和路径信息
        H = self.Hs[curEnv][linkStr]
        P = self.Ps[curEnv][linkStr]
        tau = np.asarray(P['taud']) # 路径时延
        sortedPath = np.argsort(tau)[:maxPathNum] # 选取最短的maxPathNum条路径
        doa = np.asarray(P['doa']) # 到达角
        dod = np.asarray(P['dod']) # 发射角
        # 计算接收端阵列响应
        pos_r = antennaPosition(Nr,spacing_r,Basis_r)        
        res_r = arrayResponse(doa,pos_r,sortedPath)
        # 计算发射端阵列响应
        pos_t = antennaPosition(Nt,spacing_t,Basis_t)
        res_t = arrayResponse(dod,pos_t,sortedPath)
        # 天线方向图功率
        pow_t = 10**(Pattern_t['Power']/10)
        # 归一化信道
        norm_H = H*(pow_t**0.5)/(subcarriers**0.5)
        # 计算OFDM信道响应
        ofdm_H  = norm_H[sortedPath,None]*np.exp(-2*1j*np.pi*tau[sortedPath,None]*self.fGHz[None,:])        
        # 计算频域信道响应 (Nt, Nr, Nf)
        CFR = np.sum(ofdm_H[:,None,None,:]*res_t[:,:,None,None]*res_r[:,None,:,None],axis=0)        
        # 重塑为 (Nt*Nr, Nf)
        channel = np.reshape(CFR,(-1,sampledCarriers))
        # 信道归一化
        channel = channel / np.sqrt(np.mean(np.abs(channel) ** 2))
        
        # 保存为npy数组
        if saveAsArray:
            arrayPath = os.path.join(generatedFolder, self.envs[curEnv], 'array', linkStr+'.npy')
            array = np.concatenate((np.real(channel)[None,...],np.imag(channel)[None,...]),axis=0)
            np.save(arrayPath,array)            
        # 保存为图片
        if saveAsImage:
            norm_channel = channel/np.max(np.abs(channel)) # 归一化到[-1,1]
            image = (norm_channel/2+0.5+0.5*1j)*255
            image = np.concatenate((np.uint8(np.round(np.real(image)))[:,:,None],np.uint8(np.round(np.imag(image)))[:,:,None]),axis=-1)
            image = Image.fromarray(image,mode='LA')            
            imagePath = os.path.join(generatedFolder, self.envs[curEnv], 'image', linkStr+'.png')
            image.save(imagePath)
        # 拼接实部和虚部，输出shape为(2, Nt*Nr, Nf)
        channel = np.concatenate((np.real(channel)[None,...],np.imag(channel)[None,...]),axis=0)
        return channel
        
    def __len__(self):
        # 数据集总长度 = 环境数 * 基站数 * 用户数
        return ENVnum*BSnum*UEnum
        

if __name__ == "__main__":
    print('初始化...')    
    doraset = DoraSet()
    # print(f'环境数量: {ENVnum}, 基站数量: {BSnum}, 用户数量: {UEnum}')
    # print(f'数据集大小: {len(doraset)}')
    # 创建数据加载器
    generator = DataLoader(doraset, batch_size=1000, shuffle=False, num_workers=numCores, pin_memory=True)
    print('正在生成...')
    data = []
    # 遍历数据集并收集所有信道数据
    for channel in tqdm(generator):
        data.append(channel)
    # 拼接所有batch
    data = torch.cat(data, dim=0)
    # 保存为npy文件
    data_dir = f'waird_1_env{ENVnum}'
    if not os.path.exists(f'data/{data_dir}'):
        os.makedirs(f'data/{data_dir}')
        
    # 按82划分数据集
    total = data.shape[0]
    train_end = int(total * 0.8)
    train_data = data[:train_end]
    test_data = data[train_end:]

    np.save(f'data/{data_dir}/train.npy', train_data.numpy())
    np.save(f'data/{data_dir}/test.npy', test_data.numpy())
    print('完成!')