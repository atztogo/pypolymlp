#!/usr/bin/env python 
import numpy as np
import copy

from scipy.optimize import minimize
from pypolymlp.core.io_polymlp import load_mlp_lammps
from pypolymlp.calculator.properties import Properties


class Minimize:
    
    def __init__(self, cell, pot=None, params_dict=None, coeffs=None):

        if pot is not None:
            params_dict, mlp_dict = load_mlp_lammps(filename=pot)
            coeffs = mlp_dict['coeffs'] / mlp_dict['scales']

        self.prop = Properties(params_dict=params_dict, coeffs=coeffs)
        self.st_dict = self.set_structure(cell)

        self.__energy = None
        self.__force = None
        self.__stress = None
        self.__relax_cell = False
        self.__res = None
        self.__n_atom = len(self.st_dict['elements'])

    def set_structure(self, cell):

        self.st_dict = copy.deepcopy(cell)
        self.st_dict['axis_inv'] = np.linalg.inv(cell['axis'])
        self.st_dict['volume'] = np.linalg.det(cell['axis'])
        return self.st_dict

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

        prod = - self.__force.T @ self.st_dict['axis']
        derivatives = prod.reshape(-1)
        return derivatives

    def to_st_dict_fix_cell(self, x):

        self.st_dict['positions'] = x.reshape((-1,3)).T
        return self.st_dict

    ''' with cell relaxation'''
    def fun_relax_cell(self, x, args=None):

        self.to_st_dict_relax_cell(x)
        (self.__energy, 
         self.__force, 
         self.__stress) = self.prop.eval(self.st_dict)

        if self.__energy < -1e8:
            print('Energy =', self.__energy)
            raise ValueError('Geometry optimization failed: '
                              'Huge negative energy value.')
        return self.__energy

    def jac_relax_cell(self, x, args=None):

        derivatives = np.zeros(len(x))
        derivatives[:-9] = self.jac_fix_cell(x)
        sigma = [[self.__stress[0], self.__stress[3], self.__stress[5]],
                 [self.__stress[3], self.__stress[1], self.__stress[4]],
                 [self.__stress[5], self.__stress[4], self.__stress[2]]]
        derivatives_s = - np.array(sigma) @ self.st_dict['axis_inv'].T
        derivatives[-9:] = derivatives_s.reshape(-1)
        return derivatives

    def to_st_dict_relax_cell(self, x):

        x_positions, x_cells = x[:-9], x[-9:]

        self.st_dict['axis'] = x_cells.reshape((3,3))
        self.st_dict['volume'] = np.linalg.det(self.st_dict['axis'])
        self.st_dict['axis_inv'] = np.linalg.inv(self.st_dict['axis'])
        self.st_dict['positions'] = x_positions.reshape((-1,3)).T
        return self.st_dict

    def run(self, relax_cell=False, gtol=1e-4, method='BFGS'): 
        ''' 
        Parameters
        ----------
        method: CG, BFGS, or L-BFGS-B
        '''
        print('Using', method, 'method')
        self.__relax_cell = relax_cell
        options = {
            'gtol': gtol,
            'disp': True,
        }

        if relax_cell:
            fun = self.fun_relax_cell
            jac = self.jac_relax_cell
            xf = self.st_dict['positions'].T.reshape(-1)
            xs = self.st_dict['axis'].reshape(-1)
            self.__x0 = np.concatenate([xf, xs], 0)
        else:
            fun = self.fun_fix_cell
            jac = self.jac_fix_cell
            self.__x0 = self.st_dict['positions'].T.reshape(-1)

        self.__res = minimize(fun, 
                              self.__x0, 
                              method=method,
                              jac=jac,
                              options=options)
        self.__x0 = self.__res.x
        return self

    @property
    def structure(self):
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
            residual_f = - self.__res.jac[:-9].reshape((-1,3)).T
            residual_s = - self.__res.jac[-9:].reshape((3,3))
            return residual_f, residual_s
        return - self.__res.jac.reshape((-1,3)).T

    def print_structure(self):
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

    print('Fixing cell parameters')
    try:
        minobj = Minimize(unitcell, pot=args.pot)
        minobj.run(gtol=1e-5)

        print(minobj.residual_forces.T)
        minobj.print_structure()
    except:
        print('Optimization has failed '
              'or No degree of freedom to be optimized.')

    print('---')
    print('Relaxing cell parameters')
    try:
        minobj = Minimize(unitcell, pot=args.pot)
        minobj.run(relax_cell=True, gtol=1e-5)

        res_f, res_s = minobj.residual_forces
        print('Residuals (force):')
        print(res_f.T)
        print('Residuals (stress):')
        print(res_s)
        minobj.print_structure()
    except:
        print('Optimization has failed ')
