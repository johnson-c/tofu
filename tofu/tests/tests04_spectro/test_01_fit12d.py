
"""
This module contains tests for tofu.geom in its structured version
"""

# Built-in
import os
import warnings

# Standard
import numpy as np
import scipy.constants as scpct
import matplotlib.pyplot as plt

# tofu-specific
from tofu import __version__
import tofu.spectro as tfs

_here = os.path.abspath(os.path.dirname(__file__))
VerbHead = 'tofu.spectro.fit12d'


#######################################################
#
#     Setup and Teardown
#
#######################################################


def setup_module(module):
    print("")   # this is to get a newline after the dots
    LF = os.listdir(_here)
    lss = ['TFD_', 'Test', '.npz']
    LF = [lf for lf in LF if all([ss in lf for ss in lss])]
    LF = [
        lf for lf in LF
        if not lf[lf.index('_Vv')+2:lf.index('_U')] == __version__
    ]
    print("Removing the following previous test files:")
    print(LF)
    for lf in LF:
        os.remove(os.path.join(_here, lf))
    # print("setup_module before anything in this file")


def teardown_module(module):
    # os.remove(VesTor.Id.SavePath + VesTor.Id.SaveName + '.npz')
    # os.remove(VesLin.Id.SavePath + VesLin.Id.SaveName + '.npz')
    # print("teardown_module after everything in this file")
    # print("") # this is to get a newline
    LF = os.listdir(_here)
    lss = ['TFD_', 'Test', '.npz']
    LF = [lf for lf in LF if all([ss in lf for ss in lss])]
    LF = [
        lf for lf in LF
        if lf[lf.index('_Vv')+2:lf.index('_U')] == __version__
    ]
    print("Removing the following test files:")
    print(LF)
    for lf in LF:
        os.remove(os.path.join(_here, lf))
    pass


# def my_setup_function():
#    print ("my_setup_function")

# def my_teardown_function():
#    print ("my_teardown_function")

# @with_setup(my_setup_function, my_teardown_function)
# def test_numbers_3_4():
#    print 'test_numbers_3_4  <============================ actual test code'
#    assert multiply(3,4) == 12

# @with_setup(my_setup_function, my_teardown_function)
# def test_strings_a_3():
#    print 'test_strings_a_3  <============================ actual test code'
#    assert multiply('a',3) == 'aaa'


#######################################################
#
#     Creating Ves objects and testing methods
#
#######################################################


class Test01_DataCollection(object):

    @classmethod
    def setup_class(cls):

        lamb = np.linspace(3.94, 4, 200)*1e-10
        var = np.linspace(-250, 250, 1001)

        def bck(lamb=None, offset=None, slope=None):
            return offset + (lamb-lamb.min())*slope/(lamb.max()-lamb.min())

        def gauss(lamb=None, lamb0=None, sigma=None, delta=None, amp=None):
            return amp * np.exp(-(lamb-lamb0-delta)**2/(2*sigma**2))

        def noise(lamb=None, amp=None, freq=None, phase=None):
            return amp*np.sin(
                lamb*freq*2.*np.pi/(lamb.max()-lamb.min()) + phase
            )

        dlines = {
            'a': {
                'lambda0': 3.95e-10,
                'delta': 0.001e-10,
                'sigma': 0.002e-10,
                'amp': 1.,
                'noise': 0.01,
                'group': 0,
            },
            'b': {
                'lambda0': 3.97e-10,
                'delta': -0.001e-10,
                'sigma': 0.0015e-10,
                'amp': 0.5,
                'noise': 0.001,
                'group': 1,
            },
            'c': {
                'lambda0': 3.975e-10,
                'delta': 0.001e-10,
                'sigma': 0.001e-10,
                'amp': 0.6,
                'noise': 0.005,
                'group': 0,
            },
            'd': {
                'lambda0': 3.99e-10,
                'delta': 0.002e-10,
                'sigma': 0.002e-10,
                'amp': 0.8,
                'noise': 0.01,
                'group': 1,
            },
        }

        spect2d = bck(
            lamb=lamb[:, None],
            offset=0.05*np.exp(-(var[None, :]-250)**2/100**2),
            slope=0.001,
        )
        spect2d += noise(lamb=lamb[:, None], amp=0.01, freq=10, phase=0.)

        for ii, k0 in enumerate(dlines.keys()):
            spect2d += gauss(
                lamb=lamb[:, None],
                amp=dlines[k0]['amp'] * np.exp(-var[None, :]**2/200**2),
                lamb0=dlines[k0]['lambda0'],
                sigma=dlines[k0]['sigma']*(
                    1 + 2*(ii/len(dlines))*np.cos(var[None, :]*2*np.pi/500)
                ),
                delta=dlines[k0]['delta']*(
                    1 + 2*(ii/len(dlines))*np.sin(
                        var[None, :]*2*np.pi*(len(dlines)-ii)/500
                    )
                ),
            )
            spect2d += noise(
                lamb=lamb[:, None],
                    amp=dlines[k0]['noise'] * np.exp(-var[None, :]**2/100**2),
                    freq=10*(len(dlines)-ii),
                    phase=ii,
                )

        # Plot spect 2d
        # fig = plt.figure(figsize=(6, 10));
        # ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        # ax.set_xlabel(r'$\lambda$ (m)')
        # ax.set_ylabel(r'$y$ (m)')
        # extent = (lamb.min(), lamb.max(), var.min(), var.max())
        # ax.imshow(spect2d.T, extent=extent, aspect='auto');
        # plt.show();
        # import pdb; pdb.set_trace()     # DB

        cls.lamb = lamb
        cls.var = var
        cls.dlines = dlines
        cls.spect2d = spect2d

    @classmethod
    def setup(self):
        pass

    def teardown(self):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def test01_fit1d_dinput(self):
        defconst={
            'amp': False,
            'width': False,
            'shift': False,
            'double': False,
            'symmetry': False,
        }

        # Define constraint dict 
        dconst0 = {
            'amp': {'a1': ['a', 'd']},
            'width': 'group',
            'shift': {
                'a': {'key': 's1', 'coef': 1., 'offset': 0.},
                'b': {'key': 's1', 'coef': 1., 'offset': 0.},
                'c': {'key': 's2', 'coef': 2., 'offset': 0.},
                'd': {'key': 's2', 'coef': 1., 'offset': 0.001e-10},
            },
            'double': True,
            'symmetry': True,
        }

        dconst1 = {
            'amp': False,
            'width': 'group',
            'shift': {
                'a': {'key': 's1', 'coef': 1., 'offset': 0.},
                'c': {'key': 's2', 'coef': 2., 'offset': 0.},
                'd': {'key': 's2', 'coef': 1., 'offset': 0.001e-10},
            },
            'double': False,
            'symmetry': False,
        }

        for dd in [dconst0, dconst1]:
            dinput = tfs.fit1d_dinput(
                dlines=self.dlines,
                dconstraints=dd,
                dprepare=None,
                data=self.spect2d[:, 200],
                lamb=self.lamb,
                mask=None,
                domain=None,
                pos=None,
                subset=None,
                same_spectrum=None,
                nspect=None,
                same_spectrum_dlamb=None,
                focus=None,
                valid_fraction=None,
                valid_nsigma=None,
                focus_half_width=None,
                valid_return_fract=None,
                dscales=None,
                dx0=None,
                dbounds=None,
                defconst=defconst,
            )


    def test02_fit1d(self):
        pass

    def test03_fit1d_dextract(self):
        pass






