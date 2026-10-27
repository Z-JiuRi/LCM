'''
Copyright (C) 2021. Huawei Technologies Co., Ltd.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
'''

import sys
sys.path.append("../..")
from util import *
from parameters import *
from torchvision import transforms
from torch.utils.data import Dataset,DataLoader
from tqdm import tqdm
import matplotlib.cm as cm
from matplotlib import pyplot as plt
import torch.multiprocessing
torch.multiprocessing.set_sharing_strategy('file_system')

imageSize = 256
readImage = True

class PrepareData(Dataset):

    def __init__(self,paths):
        self.paths = paths
        
    def __getitem__(self, idx):
        env,linklocA,sight,distance,angle,gain = readEnvLink(scenarioFolder,self.paths[idx],carrierFreq,imageSize,scenario)
        return env,linklocA,sight,distance,angle,gain
        
    def __len__(self):
        return len(self.paths)

class DoraSet(Dataset):

    def __init__(self,cases=10000,start=0,set='valid'):
        self.start = start
        self.cases = cases
        self.set = set
        self.imageSize = imageSize
        path_list = os.listdir('../../'+scenarioFolder)
        path_list.sort(key=lambda x:int(x))
        self.paths = path_list[start:start+cases]
        prepareData = PrepareData(self.paths)
        prepareLoader = DataLoader(prepareData, batch_size=1, shuffle=False, num_workers=numCores, pin_memory=False)
        print(f'Preparing {set} data...')
        self.linklocAs = []
        self.sights = []
        self.angles = []
        self.distances = []
        self.envs = []
        self.gains = []
        for (envs,linklocAs,sights,distances,angles,gains) in tqdm(prepareLoader):
            self.envs.append(envs[0,:].float())
            self.linklocAs.append(linklocAs[0,:].float())
            self.sights.append(sights.float())
            self.distances.append(distances.float())
            self.angles.append(angles.float())
            self.gains.append(gains.float())
        
    def __getitem__(self, idx):
        curEnv = idx//(BSnum*UEnum)
        curLink = idx%(BSnum*UEnum)
        bsIdx = curLink//UEnum
        ueIdx = curLink%UEnum
        envImg = self.envs[curEnv]
        linklocA = self.linklocAs[curEnv]
        ImgSize = linklocA[:2].numpy().astype(np.int)
        if scenario==1:
            linklocA = torch.reshape(linklocA[2:],(150,4))
            BSloc = linklocA[::30,:2][BSlist[bsIdx],:]
            UEloc = linklocA[UElist[ueIdx],2:]
        else:
            BSloc = linklocA[2:4]
            linklocA = torch.reshape(linklocA[4:],(10000,2))
            UEloc = linklocA[UElist[ueIdx],:]
        distance = self.distances[curEnv][0:1,BSlist[bsIdx]*30+UElist[ueIdx]]
        gain = self.gains[curEnv][0:1,BSlist[bsIdx]*30+UElist[ueIdx]]
        angle = self.angles[curEnv][0,BSlist[bsIdx]*30+UElist[ueIdx]]
        channel = readChannel(readImage,generatedFolder,self.paths[curEnv],BSlist[bsIdx],UElist[ueIdx],scenario) 
        channel = channel/np.max(np.abs(channel))
        channel = torch.FloatTensor(np.concatenate((np.real(channel)[None,:,:],np.imag(channel)[None,:,:]),axis=0))
        sight = self.sights[curEnv][0:1,BSlist[bsIdx]*30+UElist[ueIdx]]
        scale = torch.FloatTensor([imageSize/np.max(ImgSize)])
        return envImg, distance, channel, BSloc, UEloc, sight, scale, angle, gain
        
    def __len__(self):
        return self.cases*BSnum*UEnum

if __name__ == '__main__':
    dataset=DoraSet(cases=1, start=0)
    fig, ax = plt.subplots()
    imageShown = False
    for i in range(30):
        envImg, distance, channel, BSloc, UEloc, sight, scale, angle, gain = dataset[i]
        if not imageShown:
            ax.imshow(1-envImg[0,:,:], cmap='gray',vmin=0.0,vmax=1.0)
            imageShown = True
        marker = 's' if sight.item()==1 else 'v'
        ax.scatter(imageSize*UEloc[0],imageSize-imageSize*UEloc[1], marker=marker,s=20,c=gain.item(),cmap=cm.jet,vmax=-70,vmin=-150)
        ax.scatter(imageSize*BSloc[0],imageSize-imageSize*BSloc[1],marker='^', c='red')
        ax.plot([imageSize*BSloc[0],imageSize*UEloc[0]],[imageSize-imageSize*BSloc[1],imageSize-imageSize*UEloc[1]],'k--')
        ax.set_title(f'Area: {int(imageSize/scale/2)}*{int(imageSize/scale/2)} m2')
    plt.show()