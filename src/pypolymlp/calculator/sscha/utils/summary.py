#!/usr/bin/env python
import numpy as np
import glob

from pypolymlp.calculator.sscha.sscha_io import Restart

def write_yaml(data):

    f = open('sscha_free_energy.yaml', 'w')
    print('equilibrium:', file=f)
    sortid = data[:,0].argsort()
    for d in data[sortid]:
        print('- temperature:', d[0], file=f)
        print('  free_energy:', d[1], file=f)
        print('', file=f)

    f.close()

if __name__ == '__main__':

    yml_files = sorted(glob.glob('./sscha/*/sscha_results.yaml'))

    free_energies = []
    for yml in yml_files:
        res = Restart(yml, unit='eV/atom')
        f_sum = res.free_energy + res.static_potential
        free_energies.append([res.temperature, f_sum])
    free_energies = np.array(free_energies)

    write_yaml(free_energies)
    
