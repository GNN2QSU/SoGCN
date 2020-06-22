import torch
import torch.nn as nn
import torch.nn.functional as F

from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score
import numpy as np

import dgl.function as fn


def MAE(scores, targets):
    MAE = F.l1_loss(scores, targets)
    return MAE


def accuracy_TU(scores, targets):
    scores = scores.detach().argmax(dim=1)
    acc = (scores==targets).float().sum().item()
    return acc


def accuracy_MNIST_CIFAR(scores, targets):
    scores = scores.detach().argmax(dim=1)
    acc = (scores==targets).float().sum().item()
    return acc

def accuracy_CITATION_GRAPH(scores, targets):
    scores = scores.detach().argmax(dim=1)
    acc = (scores==targets).float().sum().item()
    acc = acc / len(targets)
    return acc


def accuracy_SBM(scores, targets):
    S = targets.cpu().numpy()
    C = np.argmax( torch.nn.Softmax(dim=1)(scores).cpu().detach().numpy() , axis=1 )
    CM = confusion_matrix(S,C).astype(np.float32)
    nb_classes = CM.shape[0]
    targets = targets.cpu().detach().numpy()
    nb_non_empty_classes = 0
    pr_classes = np.zeros(nb_classes)
    for r in range(nb_classes):
        cluster = np.where(targets==r)[0]
        if cluster.shape[0] != 0:
            pr_classes[r] = CM[r,r]/ float(cluster.shape[0])
            if CM[r,r]>0:
                nb_non_empty_classes += 1
        else:
            pr_classes[r] = 0.0
    acc = 100.* np.sum(pr_classes)/ float(nb_non_empty_classes)
    return acc


def binary_f1_score(scores, targets):
    """Computes the F1 score using scikit-learn for binary class labels. 
    
    Returns the F1 score for the positive class, i.e. labelled '1'.
    """
    y_true = targets.cpu().numpy()
    y_pred = scores.argmax(dim=1).cpu().numpy()
    return f1_score(y_true, y_pred, average='binary')

  
def accuracy_VOC(scores, targets):
    scores = scores.detach().argmax(dim=1).cpu()
    targets = targets.cpu().detach().numpy()
    acc = f1_score(scores, targets, average='weighted')
    return acc



class Smoothness:
    msg = fn.copy_src(src='h', out='m')
    
    def reduce(nodes):
        h = nodes.data['h'].detach()
        m = nodes.mailbox['m'].detach()
        L = nodes.mailbox['m'].shape[0]
        dist = torch.zeros(L)

        for i in range(L):
            n_h = F.normalize(h[i, :], p=2, dim=0)
            n_m = F.normalize(m[i, :, :], p=2, dim=1)

            D = 1 - torch.matmul(n_m, n_h)
            N = (torch.abs(D - 0) > 1e-10000).float().sum(dim=0)
            if N == 0:
                dist[i] = 0
            else:
                dist[i] = torch.sum(D, dim=0) / N
        
        return {'d': dist}

    
    @classmethod
    def MAD(self, g, h):
        g = g.local_var()
        g.ndata['h'] = h
        g.update_all(self.msg, self.reduce)

        d = g.ndata['d']
        N = (torch.abs(d - 0) > 1e-10000).float().sum(dim=0)
        if N == 0:
            return 0.0
        
        return torch.sum(d, dim=0) / N


