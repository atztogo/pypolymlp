#!/usr/bin/env python 
import numpy as np
import copy
from scipy.optimize import minimize

from pypolymlp.core.io_polymlp import load_mlp_lammps
from pypolymlp.utils.structure_utils import refine_positions
from pypolymlp.calculator.properties import Properties
from pypolymlp.calculator.str_opt.symmetry import (
    construct_basis_fractional_coordinates,
    basis_cell,
)


class MinimizeSym:
    
    def __init__(self, 
                 cell, 
                 relax_cell=False,
                 relax_positions=True,
                 pot=None, 
                 params_dict=None, 
                 coeffs=None):

        if pot is not None:
            params_dict, mlp_dict = load_mlp_lammps(filename=pot)
            coeffs = mlp_dict['coeffs'] / mlp_dict['scales']

        self.__relax_cell = relax_cell
        self.__relax_positions = relax_positions

        self.prop = Properties(params_dict=params_dict, coeffs=coeffs)

        self.__energy = None
        self.__force = None
        self.__stress = None
        self.__res = None

        if relax_cell:
            self.__basis_axis, self.st_dict = basis_cell(cell)
            if not np.allclose(cell['axis'], self.st_dict['axis']):
                print('- Input structure is standarized by spglib.')
        else:
            self.__basis_axis = None
            self.st_dict = cell

        self.__basis_f = None
        self.__split = 0
        if relax_positions:
            try:
                self.__basis_f \
                    = construct_basis_fractional_coordinates(self.st_dict)
                self.__split = self.__basis_f.shape[1]
            except:
                self.__relax_positions = False

        if self.__relax_cell == False and self.__relax_positions == False:
            raise ValueError('No degree of freedom to be optimized.')

        self.__positions_f0 = copy.deepcopy(self.st_dict['positions'])
        self.st_dict = self.set_structure(self.st_dict)
        self.__n_atom = len(self.st_dict['elements'])

    def set_structure(self, cell):

        self.st_dict = copy.deepcopy(cell)
        self.st_dict['axis_inv'] = np.linalg.inv(cell['axis'])
        self.st_dict['volume'] = np.linalg.det(cell['axis'])
        x0 = self.set_x0()
        return self.st_dict

    def set_x0(self):

        if self.__relax_cell:
            xs = self.__basis_axis.T @ self.st_dict['axis'].reshape(-1)
            if self.__relax_positions:
                xf = np.zeros(self.__basis_f.shape[1])
                self.__x0 = np.concatenate([xf, xs], 0)
            else:
                self.__x0 = xs
        else:
            if self.__relax_positions:
                self.__x0 = np.zeros(self.__basis_f.shape[1])
            else:
                raise ValueError('No degree of freedom to be optimized.')
        return self.__x0
 
    ''' no cell relaxation'''
    def fun_fix_cell(self, x, args=None):

        self.to_st_dict_fix_cell(x)
        self.__energy, self.__force, _ = self.prop.eval(self.st_dict)

        if self.__energy < -1e3 * self.__n_atom:
            print('Energy =', self.__energy)
            raise ValueError('Geometry optimization failed: '
                              'Huge negative energy value.')
 
        return self.__energy

    def jac_fix_cell(self, x, args=None):

        if self.__basis_f is not None:
            prod = - self.__force.T @ self.st_dict['axis']
            derivatives = self.__basis_f.T @ prod.reshape(-1)
            return derivatives
        return []

    def to_st_dict_fix_cell(self, x):

        if self.__basis_f is not None:
            disps_f = (self.__basis_f @ x).reshape(-1,3).T
            self.st_dict['positions'] = self.__positions_f0 + disps_f
        return self.st_dict

    ''' with cell relaxation'''
    def fun_relax_cell(self, x, args=None):

        self.to_st_dict_relax_cell(x)
        (self.__energy, 
         self.__force, 
         self.__stress) = self.prop.eval(self.st_dict)

        if self.__energy < -1e3 * self.__n_atom:
            print('Energy =', self.__energy)
            raise ValueError('Geometry optimization failed: '
                              'Huge negative energy value.')
        return self.__energy

    def jac_relax_cell(self, x, args=None):

        derivatives = np.zeros(len(x))
        if self.__relax_positions:
            derivatives[:self.__split] = self.jac_fix_cell(x)
        derivatives[self.__split:] = self.derivatives_by_axis()
        return derivatives

    def to_st_dict_relax_cell(self, x):

        x_positions, x_cells = x[:self.__split], x[self.__split:]

        axis = self.__basis_axis @ x_cells
        self.st_dict['axis'] = axis.reshape((3,3))
        self.st_dict['volume'] = np.linalg.det(self.st_dict['axis'])
        self.st_dict['axis_inv'] = np.linalg.inv(self.st_dict['axis'])

        if self.__relax_positions:
            self.st_dict = self.to_st_dict_fix_cell(x_positions)
        return self.st_dict

    def derivatives_by_axis(self):

        sigma = [[self.__stress[0], self.__stress[3], self.__stress[5]],
                 [self.__stress[3], self.__stress[1], self.__stress[4]],
                 [self.__stress[5], self.__stress[4], self.__stress[2]]]
        derivatives_s = - np.array(sigma) @ self.st_dict['axis_inv'].T

        '''derivatives_s: In the order of ax, bx, cx, ay, by, cy, az, bz, cz'''
        return self.__basis_axis.T @ derivatives_s.reshape(-1)

    def run(self, gtol=1e-4, method='BFGS'): 
        ''' 
        Parameters
        ----------
        method: CG, BFGS, or L-BFGS-B
        '''
        print('Using', method, 'method')
        options = {
            'gtol': gtol,
            'disp': True,
        }

        if self.__relax_cell:
            fun = self.fun_relax_cell
            jac = self.jac_relax_cell
        else:
            fun = self.fun_fix_cell
            jac = self.jac_fix_cell

        print('Number of degrees of freedom:', len(self.__x0))
        self.__res = minimize(fun, 
                              self.__x0, 
                              method=method,
                              jac=jac,
                              options=options)
        self.__x0 = self.__res.x
        return self

    @property
    def structure(self):
        self.st_dict = refine_positions(self.st_dict)
        return self.st_dict

    @property
    def energy(self):
        return self.__res.fun

    @property
    def n_iter(self):
        return self.__res.nit
    
    @property
    def success(self):
        return self.__res.success

    @property
    def residual_forces(self):
        if self.__relax_cell:
            residual_f = - self.__res.jac[:self.__split]
            residual_s = - self.__res.jac[self.__split:]
            return residual_f, residual_s
        return - self.__res.jac

    def print_structure(self):
        self.st_dict = refine_positions(self.st_dict)
        print('Axis basis vectors:')
        for a in self.st_dict['axis'].T:
            print(' -', list(a))
        print('Fractional coordinates:')
        for p, e in zip(self.st_dict['positions'].T, self.st_dict['elements']):
            print(' -', e, list(p))

   
if __name__ == '__main__':

    import argparse
    from pypolymlp.core.interface_vasp import Poscar

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--poscar', 
                        type=str, 
                        default=None,
                        help='poscar file')
    parser.add_argument('--pot', 
                        type=str, 
                        default='polymlp.lammps',
                        help='polymlp file')
    args = parser.parse_args()

    unitcell = Poscar(args.poscar).get_structure()

    print('Fixing cell parameters (symmetric constraints)')
    try:
        minobj = MinimizeSym(unitcell, pot=args.pot)
        minobj.run(gtol=1e-5)

        print('Residuals (force):')
        print(minobj.residual_forces.T)
        minobj.print_structure()
    except:
        print('Optimization has failed '
              'or No degree of freedom to be optimized.')

    print('---')
    print('Relaxing cell parameters')
    try:
        minobj = MinimizeSym(unitcell, pot=args.pot, relax_cell=True)
        print('Initial structure')
        minobj.print_structure()
        minobj.run(gtol=1e-5)

        res_f, res_s = minobj.residual_forces
        print('Residuals (force):')
        print(res_f.T)
        print('Residuals (stress):')
        print(res_s)
        print('Final structure')
        minobj.print_structure()
    except:
        print('Optimization has failed.')
