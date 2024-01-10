#!/usr/bin/env python
import numpy as np
import sys, os, glob
import shutil

def set_dataset(dft_dict):

    e_all = dft_dict['energy'] / dft_dict['total_n_atoms']
    vol_all = dft_dict['volumes'] / dft_dict['total_n_atoms']

    f_std_all = []
    begin = 0
    for n in dft_dict['total_n_atoms']:
        end = begin + 3 * n
        f_std_all.append(np.std(dft_dict['force'][begin:end]))
        begin = end
    f_std_all = np.array(f_std_all)

    return e_all, f_std_all, vol_all

def set_threshold_energy(e_all, eth=None, e_ratio=0.25):
    if eth is None:
        eth_from_min = np.std(e_all) * e_ratio
        eth = np.min(e_all) + eth_from_min
    return eth

def set_threshold_force(f_std_all, fth=None, f_ratio=1.0):
    if fth is None:
        fth = np.average(f_std_all) * f_ratio
    return fth

def set_threshold_volume(vol_all, volth=None, vol_ratio=2.0):
    if volth is None:
        volth = np.average(vol_all) * vol_ratio
    return volth

def split_train_test(data):
    test = data[9::10]
    train = np.array(sorted(set(data) - set(test)))
    return train, test

def split_two_datasets(dft_dict, 
                       eth=None, fth=None, volth=None,
                       e_ratio=0.25, f_ratio=1.0, vol_ratio=2.0):

    e_all, f_std_all, vol_all = set_dataset(dft_dict)
    eth = set_threshold_energy(e_all, eth=eth, e_ratio=e_ratio)
    fth = set_threshold_force(f_std_all, fth=fth, f_ratio=f_ratio)
    volth = set_threshold_volume(vol_all, volth=volth, vol_ratio=vol_ratio)

    print(' energy threshold: ', eth)
    print(' force threshold:  ', fth)
    print(' volume threshold: ', volth)

    set_all = set(list(range(len(e_all))))

    set_e = set(np.where(e_all <= eth)[0])
    set_f = set(np.where(f_std_all <= fth)[0])
    set_v = set(np.where(vol_all <= volth)[0])

    set1 = set_e & set_f & set_v
    set2 = np.array(list(set_all - set1))
    set1 = np.array(list(set1))

    train1, test1 = split_train_test(set1)
    train2, test2 = split_train_test(set2)
    return train1, train2, test1, test2

def split_three_datasets(dft_dict, 
                         eth=None, fth=None, volth=None,
                         e_ratio=0.25, f_ratio=1.0, vol_ratio=2.0):

    e_all, f_std_all, vol_all = set_dataset(dft_dict)
    eth = set_threshold_energy(e_all, eth=eth, e_ratio=e_ratio)
    fth = set_threshold_force(f_std_all, fth=fth, f_ratio=f_ratio)
    volth = set_threshold_volume(vol_all, volth=volth, vol_ratio=vol_ratio)

    print(' energy threshold: ', eth)
    print(' force threshold:  ', fth)
    print(' volume threshold: ', volth)

    set_all = set(list(range(len(e_all))))

    set0 = set(np.where(e_all > 0)[0])
    set_e = set(np.where(e_all <= eth)[0])
    set_e = set_e - set0

    set_f = set(np.where(f_std_all <= fth)[0])
    set_v = set(np.where(vol_all <= volth)[0])

    set1 = set_e & set_f & set_v
    set2 = np.array(list(set_all - set1 - set0))
    set0, set1 = np.array(list(set0)), np.array(list(set1))

    train0, test0 = split_train_test(set0)
    train1, test1 = split_train_test(set1)
    train2, test2 = split_train_test(set2)
    return train0, train1, train2, test0, test1, test2

def copy_vaspruns(vaspruns, tag):

    dir_output = 'vaspruns/' + tag + '/'
    os.makedirs('vaspruns/' + tag, exist_ok=True)

    f = open(dir_output + 'dataset_auto_div.yaml', 'w')
    print('datasets:', file=f)
    print('- dataset_id:', tag, file=f)
    print('  structures:', file=f)
    for id1, infile in enumerate(vaspruns):
        print('  - id:', id1, file=f)
        print('    file:', infile, file=f)

        outfile = 'vaspruns-' + str(id1).zfill(5) + '.xml'
        shutil.copyfile(infile, dir_output + outfile)
    f.close()

