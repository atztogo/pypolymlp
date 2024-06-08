#!/usr/bin/env python
import argparse
import gc
import signal

import numpy as np

from pypolymlp.core.interface_vasp import Poscar
from pypolymlp.utils.phonopy_utils import phonopy_supercell

"""
from pypolymlp.calculator.compute_fcs import recover_fc2, recover_fc3
from symfc.basis_sets.basis_sets_O2 import FCBasisSetO2
from symfc.basis_sets.basis_sets_O3 import FCBasisSetO3
from symfc.solvers.solver_O2O3 import run_solver_sparse_O2O3
"""

import time

from symfc.basis_sets.basis_sets_O3 import print_sp_matrix_size
from symfc.spg_reps import SpgRepsO3
from symfc.utils.eig_tools import (
    dot_product_sparse,
    eigsh_projector,
    eigsh_projector_sumrule,
)

# from utils_O3_dev import get_compr_coset_reps_sum_O3
from symfc.utils.matrix_tools_O3 import (
    compressed_projector_sum_rules_from_compact_compr_mat,
    projector_permutation_lat_trans,
)
from symfc.utils.utils_O3 import get_compr_coset_reps_sum_O3


def permutation_dot_lat_trans_stable(trans_perms):

    from symfc.utils.matrix_tools_O3 import get_perm_compr_matrix_O3
    from symfc.utils.utils_O3 import get_lat_trans_compr_matrix_O3

    n_lp, N = trans_perms.shape
    c_trans = get_lat_trans_compr_matrix_O3(trans_perms)
    print_sp_matrix_size(c_trans, " C_(trans):")

    c_perm = get_perm_compr_matrix_O3(N)
    print_sp_matrix_size(c_perm, " C_(perm):")

    c_pt = c_perm.T @ c_trans
    return c_pt


def run_basis(supercell, apply_sum_rule=True):

    t00 = time.time()

    """space group representations"""
    spg_reps = SpgRepsO3(supercell)
    trans_perms = spg_reps.translation_permutations
    n_lp, N = trans_perms.shape
    print_sp_matrix_size(trans_perms, " trans_perms:")
    t01 = time.time()

    """permutation @ lattice translation"""
    """
    #c_pt = permutation_dot_lat_trans_stable(trans_perms)
    c_pt = permutation_dot_lat_trans(trans_perms)
    print_sp_matrix_size(c_pt, " C_perm.T @ C_trans:")
    t02 = time.time()

    proj_pt = dot_product_sparse(c_pt.T, c_pt, use_mkl=True)
    """
    proj_pt = projector_permutation_lat_trans(trans_perms, use_mkl=True)
    print_sp_matrix_size(proj_pt, " P_(perm,trans):")
    t02 = time.time()

    c_pt = eigsh_projector(proj_pt)
    #    del proj_pt
    #    gc.collect()

    print_sp_matrix_size(c_pt, " C_(perm,trans):")
    t03 = time.time()

    coset_reps_sum = get_compr_coset_reps_sum_O3(spg_reps)
    print_sp_matrix_size(coset_reps_sum, " R_(coset):")
    t04 = time.time()

    proj_rpt = c_pt.T @ coset_reps_sum @ c_pt
    del coset_reps_sum
    gc.collect()

    c_rpt = eigsh_projector(proj_rpt)
    del proj_rpt
    gc.collect()

    print_sp_matrix_size(c_rpt, " C_(perm,trans,coset):")
    t05 = time.time()

    n_a_compress_mat = dot_product_sparse(c_pt, c_rpt, use_mkl=True)
    print_sp_matrix_size(n_a_compress_mat, " C_(n_a_compr):")

    t06 = time.time()

    if apply_sum_rule:
        proj = compressed_projector_sum_rules_from_compact_compr_mat(
            trans_perms, n_a_compress_mat, use_mkl=True
        )
        print_sp_matrix_size(proj, " P_(perm,trans,coset,sum):")
        t07 = time.time()

        eigvecs = eigsh_projector_sumrule(proj)
        t08 = time.time()

    print("-----")
    print("Time (spg. rep.)                        =", t01 - t00)
    print("Time (proj(perm @ lattice trans.)       =", t02 - t01)
    print("Time (eigh(perm @ ltrans))              =", t03 - t02)
    print("Time (coset)                            =", t04 - t03)
    print("Time (eigh(coset @ perm @ ltrans))      =", t05 - t04)
    print("Time (c_pt @ c_rpt)                     =", t06 - t05)

    if apply_sum_rule:
        print("Time (proj(coset @ perm @ ltrans @ sum) =", t07 - t06)
        print("Time (eigh(coset @ perm @ ltrans @ sum) =", t08 - t07)
        print("Basis size =", eigvecs.shape)
        return n_a_compress_mat, eigvecs

    print("Basis size =", n_a_compress_mat.shape)
    return n_a_compress_mat, proj_pt


if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = argparse.ArgumentParser()
    parser.add_argument("--poscar", type=str, default=None, help="poscar")
    parser.add_argument(
        "--supercell",
        nargs=3,
        type=int,
        default=None,
        help="Supercell size (diagonal components)",
    )
    args = parser.parse_args()

    unitcell_dict = Poscar(args.poscar).get_structure()
    supercell_matrix = np.diag(args.supercell)

    supercell = phonopy_supercell(unitcell_dict, supercell_matrix)

    t1 = time.time()
    n_a_compress_mat, eigvecs = run_basis(supercell)
    # n_a_compress_mat = run_basis(supercell, apply_sum_rule=False)
    t2 = time.time()
    print("Elapsed time (basis sets for fc2 and fc3) =", t2 - t1)