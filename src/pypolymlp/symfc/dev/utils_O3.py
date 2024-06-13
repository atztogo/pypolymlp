#!/usr/bin/env python
import numpy as np
from scipy.sparse import csr_array, kron
from symfc.spg_reps import SpgRepsO3
from symfc.utils.utils import get_indep_atoms_by_lat_trans
from symfc.utils.utils_O3 import get_atomic_lat_trans_decompr_indices_O3

from pypolymlp.symfc.dev.zero_tools_O3 import FCCutoffO3


def get_atomic_lat_trans_decompr_indices_sparse_O3(
    trans_perms: np.ndarray, fc_cutoff: FCCutoffO3
) -> np.ndarray:
    """Return indices to de-compress compressed matrix by atom-lat-trans-sym.

    This is atomic permutation only version of get_lat_trans_decompr_indices.

    Usage
    -----
    vec[indices] of shape (n_a*N*N,) gives an array of shape=(N**3,).
    1/sqrt(n_lp) must be multiplied manually after decompression.

    Parameters
    ----------
    trans_perms : ndarray
        Permutation of atomic indices by lattice translational symmetry.
        dtype='intc'.
        shape=(n_l, N), where n_l and N are the numbers of lattce points and
        atoms in supercell.

    Returns
    -------
    indices : ndarray
        Indices of n_a * N * N elements.
        shape=(N**3,), dtype='int_'.

    """
    indep_atoms = get_indep_atoms_by_lat_trans(trans_perms)
    n_lp, N = trans_perms.shape
    size_row = N**3

    n = 0
    indices = np.ones(size_row, dtype="int_") * -1
    for i_patom in indep_atoms:
        index_shift_i = trans_perms[:, i_patom] * N**2
        for j in range(N):
            index_shift_j = index_shift_i + trans_perms[:, j] * N
            for k in range(N):
                index_shift = index_shift_j + trans_perms[:, k]
                indices[index_shift] = n
                n += 1

    for i_patom in indep_atoms:
        index_shift_i = trans_perms[:, i_patom] * N**2
        for j in fc_cutoff.outsides[i_patom]:
            index_shift_j = index_shift_i + trans_perms[:, j] * N
            for k in fc_cutoff.outsides[i_patom]:
                index_shift = index_shift_j + trans_perms[:, k]
                indices[index_shift] = -1

    return indices


def get_compr_coset_reps_sum_sparse_O3(
    spg_reps: SpgRepsO3,
    fc_cutoff: FCCutoffO3,
    c_pt: csr_array,
) -> csr_array:
    """Return projection matrix of sum of coset reps compressed by c_pt."""
    trans_perms = spg_reps.translation_permutations
    n_lp, N = trans_perms.shape
    size = c_pt.shape[1]
    proj_rpt = csr_array(([], ([], [])), shape=(size, size), dtype="double")

    """Todo: Better interface"""
    atomic_decompr_idx = get_atomic_lat_trans_decompr_indices_sparse_O3(
        trans_perms, fc_cutoff
    )
    match = np.where(atomic_decompr_idx != -1)[0]
    col_vec = atomic_decompr_idx[match]
    data_vec = np.ones(len(match), dtype=int)

    C = csr_array(
        (data_vec, (match, col_vec)),
        shape=(N**3, N**3 // n_lp),
    )

    factor = 1 / n_lp / len(spg_reps.unique_rotation_indices)
    for i, _ in enumerate(spg_reps.unique_rotation_indices):
        print(
            "Coset sum:", str(i + 1) + "/" + str(len(spg_reps.unique_rotation_indices))
        )
        """This part is equivalent to mat = C.T @ spg_reps.get_sigma3_rep(i) @ C"""
        row, col = spg_reps.get_sigma3_rep_nonzero(i)
        permutation = np.zeros(len(row), dtype=int)
        permutation[col] = row

        mat = csr_array(
            (data_vec, (permutation[match], col_vec)),
            shape=(N**3, N**3 // n_lp),
        )
        mat = C.T @ mat
        mat = kron(mat, spg_reps.r_reps[i] * factor)
        proj_rpt += c_pt.T @ mat @ c_pt

    return proj_rpt


def get_compr_coset_reps_sum_O3(spg_reps: SpgRepsO3) -> csr_array:
    """Return compr matrix of sum of coset reps."""
    trans_perms = spg_reps.translation_permutations
    n_lp, N = trans_perms.shape
    size = N**3 * 27 // n_lp
    coset_reps_sum = csr_array(([], ([], [])), shape=(size, size), dtype="double")
    atomic_decompr_idx = get_atomic_lat_trans_decompr_indices_O3(trans_perms)
    C = csr_array(
        (
            np.ones(N**3, dtype=int),
            (np.arange(N**3, dtype=int), atomic_decompr_idx),
        ),
        shape=(N**3, N**3 // n_lp),
    )
    factor = 1 / n_lp / len(spg_reps.unique_rotation_indices)
    for i, _ in enumerate(spg_reps.unique_rotation_indices):
        print(
            "Coset sum:", str(i + 1) + "/" + str(len(spg_reps.unique_rotation_indices))
        )
        """This part is equivalent to mat = C.T @ spg_reps.get_sigma3_rep(i) @ C"""
        row, col = spg_reps.get_sigma3_rep_nonzero(i)
        permutation = np.zeros(len(row), dtype=int)
        permutation[col] = row

        mat = csr_array(
            (np.ones(N**3, dtype=int), (permutation, atomic_decompr_idx)),
            shape=(N**3, N**3 // n_lp),
        )
        mat = C.T @ mat
        coset_reps_sum += kron(mat, spg_reps.r_reps[i] * factor)

    return coset_reps_sum
