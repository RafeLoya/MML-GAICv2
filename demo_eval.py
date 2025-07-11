from croppingModel import build_crop_model
from croppingDataset import setup_test_dataset
import os
import torch
import cv2
from torch.autograd import Variable
import torch.backends.cudnn as cudnn
import torch.utils.data as data
import argparse
import time

#NEW
import json

import torch.multiprocessing
torch.multiprocessing.set_sharing_strategy('file_system')

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

parser = argparse.ArgumentParser(
    description='Grid anchor based image cropping With Pytorch')
parser.add_argument('--input_dir', default='dataset/GAIC/images/test',
                    help='root directory path of testing images')
parser.add_argument('--output_dir', default='dataset/test_result',
                    help='root directory path of testing images')
parser.add_argument('--batch_size', default=1, type=int,
                    help='Batch size for training')
parser.add_argument('--num_workers', default=0, type=int,
                    help='Number of workers used in dataloading')
parser.add_argument('--cuda', default=True, type=str2bool,
                    help='Use CUDA to train model')
parser.add_argument('--net_path', default='pretrained_model/mobilenet_0.682_0.643_0.613_0.585_0.844_0.827_0.807_0.787_0.849_0.874.pth',
                    help='Directory for saving checkpoint models')
args = parser.parse_args()

if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)

if torch.cuda.is_available():
    if args.cuda:
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
    if not args.cuda:
        print("WARNING: It looks like you have a CUDA device, but aren't " +
              "using CUDA.\nRun with --cuda for optimal training speed.")
        torch.set_default_tensor_type('torch.FloatTensor')
else:
    torch.set_default_tensor_type('torch.FloatTensor')

dataset = setup_test_dataset(dataset_dir = args.input_dir)

def naive_collate(batch):
    return batch[0]

def output_file_name(input_path, idx):
    name = os.path.basename(input_path)
    segs = name.split('.')
    assert len(segs) >= 2
    return '%scrop_%d.%s'%('.'.join(segs[:-1]), idx, segs[-1])

def test():
    for epoch in range(0,1):

        net = build_crop_model(scale='multi',#scale='single', 
                               alignsize=9, reddim=8, loadweight=False, model='mobilenetv2',downsample=4)
        #net.load_state_dict(torch.load(args.net_path))
        net.load_state_dict(torch.load(args.net_path, weights_only=False))
        net.eval()

        if args.cuda:
            net = torch.nn.DataParallel(net,device_ids=[0])
            cudnn.benchmark = True
            net = net.cuda()

        data_loader = data.DataLoader(dataset, args.batch_size,
                                      num_workers=args.num_workers,
                                      collate_fn=naive_collate,
                                      shuffle=False)

        for id, sample in enumerate(data_loader):
            imgpath = sample['imgpath']
            image = sample['image']
            bboxes = sample['sourceboxes']
            resized_image = sample['resized_image']
            tbboxes = sample['tbboxes']

            if len(tbboxes['xmin'])==0:
                continue

            roi = []

            for idx in range(0,len(tbboxes['xmin'])):
                roi.append((0, tbboxes['xmin'][idx],tbboxes['ymin'][idx],tbboxes['xmax'][idx],tbboxes['ymax'][idx]))           

            resized_image = torch.unsqueeze(torch.as_tensor(resized_image), 0)
            if args.cuda:
                resized_image = Variable(resized_image.cuda())
                roi = Variable(torch.Tensor(roi))
            else:
                resized_image = Variable(resized_image)
                roi = Variable(torch.Tensor(roi))

            t0 = time.time()
            out = net(resized_image,roi)
            t1 = time.time()
            print('timer: %.4f sec.' % (t1 - t0))
            id_out = sorted(range(len(out)), key=lambda k: out[k], reverse = True)

            #NEW
            all_crops_info = {
                'image_path': imgpath,
                'candidates': []
            }

            for i, (box, score) in enumerate(zip(bboxes, out)):
                all_crops_info['candidates'].append({
                    'original_i': i,
                    'coordinates': {'y1': int(box[0]), 'x1': int(box[1]),
                                    'y2': int(box[2]), 'x2': int(box[3])},
                    'score': float(score)
                })

            all_crops_info['candidates'].sort(key=lambda x: x['score'], reverse=True)
           
            for rank, candidate in enumerate(all_crops_info['candidates']):
                candidate['rank'] = rank

            imgname = imgpath.split('/')[-1]
            #json_filename = imgname[:4] + '_crop_info.json'
            base_name = imgname.rsplit('.', 1)[0]
            json_filename = '.' + base_name + '.json'
            #json_filename = '.' + imgname.split(imgname)[0] + '.json'
            json_path = os.path.join(args.output_dir, json_filename)

            with open(json_path, 'w') as f:
                json.dump(all_crops_info, f, indent=2)
                
            print(f"Saved crop info to: {json_path}")
            #NEW

            for id in range(0,1):
                top_box = bboxes[id_out[id]]
                top_crop = image[int(top_box[0]):int(top_box[2]),int(top_box[1]):int(top_box[3])]
                imgname = imgpath[0].split('/')[-1]
                cv2.imwrite(os.path.join(args.output_dir, 
                                         output_file_name(imgpath, id+1)),
                            top_crop[:,:,(2, 1, 0)])


if __name__ == '__main__':
    test()
