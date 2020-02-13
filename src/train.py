## _tkinter.TclError: no display name and no $DISPLAY environment variable
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys, time, argparse, os, re
import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from tensorflow.contrib.layers import l2_regularizer
from tensorflow.contrib.layers import batch_norm
import tensorflow.contrib.slim as slim
import tqdm
from scipy.stats.stats import pearsonr

_VALIDATION_RATIO = 0.1

from model import MEDGAN, MEDWGAN, MEDBGAN

def parse_arguments(parser):
    parser.add_argument('--model', type=str, default='medGAN', help='Specify the model name (medGAN, medWGAN, etc.). A dedicated folder will be created to save all models and outputs for this model (default value: medGAN)')
    parser.add_argument('--embed_size', type=int, default=128, help='The dimension size of the embedding, which will be generated by the generator. (default value: 128)')
    parser.add_argument('--noise_size', type=int, default=128, help='The dimension size of the random noise, on which the generator is conditioned. (default value: 128)')
    parser.add_argument('--generator_size', type=tuple, default=(128, 128), help='The dimension size of the generator. Note that another layer of size "--embed_size" is always added. (default value: (128, 128))')
    parser.add_argument('--discriminator_size', type=tuple, default=(256, 128, 1), help='The dimension size of the discriminator. (default value: (256, 128, 1))')
    parser.add_argument('--compressor_size', type=tuple, default=(), help='The dimension size of the encoder of the autoencoder. Note that another layer of size "--embed_size" is always added. Therefore this can be a blank tuple. (default value: ())')
    parser.add_argument('--decompressor_size', type=tuple, default=(), help='The dimension size of the decoder of the autoencoder. Note that another layer, whose size is equal to the dimension of the <patient_matrix>, is always added. Therefore this can be a blank tuple. (default value: ())')
    parser.add_argument('--data_type', type=str, default='binary', choices=['binary', 'count'], help='The input data type. The <patient matrix> could either contain binary values or count values. (default value: "binary")')
    parser.add_argument('--batchnorm_decay', type=float, default=0.99, help='Decay value for the moving average used in Batch Normalization. (default value: 0.99)')
    parser.add_argument('--L2', type=float, default=0.001, help='L2 regularization coefficient for all weights. (default value: 0.001)')
    parser.add_argument('--gp_scale', type=float, default=10.0, help='Gradient penalty scale used in WGAN (default value: 10.0)')
    parser.add_argument('--data_file', type=str, default='data/inpatient_final_data.npy', help='The path to the numpy matrix containing aggregated patient records.')
    parser.add_argument('--out_name', type=str, default='generated.npy', help='The file name of the generating data.')
    parser.add_argument('--init_from', type=str, default=None, help='Continue training from saved model in the "models" sub-folder in this folder. If None, train from scratch. (default value: None)')
    parser.add_argument('--n_pretrain_epoch', type=int, default=100, help='The number of epochs to pre-train the autoencoder. (default value: 100)')
    parser.add_argument('--n_epoch', type=int, default=1000, help='The number of epochs to train medGAN. (default value: 1000)')
    parser.add_argument('--n_discriminator_update', type=int, default=2, help='The number of times to update the discriminator per epoch. (default value: 2)')
    parser.add_argument('--n_generator_update', type=int, default=1, help='The number of times to update the generator per epoch. (default value: 1)')
    parser.add_argument('--pretrain_batch_size', type=int, default=100, help='The size of a single mini-batch for pre-training the autoencoder. (default value: 100)')
    parser.add_argument('--batch_size', type=int, default=1000, help='The size of a single mini-batch for training medGAN. (default value: 1000)')
    parser.add_argument('--save_max_keep', type=int, default=0, help='The number of models to keep. Setting this to 0 will save models for every epoch. (default value: 0)')
    parser.add_argument('--data_set', type=str, default='mimic', help='The name of dataset folder in results')

    args = parser.parse_args()
    return args
    ## for jupyter notebook
    # args = parser.parse_known_args()
    # return args[0]

parser = argparse.ArgumentParser()
args = parse_arguments(parser)

# Pre-load training data
train_data = np.load(args.data_file, allow_pickle = True)

# Training GAN
tf.reset_default_graph()
with tf.Session() as sess:
    # Parse the GAN type from args.model
    if re.search('medWGAN', args.model):
        mg = MEDWGAN(sess,
                     model_name=args.model,
                     dataType=args.data_type,
                     inputDim=train_data.shape[1],
                     compressDims=args.compressor_size,
                     decompressDims=args.decompressor_size,
                     bnDecay=args.batchnorm_decay,
                     l2scale=args.L2,
                     gp_scale=args.gp_scale,
                     dataset=args.data_set)
    elif re.search('medBGAN', args.model):
        mg = MEDBGAN(sess,
                     model_name=args.model,
                     dataType=args.data_type,
                     inputDim=train_data.shape[1],
                     compressDims=args.compressor_size,
                     decompressDims=args.decompressor_size,
                     bnDecay=args.batchnorm_decay,
                     l2scale=args.L2,
                     dataset=args.data_set)
    else:
        mg = MEDGAN(sess,
                    model_name=args.model,
                    dataType=args.data_type,
                    inputDim=train_data.shape[1],
                    compressDims=args.compressor_size,
                    decompressDims=args.decompressor_size,
                    bnDecay=args.batchnorm_decay,
                    l2scale=args.L2,
                    dataset=args.data_set)
    mg.build_model()
    results = mg.train(data_path=args.data_file,
                       pretrainEpochs=args.n_pretrain_epoch,
                       nEpochs=args.n_epoch,
                       discriminatorTrainPeriod=args.n_discriminator_update,
                       generatorTrainPeriod=args.n_generator_update,
                       pretrainBatchSize=args.pretrain_batch_size,
                       batchSize=args.batch_size,
                       saveMaxKeep=args.save_max_keep)

# Generate synthetic data
tf.reset_default_graph()
with tf.Session() as sess:
    # Parse the GAN type from args.model
    if re.search('medWGAN', args.model):
        mg = MEDWGAN(sess,
                     model_name=args.model,
                     dataType=args.data_type,
                     inputDim=train_data.shape[1],
                     compressDims=args.compressor_size,
                     decompressDims=args.decompressor_size,
                     bnDecay=args.batchnorm_decay,
                     l2scale=args.L2,
                     gp_scale=args.gp_scale)
    elif re.search('medBGAN', args.model):
        mg = MEDBGAN(sess,
                     model_name=args.model,
                     dataType=args.data_type,
                     inputDim=train_data.shape[1],
                     compressDims=args.compressor_size,
                     decompressDims=args.decompressor_size,
                     bnDecay=args.batchnorm_decay,
                     l2scale=args.L2)
    else:
        mg = MEDGAN(sess,
                    model_name=args.model,
                    dataType=args.data_type,
                    inputDim=train_data.shape[1],
                    compressDims=args.compressor_size,
                    decompressDims=args.decompressor_size,
                    bnDecay=args.batchnorm_decay,
                    l2scale=args.L2)
    mg.build_model()
    save_chk = os.path.join("../results", args.model, args.data_type)
    mg.generateData(nSamples=train_data.shape[0],
                    gen_from=save_chk,
                    out_name='generated.npy',
                    batchSize=args.batch_size)



