import torch
import torch.nn as nn
import torchvision
from torch.utils.data import DataLoader
import torch.optim as optim
from torch.optim import lr_scheduler
import argparse
import os
import cv2
from torchvision import datasets, models, transforms
from network.classifier import *
from network.transform import mesonet_data_transforms
import os
from tqdm import tqdm


def main():
	args = parse.parse_args()
	name = args.name
	train_path = args.train_path
	val_path = args.val_path
	continue_train = args.continue_train
	epoches = args.epoches
	batch_size = args.batch_size
	model_name = args.model_name
	model_path = args.model_path
	# change

	train_path=os.path.join(os.getcwd(),train_path)

	if not os.path.exists(train_path):
		raise FileNotFoundError(f"Train path not found: {train_path}")
	
	val_path=os.path.join(os.getcwd(),val_path)

	if not os.path.exists(train_path):
		raise FileNotFoundError(f"Train path not found: {val_path}")

	print("Paths verified successfully!")
	#
	output_path = os.path.join('MesoNet-Pytorch\output', name)
	if not os.path.exists(output_path):
		os.mkdir(output_path)
	torch.backends.cudnn.benchmark=True

	#creat train and val dataloader
	train_dataset = torchvision.datasets.ImageFolder(train_path, transform=mesonet_data_transforms['train'])
	val_dataset = torchvision.datasets.ImageFolder(val_path, transform=mesonet_data_transforms['val'])
	train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False, num_workers=8)
	val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=True, drop_last=False, num_workers=8)
	train_dataset_size = len(train_dataset)
	val_dataset_size = len(val_dataset)


	#for id, (image, labels) in enumerate(val_loader):

		#print(id,image,labels)


	#Creat the model
	device = torch.device("cpu")

	model = Meso4()
	if continue_train:
		model.load_state_dict(torch.load(model_path))
	model = model.to(device)
	#model.cuda()
	criterion = nn.CrossEntropyLoss()
	#optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9, weight_decay=0.001)
	optimizer = optim.Adam(model.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-08)
	scheduler = lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

	#Train the model using multiple GPUs
	#model = nn.DataParallel(model)

	best_model_wts = model.state_dict()
	best_acc = 0.0
	iteration = 0
	for epoch in tqdm(range(epoches)):
		print('Epoch {}/{}'.format(epoch+1, epoches))
		print('-'*10)
		model=model.train()
		train_loss = 0.0
		train_corrects = 0.0
		val_loss = 0.0
		val_corrects = 0.0
		for (image, labels) in train_loader:
			iter_loss = 0.0
			iter_corrects = 0.0
			image = image.to(device)
			labels = labels.to(device)
			#image = image.cuda()
			#labels = labels.cuda()
			optimizer.zero_grad()
			outputs = model(image)
			_, preds = torch.max(outputs.data, 1)
			loss = criterion(outputs, labels)
			loss.backward()
			optimizer.step()
			iter_loss = loss.data.item()
			train_loss += iter_loss
			iter_corrects = torch.sum(preds == labels.data).to(torch.float32)
			train_corrects += iter_corrects
			iteration += 1
			if not (iteration % 20):
				print('iteration {} train loss: {:.4f} Acc: {:.4f}'.format(iteration, iter_loss / batch_size, iter_corrects / batch_size))
		epoch_loss = train_loss / train_dataset_size
		epoch_acc = train_corrects / train_dataset_size
		print('epoch train loss: {:.4f} Acc: {:.4f}'.format(epoch_loss, epoch_acc))

		model.eval()
		with torch.no_grad():
			for (image, labels) in val_loader:
				image = image.to(device)
				labels = labels.to(device)
				#image = image.cuda()
				#labels = labels.cuda()
				outputs = model(image)
				_, preds = torch.max(outputs.data, 1)
				loss = criterion(outputs, labels)
				val_loss += loss.data.item()
				val_corrects += torch.sum(preds == labels.data).to(torch.float32)
			epoch_loss = val_loss / val_dataset_size
			epoch_acc = val_corrects / val_dataset_size
			print('epoch val loss: {:.4f} Acc: {:.4f}'.format(epoch_loss, epoch_acc))
			if epoch_acc > best_acc:
				best_acc = epoch_acc
				best_model_wts = model.state_dict()
		scheduler.step()
		if not (epoch % 10):
		#Save the model trained with multiple gpu
		#torch.save(model.module.state_dict(), os.path.join(output_path, str(epoch) + '_' + model_name))
			torch.save(model.state_dict(), os.path.join(output_path, str(epoch) + '_' + model_name))
	print('Best val Acc: {:.4f}'.format(best_acc))
	model.load_state_dict(best_model_wts)
	#torch.save(model.module.state_dict(), os.path.join(output_path, "best.pkl"))
	torch.save(model.state_dict(), os.path.join(output_path, "best.pkl"))



if __name__ == '__main__':
	parse = argparse.ArgumentParser(
		formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parse.add_argument('--name', '-n', type=str, default='Mesonet')
	parse.add_argument('--train_path', '-tp' , type=str, default = './deepfake_database/train')
	parse.add_argument('--val_path', '-vp' , type=str, default = './deepfake_database/val')
	parse.add_argument('--batch_size', '-bz', type=int, default=64)
	parse.add_argument('--epoches', '-e', type=int, default='50')
	parse.add_argument('--model_name', '-mn', type=str, default='meso4.pkl')
	parse.add_argument('--continue_train', type=bool, default=False)
	parse.add_argument('--model_path', '-mp', type=str, default='./output/Mesonet/best.pkl')
	main()