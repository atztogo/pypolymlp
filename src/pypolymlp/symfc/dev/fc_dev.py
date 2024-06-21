#!/usr/bin/env python
import time

import numpy as np
import phono3py
import phonopy
from phono3py.file_IO import write_fc2_to_hdf5, write_fc3_to_hdf5
from symfc import Symfc
from symfc.basis_sets.basis_sets_O2 import FCBasisSetO2
from symfc.solvers.solver_O2O3 import run_solver_O2O3_update
from symfc.spg_reps import SpgRepsO1
from symfc.utils.cutoff_tools_O3 import FCCutoffO3
from symfc.utils.matrix_tools_O3 import set_complement_sum_rules

from pypolymlp.calculator.properties import Properties
from pypolymlp.calculator.str_opt.optimization_sym import MinimizeSym
from pypolymlp.core.displacements import (
    generate_random_const_displacements,
    get_structures_from_displacements,
)
from pypolymlp.core.interface_phono3py_ver3 import parse_phono3py_yaml_fcs
from pypolymlp.utils.phonopy_utils import (
    phonopy_cell_to_st_dict,
    phonopy_supercell,
    st_dict_to_phonopy_cell,
)

"""symfc_basis_dev: must be included to FCBasisSetO3 in symfc"""
from pypolymlp.symfc.dev.symfc_basis_dev import run_basis, run_basis_fc2

# from symfc.solvers.solver_O2O3 import run_solver_O2O3_no_sum_rule_basis


def recover_fc2(coefs, compress_mat, compress_eigvecs, N):
    n_a = compress_mat.shape[0] // (9 * N)
    n_lp = N // n_a
    fc2 = compress_eigvecs @ coefs
    fc2 = (compress_mat @ fc2).reshape((n_a, N, 3, 3))
    fc2 /= np.sqrt(n_lp)
    return fc2


def recover_fc3(coefs, compress_mat, compress_eigvecs, N):
    n_a = compress_mat.shape[0] // (27 * (N**2))
    n_lp = N // n_a
    fc3 = compress_eigvecs @ coefs
    fc3 = (compress_mat @ fc3).reshape((n_a, N, N, 3, 3, 3))
    fc3 /= np.sqrt(n_lp)
    return fc3


def recover_fc3_variant(
    coefs,
    compress_mat,
    proj_pt,
    trans_perms,
    n_iter=10,
):
    """if using full compression_matrix
    fc3 = compress_eigvecs @ coefs
    fc3 = (compress_mat @ fc3).reshape((N,N,N,3,3,3))
    """
    n_lp, N = trans_perms.shape
    n_a = compress_mat.shape[0] // (27 * (N**2))

    fc3 = compress_mat @ coefs
    c_sum_cplmt = set_complement_sum_rules(trans_perms)

    for i in range(n_iter):
        fc3 -= c_sum_cplmt.T @ (c_sum_cplmt @ fc3)
        fc3 = proj_pt @ fc3

    fc3 = fc3.reshape((n_a, N, N, 3, 3, 3))
    fc3 /= np.sqrt(n_lp)
    return fc3


class PolymlpFC:

    def __init__(
        self,
        supercell=None,
        phono3py_yaml=None,
        use_phonon_dataset=False,
        pot=None,
        params_dict=None,
        coeffs=None,
        properties=None,
        cutoff=None,
    ):
        """
        Parameters
        ----------
        supercell: Supercell in phonopy format or structure dict
        pot, (params_dict and coeffs), or Properties object: polynomal MLP
        """

        if pot is None and params_dict is None and properties is None:
            self.prop = None
        else:
            if properties is not None:
                self.prop = properties
            else:
                self.prop = Properties(pot=pot, params_dict=params_dict, coeffs=coeffs)

        self.__initialize_supercell(
            supercell=supercell,
            phono3py_yaml=phono3py_yaml,
            use_phonon_dataset=use_phonon_dataset,
        )
        self.__fc2 = None
        self.__fc3 = None
        self.__disps = None
        self.__forces = None

        if cutoff is not None:
            self.cutoff = cutoff
        else:
            self.__cutoff = None
            self.__fc_cutoff = None

    def __initialize_supercell(
        self, supercell=None, phono3py_yaml=None, use_phonon_dataset=False
    ):

        if supercell is not None:
            if isinstance(supercell, dict):
                self.__supercell_dict = supercell
                self.__supercell_ph = st_dict_to_phonopy_cell(supercell)
            elif isinstance(supercell, phonopy.structure.cells.Supercell):
                self.__supercell_dict = phonopy_cell_to_st_dict(supercell)
                self.__supercell_ph = supercell
            else:
                raise ValueError(
                    "PolymlpFC: type(supercell) must be" " dict or phonopy supercell"
                )

        elif phono3py_yaml is not None:
            print("Supercell is read from:", phono3py_yaml)
            (self.__supercell_ph, self.__disps, self.__st_dicts) = (
                parse_phono3py_yaml_fcs(
                    phono3py_yaml, use_phonon_dataset=use_phonon_dataset
                )
            )
            self.__supercell_dict = phonopy_cell_to_st_dict(self.__supercell_ph)

        else:
            raise ValueError(
                "PolymlpFC: supercell or phonon3py_yaml"
                " is required for initialization"
            )

        self.__N = len(self.__supercell_ph.symbols)
        return self

    def sample(self, n_samples=100, displacements=0.001, is_plusminus=False):

        self.__disps, self.__st_dicts = generate_random_const_displacements(
            self.__supercell_dict,
            n_samples=n_samples,
            displacements=displacements,
            is_plusminus=is_plusminus,
        )
        return self

    def run_geometry_optimization(self, gtol=1e-5, method="CG"):

        print("Running geometry optimization")
        try:
            minobj = MinimizeSym(self.__supercell_dict, properties=self.prop)
        except ValueError:
            print("No geomerty optimization is performed.")
            return self

        minobj.run(gtol=gtol, method=method)
        print("Residual forces:")
        print(minobj.residual_forces.T)
        print("E0:", minobj.energy)
        print("n_iter:", minobj.n_iter)
        print("Fractional coordinate changes:")
        diff_positions = (
            self.__supercell_dict["positions"] - minobj.structure["positions"]
        )
        print(diff_positions.T)
        print("Success:", minobj.success)

        if minobj.success:
            self.__supercell_dict = minobj.structure
            self.__supercell_ph = st_dict_to_phonopy_cell(self.__supercell_dict)
            if self.__disps is not None:
                self.displacements = self.__disps

        return self

    def set_cutoff(self, cutoff=7.0):
        self.cutoff = cutoff
        return self

    def __compute_forces(self):

        _, forces, _ = self.prop.eval_multiple(self.__st_dicts)
        _, residual_forces, _ = self.prop.eval(self.__supercell_dict)
        for f in forces:
            f -= residual_forces
        return forces

    def run_fc2(self):

        symfc = Symfc(
            self.__supercell_ph,
            displacements=self.__disps.transpose((0, 2, 1)),
            forces=self.__forces.transpose((0, 2, 1)),
        ).run(orders=[2])
        self.__fc2 = symfc.force_constants[2]

        return self

    def run_fc2fc3(self, batch_size=100, sum_rule_basis=True):
        """
        disps: (n_str, 3, n_atom) --> (n_str, n_atom, 3)
        forces: (n_str, 3, n_atom) --> (n_str, n_atom, 3)
        """
        disps = self.__disps.transpose((0, 2, 1))
        forces = self.__forces.transpose((0, 2, 1))

        n_data, N, _ = forces.shape
        disps = disps.reshape((n_data, -1))
        forces = forces.reshape((n_data, -1))

        """ Constructing fc2 basis and fc3 basis """
        t1 = time.time()
        compress_mat_fc2, compress_eigvecs_fc2, atomic_decompr_idx_fc2 = run_basis_fc2(
            self.__supercell_ph,
            fc_cutoff=self.__fc_cutoff,
        )

        _ = FCBasisSetO2(self.__supercell_ph, use_mkl=False)
        """
        fc2_basis = FCBasisSetO2(self.__supercell_ph, use_mkl=False).run()
        compress_mat_fc2 = fc2_basis.compact_compression_matrix
        compress_eigvecs_fc2 = fc2_basis.basis_set
        """
        ta = time.time()
        print(" elapsed time (basis sets for fc2) =", "{:.3f}".format(ta - t1))
        print(compress_eigvecs_fc2.shape)

        if sum_rule_basis:
            compress_mat_fc3, compress_eigvecs_fc3, atomic_decompr_idx_fc3 = run_basis(
                self.__supercell_ph,
                fc_cutoff=self.__fc_cutoff,
                apply_sum_rule=True,
            )
        else:
            compress_mat_fc3, proj_pt, atomic_decompr_idx_fc3 = run_basis(
                self.__supercell_ph,
                fc_cutoff=self.__fc_cutoff,
                apply_sum_rule=False,
            )

        t2 = time.time()
        print(" elapsed time (basis sets for fc2 and fc3) =", "{:.3f}".format(t2 - t1))

        """Temporarily used. Better approach is desired to reduce memory assumption."""
        trans_perms = SpgRepsO1(self.__supercell_ph).translation_permutations

        print("----- Solving fc2 and fc3 using run_solver -----")
        t1 = time.time()
        use_mkl = False if N > 400 else True
        if sum_rule_basis:
            coefs_fc2, coefs_fc3 = run_solver_O2O3_update(
                disps,
                forces,
                compress_mat_fc2,
                compress_mat_fc3,
                compress_eigvecs_fc2,
                compress_eigvecs_fc3,
                trans_perms,
                atomic_decompr_idx_fc3=atomic_decompr_idx_fc3,
                use_mkl=use_mkl,
                batch_size=batch_size,
            )
            """
            from symfc.solvers.solver_O2O3 import run_solver_O2O3
            from symfc.utils.utils_O3 import dot_lat_trans_compr_matrix_O3

            # Bottleneck part of memory allocation
            compress_mat_fc3_full = dot_lat_trans_compr_matrix_O3(
                compress_mat_fc3,
                trans_perms,
            )
            coefs_fc2, coefs_fc3 = run_solver_O2O3(
                disps,
                forces,
                compress_mat_fc2_full,
                compress_mat_fc3_full,
                compress_eigvecs_fc2,
                compress_eigvecs_fc3,
                use_mkl=use_mkl,
                batch_size=batch_size,
            )
            """
        else:
            raise ValueError("sum_rule_basis=False is not available now.")
            """
            compress_mat_fc3_full = dot_lat_trans_compr_matrix_O3(
                compress_mat_fc3,
                trans_perms,
            )
            coefs_fc2, coefs_fc3 = run_solver_O2O3_no_sum_rule_basis(
                disps,
                forces,
                compress_mat_fc2_full,
                compress_mat_fc3_full,
                compress_eigvecs_fc2,
                use_mkl=use_mkl,
                batch_size=batch_size,
            )
            """
        t2 = time.time()
        print(" elapsed time (solve fc2 + fc3) =", "{:.3f}".format(t2 - t1))

        t1 = time.time()
        fc2 = recover_fc2(coefs_fc2, compress_mat_fc2, compress_eigvecs_fc2, self.__N)

        if sum_rule_basis:
            fc3 = recover_fc3(
                coefs_fc3, compress_mat_fc3, compress_eigvecs_fc3, self.__N
            )
        else:
            """
            print("Applying sum rules to fc3")
            fc3 = recover_fc3_variant(coefs_fc3, compress_mat_fc3, proj_pt, trans_perms)
            """

        t2 = time.time()
        print(" elapsed time (recover fc2 and fc3) =", "{:.3f}".format(t2 - t1))

        self.__fc2 = fc2
        self.__fc3 = fc3

        return self

    def run(
        self,
        disps=None,
        forces=None,
        batch_size=100,
        sum_rule_basis=True,
        write_fc=True,
        only_fc2=False,
    ):

        if disps is not None:
            self.displacements = disps

        if forces is None:
            print("Computing forces using polymlp")
            t1 = time.time()
            self.forces = np.array(self.__compute_forces())
            t2 = time.time()
            print(" elapsed time (computing forces) =", t2 - t1)
        else:
            self.forces = forces

        if only_fc2:
            self.run_fc2()
        else:
            self.run_fc2fc3(batch_size=batch_size, sum_rule_basis=sum_rule_basis)

        if write_fc:
            if self.__fc2 is not None:
                print("writing fc2.hdf5")
                write_fc2_to_hdf5(self.__fc2)
            if self.__fc3 is not None:
                print("writing fc3.hdf5")
                write_fc3_to_hdf5(self.__fc3)

        return self

    @property
    def displacements(self):
        return self.__disps

    @property
    def forces(self):
        return self.__forces

    @property
    def structures(self):
        return self.__st_dicts

    @displacements.setter
    def displacements(self, disps):
        """disps: Displacements (n_str, 3, n_atom)"""
        if not disps.shape[1] == 3 or not disps.shape[2] == self.__N:
            raise ValueError("displacements must have a shape of " "(n_str, 3, n_atom)")
        self.__disps = disps
        self.__st_dicts = get_structures_from_displacements(
            self.__disps, self.__supercell_dict
        )

    @forces.setter
    def forces(self, f):
        """forces: shape=(n_str, 3, n_atom)"""
        if not f.shape[1] == 3 or not f.shape[2] == self.__N:
            raise ValueError("forces must have a shape of " "(n_str, 3, n_atom)")
        self.__forces = f

    @structures.setter
    def structures(self, st_dicts):
        self.__st_dicts = st_dicts

    @property
    def fc2(self):
        return self.__fc2

    @property
    def fc3(self):
        return self.__fc3

    @property
    def supercell_phonopy(self):
        return self.__supercell_ph

    @property
    def supercell_dict(self):
        return self.__supercell_dict

    @property
    def cutoff(self):
        return self.__cutoff

    @cutoff.setter
    def cutoff(self, value):
        print("Cutoff radius:", value, "(ang.)")
        self.__cutoff = value
        self.__fc_cutoff = FCCutoffO3(self.__supercell_ph, cutoff=value)
        return self


if __name__ == "__main__":

    import argparse
    import signal

    from pypolymlp.core.interface_vasp import Poscar

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

    parser.add_argument("--pot", type=str, default=None, help="polymlp file")
    parser.add_argument(
        "--fc_n_samples",
        type=int,
        default=None,
        help="Number of random displacement samples",
    )
    parser.add_argument(
        "--disp",
        type=float,
        default=0.03,
        help="Displacement (in Angstrom)",
    )
    parser.add_argument(
        "--is_plusminus",
        action="store_true",
        help="Plus-minus displacements will be generated.",
    )
    parser.add_argument(
        "--geometry_optimization",
        action="store_true",
        help="Geometry optimization is performed " "for initial structure.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=100,
        help="Batch size for FC solver.",
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=None,
        help="Cutoff radius for setting zero elements.",
    )
    parser.add_argument("--run_ltc", action="store_true", help="Run LTC calculations")
    parser.add_argument(
        "--ltc_mesh",
        type=int,
        nargs=3,
        default=[19, 19, 19],
        help="k-mesh used for phono3py calculation",
    )
    args = parser.parse_args()

    unitcell_dict = Poscar(args.poscar).get_structure()
    supercell_matrix = np.diag(args.supercell)
    supercell = phonopy_supercell(unitcell_dict, supercell_matrix)

    polyfc = PolymlpFC(supercell=supercell, pot=args.pot, cutoff=args.cutoff)

    if args.fc_n_samples is not None:
        polyfc.sample(
            n_samples=args.fc_n_samples,
            displacements=args.disp,
            is_plusminus=args.is_plusminus,
        )

    if args.geometry_optimization:
        polyfc.run_geometry_optimization()

    polyfc.run(write_fc=True, batch_size=args.batch_size)

    if args.run_ltc:
        ph3 = phono3py.load(
            unitcell_filename=args.poscar,
            supercell_matrix=supercell_matrix,
            primitive_matrix="auto",
            log_level=1,
        )
        ph3.mesh_numbers = args.ltc_mesh
        ph3.init_phph_interaction()
        ph3.run_thermal_conductivity(temperatures=range(0, 1001, 10), write_kappa=True)
