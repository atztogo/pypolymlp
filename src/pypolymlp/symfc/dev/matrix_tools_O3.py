#!/usr/bin/env python
import numpy as np
import scipy
from scipy.sparse import csr_array
from symfc.utils.eig_tools import dot_product_sparse
from symfc.utils.solver_funcs import get_batch_slice
from symfc.utils.utils_O3 import get_atomic_lat_trans_decompr_indices_O3


def compressed_complement_projector_sum_rules_from_compact_compr_mat(
    trans_perms,
    n_a_compress_mat: csr_array,
    atomic_decompr_idx=None,
    use_mkl: bool = False,
    n_batch=None,
) -> csr_array:
    """Calculate a complementary projector for sum rules.

    This is compressed by C_trans and n_a_compress_mat without
    allocating C_trans.
    Memory efficient version using get_atomic_lat_trans_decompr_indices_O3.

    Return
    ------
    Compressed projector
    P^(c) = n_a_compress_mat.T @ C_trans.T @ C_sum^(c)
            @ C_sum^(c).T @ C_trans @ n_a_compress_mat
    """
    n_lp, natom = trans_perms.shape
    NNN27 = natom**3 * 27
    NNN = natom**3
    NN = natom**2

    proj_size = n_a_compress_mat.shape[1]
    proj_sum_cplmt = csr_array((proj_size, proj_size), dtype="double")

    if atomic_decompr_idx is None:
        atomic_decompr_idx = get_atomic_lat_trans_decompr_indices_O3(trans_perms)

    decompr_idx = atomic_decompr_idx.reshape((natom, NN)).T.reshape(-1) * 27

    if n_batch is None:
        if natom < 256:
            n_batch = natom // min(natom, 16)
        else:
            n_batch = natom // 4

    if n_batch > natom:
        raise ValueError("n_batch must be smaller than N.")

    batch_size = natom**2 * (natom // n_batch)
    for begin, end in zip(*get_batch_slice(NNN, batch_size)):
        print("Complementary P (Sum rule):", str(end) + "/" + str(NNN))
        size = end - begin
        size_vector = size * 27
        size_matrix = size_vector // natom

        c_sum_cplmt = csr_array(
            (
                np.ones(size_vector, dtype="double"),
                (
                    np.repeat(np.arange(size_matrix), natom),
                    (decompr_idx[begin:end][None, :] + np.arange(27)[:, None]).reshape(
                        -1
                    ),
                ),
            ),
            shape=(size_matrix, NNN27 // n_lp),
            dtype="double",
        )
        c_sum_cplmt = dot_product_sparse(c_sum_cplmt, n_a_compress_mat, use_mkl=use_mkl)
        proj_sum_cplmt += dot_product_sparse(
            c_sum_cplmt.T, c_sum_cplmt, use_mkl=use_mkl
        )

    proj_sum_cplmt /= n_lp * natom
    return proj_sum_cplmt


def compressed_projector_sum_rules_from_compact_compr_mat_lowmem(
    trans_perms,
    n_a_compress_mat: csr_array,
    atomic_decompr_idx=None,
    use_mkl: bool = False,
) -> csr_array:
    """Return projection matrix for sum rule.

    This is compressed by C_compr = C_trans @ n_a_compress_mat.
    """
    proj_cplmt = compressed_complement_projector_sum_rules_from_compact_compr_mat(
        trans_perms,
        n_a_compress_mat,
        use_mkl=use_mkl,
        atomic_decompr_idx=atomic_decompr_idx,
    )
    return scipy.sparse.identity(proj_cplmt.shape[0]) - proj_cplmt
