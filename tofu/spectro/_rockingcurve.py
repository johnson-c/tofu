

# Built-in
import sys
import os
import warnings
import copy

# Common
import numpy as np
import scipy.interpolate
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.axes._axes import Axes
from mpl_toolkits.mplot3d import Axes3D

# tofu
from tofu.version import __version__


# ##########################################################
# ##########################################################
#            compute rocking curve
# ##########################################################
# ##########################################################


def compute_rockingcurve(self,
    ih=None, ik=None, il=None, lamb=None,
    plot_asf=None, plot_power_ratio=None,
    verb=None, returnas=None,
):
    """The code evaluates, for a given wavelength, the atomic plane distance d,
    the Bragg angle, the complex structure factor, the integrated reflectivity
    with the perfect and mosaic crystal models, the reflectivity curve with the
    full dynamical model for parallel and perpendicular photon polarizations.

    The alpha-Quartz, symmetry group D(4,3), is assumed left-handed.
    It makes a difference for certain planes, for example between
    (h,k,l)=(2,0,3) and (2,0,-3).
    The alpha-Quartz structure is hexagonal with 3 molecules of SiO2 in the
    unit cell.

    All crystal lattice constants and wavelengths are in Angstroms (1e-10 m).

    Parameters:
    -----------
    ih, ik, il:    int
        Miller indices of crystal used
    lamb:    float
        Wavelength of interest, in Angstroms (1e-10 m)
    plot_asf:    str
        Plotting the atomic scattering factor thanks to data with respect to
        sin(theta)/lambda
    plot_power_ratio:    str
        Plot the power ratio with respect to the glancing angle
    verb:    str
        True or False to print the content of the results dictionnary 'dout'
    returnas:    str
        Entry 'dict' to allow optionnal returning of 'dout' dictionnary
    """

    # Check inputs
    # ------------

    if plot_asf is None:
        plot_asf = False
    if plot_power_ratio is None:
        plot_power_ratio = True
    if verb is None:
        verb = True
    if returnas is None:
        returnas = None

    ih, ik, il, lamb = CrystBragg_check_inputs_rockingcurve(
        ih=ih, ik=ik, il=il, lamb=lamb,
    )

    # Calculations of main crystal parameters
    # ---------------------------------------

    # Classical electronical radius, in Angstroms
    re = 2.82084508e-5

    # From Ralph W.G. Wyckoff, "Crystal Structures" (1948)
    # https://babel.hathitrust.org/cgi/pt?id=mdp.39015081138136&view=1up&seq=259&skin=2021
    # Inter-atomic distances into hexagonal cell unit (page 239 & 242) and
    # calculation of the associated volume
    # TBC with Francesca
    a0 = 4.9130
    c0 = 5.4045
    V = a0**2.*c0*np.sqrt(3.)/2.

    # Atomic number of Si and O atoms
    Zsi = 14.
    Zo = 8.

    # Position of the three Si atoms in the unit cell (page 242 Wyckoff)
    u = 0.4705
    xsi = np.r_[-u, u, 0.]
    ysi = np.r_[-u, 0., u]
    zsi = np.r_[1./3., 0., 2./3.]

    # Position of the six O atoms in the unit cell (page 242 Wyckoff)
    x = 0.4152
    y = 0.2678
    z = 0.1184
    xo = np.r_[x, y-x, -y, x-y, y, -x]
    yo = np.r_[y, -x, x-y, -y, x, y-x]
    zo = np.r_[z, z+1./3., z+2./3., -z, 2./3.-z, 1./3.-z]

    # Bragg angle and atomic plane distance d for a given wavelength lamb and
    # Miller index (h,k,l)
    d_num = np.sqrt(3.)*a0*c0
    d_den = np.sqrt(4.*(ih**2 + ik**2 + ih*ik)*c0**2 + 3.*il**2*a0**2)
    if d_den == 0.:
        msg = (
            "Something went wrong in the calculation of d, equal to 0!\n"
            "Please verify the values for the following Miller indices:\n"
            + "\t - h: first Miller index ({})\n".format(ih)
            + "\t - k: second Miller index ({})\n".format(ik)
            + "\t - l: third Miller index ({})\n".format(il)
        )
        raise Exception(msg)
    d_atom = d_num/d_den
    if d_atom < lamb/2.:
        msg = (
            "According to Bragg law, Bragg scattering need d > lamb/2!\n"
            "Please check your wavelength arg.\n"
        )
        raise Exception(msg)
    sol = 1./(2.*d_atom)
    sin_theta = lamb/(2.*d_atom)
    theta = np.arcsin(sin_theta)
    theta_deg = theta*180./np.pi
    lc = [theta_deg < 10., theta_deg > 89.]
    if any(lc):
        msg = (
            "The computed value of theta is behind the arbitrary limits.\n"
            "Limit condition: 10° < theta < 89° and\n"
            "theta = ({})°\n".format(theta_deg)
        )
        raise Exception(msg)

    # Atomic scattering factors ["asf"] for Si(2+) and O(1-) as a function of
    # sol = sin(theta)/lambda ["sol_values"], taking into account molecular
    # bounds
    # From Henry & Lonsdale, "International tables for Crystallography" (1969)
    # Vol.III p202 or Vol.IV page 73 for O(1-), Vol.III p202 ? for Si(2+)
    sol_si = np.r_[
        0., 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6,
        0.7, 0.8, 0.9, 1., 1.1, 1.2, 1.3, 1.4, 1.5,
    ]
    asf_si = np.r_[
        12., 11., 9.5, 8.8, 8.3, 7.7, 7.27, 6.25, 5.3,
        4.45, 3.75, 3.15, 2.7, 2.35, 2.07, 1.87, 1.71, 1.6,
    ]
    sol_o = np.r_[
        0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1., 1.1,
    ]
    asf_o = np.r_[
        9., 7.836, 5.756, 4.068, 2.968, 2.313, 1.934, 1.710, 1.566, 1.462,
        1.373, 1.294,
    ]


    # atomic absorption coefficient for Si and O as a function of lamb
    # focus on the photoelectric effect, mu=cte*(lamb*Z)**3 with
    # Z the atomic number
    # TBF : I still didn't find where to pick up the cte values and the powers
    mu_si = 1.38e-2*lamb**2.79*Zsi**2.73
    mu_si1 = 5.33e-4*lamb**2.74*Zsi**3.03
    if lamb > 6.74:
        mu_si = mu_si1
    mu_o = 5.4e-3*lamb**2.92*Zo**3.07
    mu = 2.65e-8*(7.*mu_si + 8.*mu_o)/15.

    # Calculation of the structure factor for the alpha-quartz crystal
    # ----------------------------------------------------------------

    # interpolation of atomic scattering factor ("f") in function of sol
    # ("si") for Silicium and ("o") for Oxygen
    # ("_re") for Real part and ("_im") for Imaginary part
    fsi_re = scipy.interpolate.interp1d(sol_si, asf_si)    # fsire
    dfsi_re = 0.1335*lamb - 0.006    # dfsire
    fsi_re = fsi_re(sol) + dfsi_re    # fsire
    fsi_im = 5.936e-4*Zsi*(mu_si/lamb)    # fsiim, =cte*(Z*mu)/lamb

    fo_re = scipy.interpolate.interp1d(sol_o, asf_o)    # fore
    dfo_re = 0.1335*lamb - 0.206    # dfore
    fo_re = fo_re(sol) + dfo_re    # fore
    fo_im = 5.936e-4*Zo*(mu_o/lamb)    # foim TBF: find where to find the cte

    # structure factor ("F") for (hkl) reflection
    phasesi = np.full((xsi.size), np.nan)
    phaseo = np.full((xo.size), np.nan)
    for i in range(xsi.size):
        phasesi[i] = ih*xsi[i] + ik*ysi[i] + il*zsi[i]    # arsi
    for j in range(xo.size):
        phaseo[j] = ih*xo[j] + ik*yo[j] + il*zo[j]    # aro

    Fsi_re1 = np.sum(fsi_re*np.cos(2*np.pi*phasesi))    # resip
    Fsi_re2 = np.sum(fsi_re*np.sin(2*np.pi*phasesi))    # aimsip
    Fsi_im1 = np.sum(fsi_im*np.cos(2*np.pi*phasesi))    # resis
    Fsi_im2 = np.sum(fsi_im*np.sin(2*np.pi*phasesi))    # aimsis

    Fo_re1 = np.sum(fo_re*np.cos(2*np.pi*phaseo))    # reop
    Fo_re2 = np.sum(fo_re*np.sin(2*np.pi*phaseo))    # aimop
    Fo_im1 = np.sum(fo_im*np.cos(2*np.pi*phaseo))    # reos
    Fo_im2 = np.sum(fo_im*np.sin(2*np.pi*phaseo))    # aimos

    F_re_cos = Fsi_re1 + Fo_re1    # fpre
    F_re_sin = Fsi_re2 + Fo_re2    # fpim
    F_im_cos = Fsi_im1 + Fo_im1    # fsre
    F_im_sin = Fsi_im2 + Fo_im2    # fsim

    F_re = np.sqrt(F_re_cos**2 + F_re_sin**2)    # fpmod
    F_im = np.sqrt(F_im_cos**2 + F_im_sin**2)    # fsmod

    # Calculation of Fourier coefficients of polarization
    # ---------------------------------------------------

    # expression of the Fourier coef. psi_H
    Fmod = np.sqrt(
        F_re**2 + F_im**2 - 2.*(F_re_cos*F_re_sin - F_im_cos*F_im_sin)
    )    # fmod

    # psi_-H equivalent to (-ih, -ik, -il)
    Fbmod = np.sqrt(
        F_re**2 + F_im**2 - 2.*(F_im_cos*F_im_sin - F_re_cos*F_re_sin)
    )    # fbmod

    if Fmod == 0.:
        Fmod == 1e-30
    if Fbmod == 0.:
        Fbmod == 1e-30

    # ratio imaginary part and real part of the structure factor
    kk = F_im/F_re

    # rek = Real(kk)
    rek = (F_re_cos*F_im_cos + F_re_sin*F_im_sin)/(F_re**2.)

    # real part of psi_H
    psi_re = (re*(lamb**2)*F_re)/(np.pi*V)    # psihp

    # zero-order real part (averaged) TBF
    psi0_dre = -re*(lamb**2)*(
        6.*(Zo + dfo_re) + 3.*(Zsi + dfsi_re)
        )/(np.pi*V)   # psiop

    # zero-order imaginary part (averaged)
    psi0_im = -re*(lamb**2)*(6.*fo_im + 3.*fsi_im)/(np.pi*V)    # psios

    # Power ratio and their integrated reflectivity for 3 crystals models:
    # perfect (Darwin model), ideally mosaic thick crystal and dynamical model
    # ------------------------------------------------------------------------

    (
        P_per, P_mos, P_dyn, power_ratio, th, rr, det, ymax,
    ) = CrystBragg_comp_integrated_reflect(
        lamb=lamb, re=re, V=V, Zo=Zo, theta=theta, mu=mu,
        F_re=F_re, psi_re=psi_re, psi0_dre=psi0_dre, psi0_im=psi0_im,
        Fmod=Fmod, Fbmod=Fbmod, kk=kk, rek=rek,
        model=['perfect', 'mosaic', 'dynamical',],
    )

    # Plot atomic scattering factor
    # -----------------------------

    if plot_asf:
        CrystalBragg_plot_atomic_scattering_factor(
            sol_si=sol_si, sol_o=sol_o,
            asf_si=asf_si, asf_o=asf_o,
        )

    # Plot power ratio
    # ----------------

    if plot_power_ratio:
        CrystalBragg_plot_power_ratio(
            ih=ih, ik=ik, il=il, lamb=lamb, theta=theta,
            th=th, power_ratio=power_ratio,
        )

    # Print results
    # -------------

    dout = {
        'Wavelength (A)': lamb,
        'Miller indices': (ih, ik, il),
        'Inter-reticular distance (A)': d_atom,
        'Volume of the unit cell (A^3)': np.round(V, decimals=3),
        'Bragg angle of reference (rad)': np.round(theta, decimals=3),
        'Integrated reflectivity': {
            'perfect model': np.round(P_per, decimals=9),
            'mosaic model': np.round(P_mos, decimals=9),
            'dynamical model': np.round(P_dyn, decimals=9),
        },
        'Ratio imag & real part of structure factor': np.round(kk, decimals=3),
        'Intensity maximum theoretical (normal & parallel compo)': ymax,
        'R_perp/R_par': np.round(rr[1]/rr[0], decimals=9),
        'RC width': np.round(det, decimals=6),
    }

    if verb is True:
        lstr = [f'\t -{k0}: {V0}' for k0, V0 in dout.items()]
        msg = (
            " The following data was calculated:\n"
            + "\n".join(lstr)
        )
        print(msg)

    if returnas is dict:
        return dout


def CrystBragg_check_inputs_rockingcurve(
    ih=None, ik=None, il=None, lamb=None,
):

    dd = {'ih': ih, 'ik': ik, 'il': il, 'lamb': lamb}
    lc = [v0 is None for k0, v0 in dd.items()]
    if all(lc):
        ih = 1
        ik = 1
        il = 0
        lamb = 3.96
        msg = (
            "Args h, k, l and lamb were not explicitely specified\n"
            "and have been put to default values:\n"
            + "\t - h: first Miller index ({})\n".format(ih)
            + "\t - k: second Miller index ({})\n".format(ik)
            + "\t - l: third Miller index ({})\n".format(il)
            + "\t - lamb: wavelength of interest ({})\n".format(lamb)
        )
        warnings.warn(msg)

    dd2 = {'ih': ih, 'ik': ik, 'il': il, 'lamb': lamb}
    lc2 = [v0 is None for k0, v0 in dd2.items()]
    if any(lc2):
        msg = (
            "Args h, k, l and lamb must be provided together:\n"
            + "\t - h: first Miller index ({})\n".format(ih)
            + "\t - k: second Miller index ({})\n".format(ik)
            + "\t - l: third Miller index ({})\n".format(il)
            + "\t - lamb: wavelength of interest ({})\n".format(lamb)
        )
        raise Exception(msg)

    cdt = [type(v0) == str for k0, v0 in dd.items()]
    if any(cdt) or all(cdt):
        msg = (
                        "Args h, k, l and lamb must not be string inputs:\n"
            "and have been put to default values:\n"
            + "\t - h: first Miller index ({})\n".format(ih)
            + "\t - k: second Miller index ({})\n".format(ik)
            + "\t - l: third Miller index ({})\n".format(il)
            + "\t - lamb: wavelength of interest ({})\n".format(lamb)
        )
        raise Exception(msg)

    return ih, ik, il, lamb,


def CrystBragg_comp_integrated_reflect(
    lamb=None, re=None, V=None, Zo=None, theta=None, mu=None,
    F_re=None, psi_re=None, psi0_dre=None, psi0_im=None,
    Fmod=None, Fbmod=None, kk=None, rek=None,
    model=[None, None, None]
):

    # Perfect (darwin) model
    # ----------------------

    P_per = Zo*F_re*re*lamb**2*(1. + abs(np.cos(2.*theta)))/(
        6.*np.pi*V*np.sin(2.*theta)
    )

    # Ideally thick mosaic model
    # --------------------------

    P_mos = F_re**2*re**2*lamb**3*(1. + (np.cos(2.*theta))**2)/(
        4.*mu*V**2*np.sin(2.*theta)
    )

    # Dynamical model
    # ---------------

    # incident wave polarization (normal & parallel components)
    polar = np.r_[1., abs(np.cos(2.*theta))]

    # variables of simplification y, dy, g, L
    g = psi0_im/(polar*psi_re)
    y = np.linspace(-10., 10., 501)    # ay
    ymax = kk/g
    dy = np.zeros(501) + 0.1    # day
    al = np.full((2, 501), 0.)

    power_ratio = np.full((al.shape), np.nan)    # phpo
    th = np.full((al.shape), np.nan)    # phpo
    rr = np.full((polar.shape), np.nan)
    for i in range(al[:, 0].size):
        al[i, ...] = (y**2 + g[i]**2 + np.sqrt(
            (y**2 - g[i]**2 + kk**2 - 1.)**2 + 4.*(g[i]*y - rek)**2
            ))/np.sqrt((kk**2 - 1.)**2 + 4.*rek**2)
        # reflecting power or power ratio R_dyn
        power_ratio[i, ...] = (Fmod/Fbmod)*(
            al[i, :] - np.sqrt((al[i, :]**2 - 1.))
        )
        power_ratiob = power_ratio[i, ...]
        # intensity scale on the glancing angle (y=kk/g)
        th[i, ...] = (y*polar[i]*psi_re - psi0_dre)/np.sin(2.*theta)
        # integration of the power ratio over dy
        rhy = np.sum(dy*power_ratiob)
        # diffraction radiation
        # r(i=0): normal component & r(i=1): parallel component
        rr[i, ...] = (polar[i]*psi_re*rhy)/np.sin(2.*theta)
    # Integrated reflectivity
    P_dyn = np.sum(rr)/2.
    if P_dyn < 1e-7:
        msg = (
            "Please check the equations for integrated reflectivity:\n"
            "the value of P_dyn ({}) is less than 1e-7.\n".format(P_dyn)
        )
        raise Exception(msg)

    fmax = np.max(power_ratio[0] + power_ratio[1])
    det = (2.*P_dyn)/fmax

    return (P_per, P_mos, P_dyn, power_ratio, th, rr, det, ymax,)


def CrystalBragg_plot_atomic_scattering_factor(
    sol_si=None, sol_o=None,
    asf_si=None, asf_o=None,
):

    # Check inputs
    # ------------

    lc = [sol_si is None, sol_o is None, asf_si is None, asf_o is None]
    if any(lc):
        msg = (
            "Please make sure that all entry arguments are valid and not None!"
        )
        raise Exception(msg)

    # Plot
    # ----

    fig = plt.figure(figsize=(8, 6))
    gs = gridspec.GridSpec(1, 1)
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlabel(r'sin($\theta$)/$\lambda$')
    ax.set_ylabel("atomic scattering factor")
    ax.plot(sol_si, asf_si, label="Si")
    ax.plot(sol_o, asf_o, label="O")
    ax.legend()


def CrystalBragg_plot_power_ratio(
    ih=None, ik=None, il=None, lamb=None, theta=None,
    th=None, power_ratio=None,
):

    # Plot
    # ----

    fig1 = plt.figure(figsize=(8, 6))
    gs = gridspec.GridSpec(1, 1)
    ax = fig1.add_subplot(gs[0, 0])
    ax.set_title(
        'Qz, ' + f'({ih},{ik},{il})' + fr', $\lambda$={lamb} A' +
        fr', Bragg angle={np.round(theta, decimals=3)} rad'
    )
    ax.set_xlabel(r'$\theta$-$\theta_{B}$ (rad)')
    ax.set_ylabel('P$_H$/P$_0$')
    ax.plot(th[0, :], power_ratio[0, :], label='normal component')
    ax.plot(th[1, :], power_ratio[1, :], label='parallel component')
    ax.legend()

