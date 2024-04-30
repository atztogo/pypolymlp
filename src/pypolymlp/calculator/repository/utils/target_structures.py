#!/usr/bin/env python
import numpy as np
import os

from pypolymlp.core.interface_vasp import Vasprun


def get_structure_list_alloy2(system, dir_DFT):

    structure_list = {
        'MoNi4(D1a)(x=0.20)':   ['107998-01', 10, [2,2,2]],
        'MoNi4(D1a)(x=0.80)':   ['107998-10', 10, [2,2,2]],
        'Ni3Sn(D019)(x=0.25)':  ['104506-10', 16, [2,2,2]],
        'Ni3Sn(D019)(x=0.75)':  ['104506-01', 16, [2,2,2]],
        'Ni3Ti(D024)(x=0.25)':  ['649037-10', 16, [2,2,2]],
        'Ni3Ti(D024)(x=0.75)':  ['649037-01', 16, [2,2,2]],
        'AuCu3(L12)(x=0.25)':   ['181127-01', 4, [4,4,4]],
        'AuCu3(L12)(x=0.75)':   ['181127-10', 4, [4,4,4]],
        'Al3Zr(D023)(x=0.25)':  ['416747-10', 16, [2,2,2]],
        'Al3Zr(D023)(x=0.75)':  ['416747-01', 16, [2,2,2]],
        'Al3Ti(D022)(x=0.25)':  ['105191-10', 8, [2,2,2]],
        'Al3Ti(D022)(x=0.75)':  ['105191-01', 8, [2,2,2]],
        'AlCu2Mn(L21)(x=0.25)': ['188260-01', 16, [2,2,2]],
        'AlCu2Mn(L21)(x=0.75)': ['188260-10', 16, [2,2,2]],
        'InNi2(B82)(x=0.33)':   ['105948-10', 6, [2,2,2]],
        'InNi2(B82)(x=0.67)':   ['105948-01', 6, [2,2,2]],
        'Fe2P(C22)(x=0.33)':    ['611176-10', 18, [2,2,2]],
        'Fe2P(C22)(x=0.67)':    ['611176-01', 18, [2,2,2]],
        'CrSi2(C40)(x=0.33)':   ['16504-10', 9, [2,2,2]],
        'CrSi2(C40)(x=0.67)':   ['16504-01', 9, [2,2,2]],
        'Cu2Sb(C38)(x=0.33)':   ['610464-01', 6, [2,2,2]],
        'Cu2Sb(C38)(x=0.67)':   ['610464-10', 6, [2,2,2]],
        'MgZn2(C14)(x=0.33)':   ['625334-10', 12, [2,2,2]],
        'MgZn2(C14)(x=0.67)':   ['625334-01', 12, [2,2,2]],
        'Si2U3(D5a)(x=0.40)':   ['639227-01', 10, [2,2,2]],
        'Si2U3(D5a)(x=0.60)':   ['639227-10', 10, [2,2,2]],
        'AuCu(L10)(x=0.50)':    ['59508-01', 2, [4,4,4]],
        'CoU(Ba)(x=0.50)':      ['102712-01', 16, [2,2,2]],
        'CsCl(B2)(x=0.50)':     ['650527-01', 2, [4,4,4]],
        'NiAs(B81)(x=0.50)':    ['626692-01', 4, [4,4,4]],
        'WC(Bh)(x=0.50)':       ['644708-01', 2, [4,4,4]],
        'FeSi(B20)(x=0.50)':    ['635060-01', 8, [2,2,2]],
        'NaTl(B32)(x=0.50)':    ['103775-01', 16, [2,2,2]],
    }

    structure_dict = dict()
    for st, (code, n_atom, sup) in structure_list.items():
        vasprun = dir_DFT + '/' + str(code) + '/vasprun.xml'
        if os.path.exists(vasprun):
            st_dict = Vasprun(vasprun).get_structure()
            structure_dict[st] = {
                'icsd_id': code,
                'n_atom': n_atom,
                'phonon_supercell': sup,
                'structure': st_dict,
            }

    return structure_dict


def get_structure_list_element1(elements, dir_DFT):

    if len(set(elements) & set(['Te'])) > 0:
        structure_list = {
            'sc':        [43211, 1, [4,4,4]],
            'diamond':   [41979, 8, [4,4,4]],
            'P(black)':  [609832, 8, [6,2,4]],
            'As':        [616526, 3, [4,4,4]],
            'Sb(mP4)':   [42679, 4, [4,4,4]],
            'Sn':        [236662, 4, [4,4,4]],
            'Bi':        [653719, 4, [4,4,4]],
            'Se(gamma)': [653045, 3, [4,4,4]],
            'Te3':       [653048, 3, [4,4,4]],
        }
    elif len(set(elements) & set(['As','Sb','P'])) > 0:
        structure_list = {
            'sc':        [43211, 1, [4,4,4]],
            'diamond':   [41979, 8, [4,4,4]],
            'P(black)':  [609832, 8, [6,2,4]],
            'As':        [616526, 3, [4,4,4]],
            'Sb(mP4)':   [42679, 4, [4,4,4]],
            'Se(gamma)': [653045, 3, [4,4,4]],
            'Bi':        [653719, 4, [4,4,4]],
        }
    elif len(set(elements) & set(['Bi'])) > 0:
        structure_list = {
            'fcc':       [52914, 4, [4,4,4]],
            'bcc':       [76156, 2, [4,4,4]],
            'hcp':       [652876, 2, [4,4,4]],
            'sc':        [43211, 1, [4,4,4]],
            'diamond':   [41979, 8, [4,4,4]],
            'P(black)':  [609832, 8, [6,2,4]],
            'As':        [616526, 3, [4,4,4]],
            'Sb(mP4)':   [42679, 4, [4,4,4]],
            'Se(gamma)': [653045, 3, [4,4,4]],
            'Bi':        [653719, 4, [4,4,4]],
        }
    elif len(set(elements) & set(['Ga','In','Tl'])) > 0:
        structure_list = {
            'fcc':      [52914, 4, [4,4,4]],
            'bcc':      [76156, 2, [4,4,4]],
            'hcp':      [652876, 2, [4,4,4]],
            'sc':       [43211, 1, [4,4,4]],
            'diamond':  [41979, 8, [4,4,4]],
            'Ga':       [162256, 8, [4,4,4]],
            'Ga(Cmcm)': [43539, 4, [6,2,6]],
            'In':       [639810, 2, [4,4,4]],
            'Sn':       [236662, 4, [4,4,4]],
            'Sn(tI2)':  [43216, 2, [4,4,4]],
        }
    elif len(set(elements) & set(['Si','Ge','Sn','Pb'])) > 0:
        structure_list = {
            'fcc':       [52914, 4, [4,4,4]],
            'bcc':       [76156, 2, [4,4,4]],
            'hcp':       [652876, 2, [4,4,4]],
            'sc':        [43211, 1, [4,4,4]],
            'diamond':   [41979, 8, [4,4,4]],
            'Ga':        [162256, 8, [4,4,4]],
            'In':        [639810, 2, [4,4,4]],
            'Sn':        [236662, 4, [4,4,4]],
            'Sn(tI2)':   [43216, 2, [4,4,4]],
            'Si(I4mmm)': [181908, 8, [4,4,4]],
        }
    elif len(set(elements) & set(['Ti','Ba'])) > 0:
        structure_list = {
            'Sn(tI2)': [43216, 2, [4,4,4]],
            'Sn':      [236662, 4, [4,4,4]],
            'Sm':      [652633, 9, [6,6,1]],
            'La':      [52916, 4, [6,6,2]],
            'sc':      [43211, 1, [4,4,4]],
            'fcc':     [52914, 4, [4,4,4]],
            'bcc':     [76156, 2, [4,4,4]],
            'hcp':     [652876, 2, [4,4,4]],
        }
    else:
        structure_list = {
            'Sn(tI2)': [43216, 2, [4,4,4]],
            'Sn':      [236662, 4, [4,4,4]],
            'Bi':      [653719, 4, [4,4,4]],
            'Sm':      [652633, 9, [6,6,1]],
            'La':      [52916, 4, [6,6,2]],
            'diamond': [41979, 8, [4,4,4]],
            'sc':      [43211, 1, [4,4,4]],
            'fcc':     [52914, 4, [4,4,4]],
            'bcc':     [76156, 2, [4,4,4]],
            'hcp':     [652876, 2, [4,4,4]],
        }

    structure_dict = dict()
    for st, (code, n_atom, sup) in structure_list.items():
        vasprun = dir_DFT + '/' + str(code) + '/vasprun.xml'
        if os.path.exists(vasprun):
            st_dict = Vasprun(vasprun).get_structure()
            structure_dict[st] = {
                'icsd_id': code,
                'n_atom': n_atom,
                'phonon_supercell': sup,
                'structure': st_dict,
            }

    return structure_dict

