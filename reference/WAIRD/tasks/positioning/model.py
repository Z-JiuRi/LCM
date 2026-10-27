'''
Copyright (C) 2021. Huawei Technologies Co., Ltd.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
'''

import torch
from torch import nn
import numpy as np

class DoraNet(nn.Module):
    def __init__(self):
        super(DoraNet, self).__init__()
        self.mlp = nn.Sequential(
                nn.Linear(5,256),
                nn.ReLU(),
                nn.Linear(256,1024),
                nn.ReLU(),
                nn.Linear(1024,256),
                nn.ReLU(),
                nn.Linear(256,2),
                nn.Sigmoid()
                )
                
    def forward(self, gains, channels, scale, BSloc, envImg, sights, angles, distances, device):
        inputInfo = torch.cat([distances, BSloc, angles],axis=1)
        out = self.mlp(inputInfo.to(device))
        return out
        
def main():    
    b = 10
    doraNet = DoraNet()    
    gains = torch.zeros((b,1))
    channels = torch.zeros((b,2,64,64))
    scale = torch.zeros((b,1))
    BSloc = torch.zeros((b,2))
    envImg = torch.zeros((b,1,64,64))
    sights = torch.zeros((b,1))
    angles = torch.zeros((b,2))
    distances = torch.zeros((b,1))
    UEloc = torch.zeros((b,2))
    device = torch.device("cpu")
    p_UEloc = doraNet(gains, channels, scale, BSloc, envImg, sights, angles, distances, device)
    print(torch.mean(torch.abs(p_UEloc-UEloc)))
        
if __name__ == '__main__':
    main()