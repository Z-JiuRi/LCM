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
from model import DoraNet
from dataset import DoraSet
from matplotlib import pyplot as plt

casesToTrain = 1 # 1 for los, 0 for nlos, -1 for all
epochs = 10 # total epochs
saveLossInterval = 1 # intervals to save loss
saveModelInterval = 1 # intervals to save model
batchSize = 500 # batchsize for training and evaluation
lr = 3e-4 # learning rate
cudaIdx = "cuda:0" # GPU card index
num_workers = 15 # workers for dataloader
evaluation = False # evaluation only if True
loadRUNcase = f'/runCase_{casesToTrain}/DoraNet_10.pth' # path of model to be loaded if evalution is True

def run(isTrain, data_loader, model, criterion, optimizer, epoch, device, imageSize):
    model.train() if isTrain else model.eval()
    setStr = 'Train' if isTrain else 'Valid' 
    losses = Recoder()
    Acc = Recoder()
    for i, (envImg, distances, channels, BSloc, UEloc, sights, scale, angles, gains) in enumerate(data_loader):
        cases = (sights[:,0]==casesToTrain) if casesToTrain>-1 else (sights[:,0]>casesToTrain)
        batch_size = channels.shape[0]
        UEloc = UEloc.to(device)
        p_UEloc = model(gains,channels,scale,BSloc,envImg,sights,angles,distances,device)        
        loss = criterion(p_UEloc[cases], UEloc[cases])
        if isTrain:
            backward(optimizer,loss)
        offset = torch.mean(((p_UEloc[cases,0]-UEloc[cases,0])**2+(p_UEloc[cases,1]-UEloc[cases,1])**2)**0.5*(imageSize/scale[cases,0].to(device)*0.5))        
        losses.update(loss.item(), batch_size)
        Acc.update(offset.item(), batch_size)
        print(f'{setStr} Epoch: [{epoch}][{i}/{len(data_loader)}] ---- loss {loss.item():.4f} ---- offset {offset.item():.2f} meters')        
    return Acc.avg(), toNP(envImg[cases]), toNP(p_UEloc[cases]), toNP(UEloc[cases]), toNP(BSloc[cases])

def showResults(envImg, p_UEloc, UEloc, BSloc, batchIdx, imageSize):
    fig, ax = plt.subplots()
    ax.imshow(1-envImg[batchIdx,0,:,:], cmap='gray')
    ax.scatter(imageSize*BSloc[batchIdx,0],imageSize-imageSize*BSloc[batchIdx,1],marker='^', c='red',label='BS location')
    ax.scatter(imageSize*UEloc[batchIdx,0],imageSize-imageSize*UEloc[batchIdx,1], marker='o', c='blue',label='real UE location')
    ax.scatter(imageSize*p_UEloc[batchIdx,0],imageSize-imageSize*p_UEloc[batchIdx,1], marker='o', c='green',label='predicted UE location')
    ax.legend()
    plt.show()
        
def main():
    seed_everything(42)
    valid_dataset = DoraSet(cases=100, start=900, set='valid')    
    valid_loader = torch.utils.data.DataLoader(valid_dataset, batch_size=batchSize, shuffle=False, num_workers=num_workers)
    imageSize = valid_dataset.imageSize
    device = torch.device(cudaIdx if torch.cuda.is_available() else "cpu")    
    model = DoraNet().to(device) 
    criterion = torch.nn.MSELoss().to(device)
    Valid = []
    if not evaluation:
        train_dataset=DoraSet(cases=900, start=0, set='train')
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batchSize, shuffle=True, num_workers=num_workers)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        Train = []
        runCase = f'runCase_{casesToTrain}'
        makeDIRs(runCase)        
    else:
        model.load_state_dict(torch.load(f'models{loadRUNcase}'))
        optimizer = []
        
    for epoch in range(1,epochs+1): 
        with torch.no_grad():
            lossV, envImg, p_UEloc, UEloc, BSloc = run(False, valid_loader, model, criterion, [], epoch, device, imageSize)
        Valid.append(lossV)
        if (not evaluation):
            lossT, _, _, _, _ = run(True, train_loader, model, criterion, optimizer, epoch, device, imageSize)
            Train.append(lossT)
            checkPoint(runCase,epoch,epochs,model,Train,Valid,saveModelInterval,saveLossInterval)
        else:
            break
                   
    showResults(envImg, p_UEloc, UEloc, BSloc, 0, imageSize)
    
if __name__ == '__main__':
    main()