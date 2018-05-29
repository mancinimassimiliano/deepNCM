'''Train CIFAR10 with PyTorch.'''
from __future__ import print_function

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import os
import networks
import numpy as np
import argparse

import visdom

from utils import progress_bar

vis = visdom.Visdom()

parser = argparse.ArgumentParser(description='PyTorch CIFAR10 Training')
parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
parser.add_argument('--resume', '-r', action='store_true', help='resume from checkpoint')
args = parser.parse_args()

device = 'cuda' if torch.cuda.is_available() else 'cpu'
best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch

# Data
print('==> Preparing data..')
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

# Model
print('==> Building model..')
net = networks.ResNet18_NCM()
net = net.to(device)
if device == 'cuda':
    net = net.cuda()
    cudnn.benchmark = True

if args.resume:
    # Load checkpoint.
    print('==> Resuming from checkpoint..')
    assert os.path.isdir('checkpoint'), 'Error: no checkpoint directory found!'
    checkpoint = torch.load('./checkpoint/ckpt.t7')
    net.load_state_dict(checkpoint['net'])
    best_acc = checkpoint['acc']
    start_epoch = checkpoint['epoch']

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(filter(lambda p: p.requires_grad, net.parameters()), lr=args.lr, momentum=0.9, weight_decay=5e-4)

# Training
def train(epoch):
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs= inputs.to(device)
        optimizer.zero_grad()
        outputs = net.forward(inputs)
	net.update_means(outputs,targets)
	prediction=net.predict(outputs)
	targets=targets.to(device)
        loss = criterion(prediction, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = prediction.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
	if batch_idx%10==0:
        	progress_bar(batch_idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
            % (train_loss/(batch_idx+1), 100.*correct/total, correct, total))
    return (train_loss/(batch_idx+1)), 100.*correct/total

def test(epoch):
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net.forward(inputs)
	    outputs=net.predict(outputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
	    if batch_idx%10==0:
		progress_bar(batch_idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
                % (test_loss/(batch_idx+1), 100.*correct/total, correct, total))

    # Save checkpoint.
    acc = 100.*correct/total
    return acc


def loop(epochs=200,dataset_name='ncm'):
	vis.env =dataset_name
	iters=[]
	losses_training=[]
	accuracy_training=[]
	accuracies_test=[]
	for name,param in net.named_parameters():
		if param.requires_grad:
			print(name)
	for epoch in range(start_epoch, start_epoch+epochs):

		# Perform 1 training epoch
		loss_epoch, acc_epoch = train(epoch)

		# Validate the model
		result = test(epoch)

		# Update lists (for visualization purposes)
		accuracies_test.append(result)
		accuracy_training.append(acc_epoch)
		losses_training.append(loss_epoch)
		iters.append(epoch)
	

		# Print results
		vis.line(
				X=np.array(iters),
				Y=np.array(losses_training),
		 		opts={
		        		'title': ' Training Loss ' + dataset_name,
		        		'xlabel': 'epochs',
		        		'ylabel': 'loss'},
		    			name='Training Loss '+ dataset_name,
		    		win=0)
		vis.line(
		    		X=np.array(iters),
		    		Y=np.array(accuracy_training),
		    		opts={
		        		'title': ' Training Accuracy '+ dataset_name,
		        		'xlabel': 'epochs',
		        		'ylabel': 'accuracy'},
		    			name='Training Accuracy '+ dataset_name,
		    		win=1)
		vis.line(
		    		X=np.array(iters),
		    		Y=np.array(accuracies_test),
		    		opts={
		        		'title': ' Accuracy '+ dataset_name,
		        		'xlabel': 'epochs',
		        		'ylabel': 'accuracy'},
		    			name='Validation Accuracy '+ dataset_name,
		    		win=2)


loop()