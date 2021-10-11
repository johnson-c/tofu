# -*- coding: utf-8 -*-


# Built-in
import time


# Common
import numpy as np
import scipy.linalg as scplin
import scipy.sparse as scpsp
import sksparse as sksp
import matplotlib.pyplot as plt


# tofu
from . import _inversions_checks


# #############################################################################
# #############################################################################
#                           main
# #############################################################################


def compute_inversions(
    coll=None,
    key_matrix=None,
    key_data=None,
    key_sigma=None,
    data=None,
    sigma=None,
    conv_crit=None,
    operator=None,
    geometry=None,
    isotropic=None,
    method=None,
    solver=None,
    sparse=None,
    chain=None,
    positive=None,
    verb=None,
    maxiter=None,
    store=None,
):

    # -------------
    # check inputs

    # kwdargs = {'maxiter': maxiter}

    (
        key_matrix, key_data, key_sigma, keybs, keym, data, sigma, opmat,
        conv_crit, operator, isotropic, sparse, matrix, crop, chain,
        positive, method, solver, kwdargs, verb, store,
    ) = _inversions_checks._compute_check(
        coll=coll,
        key_matrix=key_matrix,
        key_data=key_data,
        key_sigma=key_sigma,
        data=data,
        sigma=sigma,
        conv_crit=conv_crit,
        isotropic=isotropic,
        sparse=sparse,
        chain=chain,
        positive=positive,
        method=method,
        solver=solver,
        kwdargs=None,
        operator=operator,
        geometry=geometry,
        verb=verb,
        store=store,
    )

    nt, nchan = data.shape
    nbs = matrix.shape[1]
    func = eval(method)

    # -------------
    # prepare data

    if verb >= 1:
        t0 = time.process_time()
        t0 = time.perf_counter()
        print("Preparing data... ", end='', flush=True)

    # indt (later)

    # normalization
    data_n = (data / sigma)
    mu0 = 1.

    # Define Regularization operator
    if operator == 'D0N2':
        R = opmat[0]
    elif operator == 'D1N2':
        R = opmat[0] + opmat[1]
    elif operator == 'D2N2':
        R = opmat[0] + opmat[1]
    else:
        msg = 'unknown operator!'
        raise Exception(msg)

    # prepare computation intermediates
    precond = None
    Tyn = np.full((nbs,), np.nan)
    if sparse is True:
        Tn = scpsp.diags(1./np.nanmean(sigma, axis=0)).dot(matrix)
        TTn = Tn.T.dot(Tn)
        if solver != 'spsolve':
            # preconditioner to approx inv(TTn + reg*Rn), improves convergence
            precond = scpsp.linalg.inv(TTn + mu0*R)

    else:
        Tn = matrix / np.nanmean(sigma, axis=0)[:, None]
        TTn = Tn.T.dot(Tn)

    sol0 = np.full((nbs,), np.nanmean(data[0, :]) / matrix.mean())

    # prepare output arrays
    sol = np.full((nt, nbs), np.nan)
    mu = np.full((nt,), np.nan)
    chi2n = np.full((nt,), np.nan)
    regularity = np.full((nt,), np.nan)
    niter = np.zeros((nt,), dtype=int)
    spec = [None for ii in range(nt)]

    # -------------
    # initial guess

    if verb >= 1:
        t1 = time.process_time()
        t1 = time.perf_counter()
        print(f"{t1-t0} s", end='\n', flush=True)
        print("Setting inital guess... ", end='', flush=True)

    """
    sol0 = Default_sol(BF2, tmat, ddat, sigma0=ssigm, N=3)
    # Using discrepancy principle on averaged signal
    LL, mm = BF2.get_IntOp(Deriv=Deriv, Mode=IntMode)

    if True:
        LL = LL[0] + LL[1]
    b = ddat/ssigm                      # DB
    Tm = np.diag(1./ssigm).dot(tmat)    # DB
    Tb = Tm.T.dot(b)                    # DB
    TT = Tm.T.dot(Tm)                   # DB
    sol0, mu0 = InvLin_DisPrinc_V1_Sparse(
        NMes, Nbf,
        SpFc[SpType](Tm),
        SpFc[SpType](TT),
        SpFc[SpType](LL),
        Tb,
        b,
        sol0,
        ConvCrit=ConvCrit,
        mu0=mu0,
        chi2Tol=0.2,
        chi2Obj=1.2,
        M=None,
        Verb=True,
    )[0:2]    # DB

    Tm = np.diag(1./ssigm).dot(tmat)
    Tb = Tm.T.dot(b)
    TT = SpFc[SpType](Tm.T.dot(Tm))

    sol0, mu0, chi2N0, R0, Nit0, spec0 = func(
        NMes, Nbf, SpFc[SpType](Tm), TT, LL, Tb, b, sol0,
        ConvCrit=ConvCrit, mu0=mu0, M=None, Verb=False, **KWARGS,
    )
    """

    # -------------
    # compute

    if verb >= 1:
        t2 = time.process_time()
        t2 = time.perf_counter()
        print(f"{t2-t1} s", end='\n', flush=True)
        print("Starting time loop...", end='\n', flush=True)

    out = _compute_inv_loop(
        func=func,
        sol0=sol0,
        mu0=mu0,
        matrix=matrix,
        Tn=Tn,
        TTn=TTn,
        Tyn=Tyn,
        R=R,
        precond=precond,
        data_n=data_n,
        sigma=sigma,
        isotropic=isotropic,
        conv_crit=conv_crit,
        sparse=sparse,
        chain=chain,
        verb=verb,
        sol=sol,
        mu=mu,
        chi2n=chi2n,
        regularity=regularity,
        niter=niter,
        spec=spec,
        **kwdargs,
    )

    if verb >= 1:
        t3 = time.process_time()
        t3 = time.perf_counter()
        print(f"{t3-t2} s", end='\n', flush=True)
        print("Post-formatting results...", end='\n', flush=True)

    # -------------
    # format output

    # reshape solution
    if crop is True:
        shapebs = coll.dobj['bsplines'][keybs]['shape']
        shapesol = tuple(np.r_[nt, shapebs])
        sol_full = np.zeros(shapesol, dtype=float)
        cropbs = coll.ddata[coll.dobj['bsplines'][keybs]['crop']]['data']
        cropbsflat = cropbs.ravel(order='F')
        iR = np.tile(np.arange(0, shapebs[0]), shapebs[1])[cropbsflat]
        iZ = np.repeat(np.arange(0, shapebs[1]), shapebs[0])[cropbsflat]
        sol_full[:, iR, iZ] = sol

    # store
    if store is True:

        # key
        if coll.dobj.get('inversions') is None:
            ninv = 0
        else:
            ninv = np.max([int(kk[3:]) for kk in coll.dobj['inversions']]) + 1
        keyinv = f'inv{ninv}'

        # ref
        refinv = tuple(
            [coll.ddata[key_data]['ref'][0]]
            + list(coll.dobj['bsplines'][keybs]['ref'])
        )

        # dict
        ddata = {
            keyinv: {
                'data': sol_full,
                'ref': refinv,
            },
            f'{keyinv}-chi2n': {
                'data': chi2n,
                'ref': refinv[0],
            },
            f'{keyinv}-mu': {
                'data': mu,
                'ref': refinv[0],
            },
            f'{keyinv}-reg': {
                'data': regularity,
                'ref': refinv[0],
            },
            f'{keyinv}-niter': {
                'data': niter,
                'ref': refinv[0],
            },
        }

        if key_sigma is None:
            key_sigma = f'{key_data}-sigma'
            if sigma.shape == data.shape:
                ref_sigma = coll.ddata[key_data]['ref']
            else:
                ref_sigma = coll.ddata[key_data]['ref'][1:]
                sigma = sigma[0, :]
            ddata.update({
                key_sigma: {
                    'data': sigma,
                    'ref': ref_sigma,
                    'units': coll.ddata[key_data].get('units'),
                    'dim': coll.ddata[key_data].get('dim'),
                },
            })

        dobj = {
            'inversions': {
                keyinv: {
                    'data_in': key_data,
                    'matrix': key_matrix,
                    'sol': keyinv,
                    'operator': operator,
                    'geometry': geometry,
                    'isotropic': isotropic,
                    'method': method,
                    'solver': solver,
                    'chain': chain,
                    'positive': positive,
                    'conv_crit': conv_crit,
                },
            },
        }

        coll.update(dobj=dobj, ddata=ddata)


    else:
        return sol_full, mu, chi2n, regularity, niter, spec


# #############################################################################
# #############################################################################
#                           _compute
# #############################################################################


def _compute_inv_loop(
    func=None,
    sol0=None,
    mu0=None,
    matrix=None,
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    precond=None,
    data_n=None,
    sigma=None,
    conv_crit=None,
    isotropic=None,
    sparse=None,
    chain=None,
    verb=None,
    sol=None,
    mu=None,
    chi2n=None,
    regularity=None,
    niter=None,
    spec=None,
    **kwdargs,
):

    # -----------------------------------
    # Getting initial solution - step 1/2

    nt, nchan = data_n.shape
    nbs = R.shape[0]

    if verb >= 2:
        form = "nchan * chi2n   +   mu *  R           "
        verb2head = f"\n\t\titer    {form} \t\t\t  tau  \t      conv"
    else:
        verb2head = None

    if sparse:

        # Beware of element-wise operations vs matrix operations !!!!
        for ii in range(0, nt):

            if verb >= 1:
                msg = f"\ttime step {ii+1} / {nt} "
                print(msg, end='', flush=True)

            # intermediates
            if sigma.shape[0] > 1:
                Tn.data = scpsp.diags(1./sigma[ii, :]).dot(matrix).data
                TTn.data = Tn.T.dot(Tn).data

            Tyn[:] = Tn.T.dot(data_n[ii, :])

            # solving
            (
                sol[ii, :], mu[ii], chi2n[ii], regularity[ii],
                niter[ii], spec[ii],
            ) = func(
                Tn=Tn,
                TTn=TTn,
                Tyn=Tyn,
                R=R,
                yn=data_n[ii, :],
                sol0=sol0,
                nchan=nchan,
                nbs=nbs,
                mu0=mu0,
                conv_crit=conv_crit,
                precond=precond,
                chain=chain,
                verb=verb,
                verb2head=verb2head,
                **kwdargs,
            )

            # post
            if chain:
                sol0[:] = sol[ii, :]
            mu0 = mu[ii]

            if verb == 1:
                msg = f"   chi2n = {chi2n[ii]:.3e}    niter = {niter[ii]}"
                print(msg, end='\n', flush=True)

    else:
        # Beware of element-wise operations vs matrix operations !!!!
        for ii in range(0, nt):

            if verb >= 1:
                msg = f"\ttime step {ii+1} / {nt} "
                print(msg, end='', flush=True)

            # intermediates
            if sigma.shape[0] > 1:
                Tn[...] = matrix / sigma[ii, :][:, None]
                TTn[...] = Tn.T.dot(Tn)

            Tyn[:] = Tn.T.dot(data_n[ii, :])

            # solving
            (
                sol[ii, :], mu[ii], chi2n[ii], regularity[ii],
                niter[ii], spec[ii],
            ) = func(
                Tn=Tn,
                TTn=TTn,
                Tyn=Tyn,
                R=R,
                yn=data_n[ii, :],
                sol0=sol0,
                nchan=nchan,
                nbs=nbs,
                mu0=mu0,
                conv_crit=conv_crit,
                precond=precond,
                chain=chain,
                verb=verb,
                verb2head=verb2head,
                **kwdargs,
            )

            # post
            if chain:
                sol0[:] = sol[ii, :]
            mu0 = mu[ii]

            if verb == 1:
                msg = f"   chi2n = {chi2n[ii]:.3e}    niter = {niter[ii]}"
                print(msg, end='\n', flush=True)


# #############################################################################
# #############################################################################
#                       functions
# #############################################################################


def inv_linear_augTikho_v1(
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    yn=None,
    sol0=None,
    nchan=None,
    nbs=None,
    mu0=None,
    conv_crit=None,
    a0=None,
    b0=None,
    a1=None,
    b1=None,
    d=None,
    atol=None,
    btol=None,
    conlim=None,
    maxiter=None,
    precond=None,
    conv_reg=True,
    nbs_fixed=True,
    chain=None,
    verb=None,
    verb2head=None,
):
    # Install scikit !
    # Install scikits and use CHOLMOD fast cholesky factorization !!!
    """
    Linear algorithm for Phillips-Tikhonov regularisation, called "Augmented Tikhonov", sparese matrix version
    see TFI.InvLin_AugTikho_V1.__doc__ for details
    """

    a0bis = a0 - 1. + nbs/2. if not nbs_fixed else a0 - 1. + 1200./2.
    a1bis = a1 - 1. + nchan/2.

    conv = 0.           # convergence variable
    niter = 0           # number of iterations
    mu1 = 0.            # regularisation param

    # verb
    if verb >= 2:
        chi2n = np.sum((Tn.dot(sol0) - yn)**2) / nchan
        reg = sol0.dot(R.dot(sol0))
        temp = f"{nchan} * {chi2n:.3e} + {mu0:.3e} * {reg:.3e}"
        print(
            f"{verb2head}\n\t\t\t {temp} = {nchan*chi2n + mu0*reg:.3e}",
            end='\n',
        )

    # loop
    # Continue until convergence criterion, and at least 2 iterations
    while  niter < 2 or conv > conv_crit:

        # call solver
        sol = scplin.solve(
            TTn + mu0*R, Tyn,
            assume_a='pos',     # faster than 'sym'
            overwrite_a=True,  # no significant gain
            overwrite_b=False,  # True is faster, but a copy of Tyn is needed
            check_finite=False, # small speed gain compared to True
            transposed=False,
        ) # 3

        # compute residu, regularity...
        res2 = np.sum((Tn.dot(sol)-yn)**2)  # residu**2
        chi2n = res2/nchan                  # normalised residu
        reg = sol.dot(R.dot(sol))           # regularity term

        # update lamb, tau
        lamb = a0bis/(0.5*reg + b0)             # Update reg. param. estimate
        tau = a1bis/(0.5*res2 + b1)             # Update noise coef. estimate
        mu1 = (lamb/tau) * (2*a1bis/res2)**d    # Update reg. param. taking into account rescaling with noise estimate

        # Compute convergence variable
        if conv_reg:
            conv = np.abs(mu1 - mu0) / mu1
        else:
            sol2 = sol**2
            sol2max = np.max(sol2)
            sol2[sol2 < 0.001*sol2max] = 0.001*sol2max
            conv = np.sqrt(np.sum((sol - sol0)**2 / sol2) / nbs)

        # verb
        if verb >= 2:
            temp1 = f"{nchan} * {chi2n:.3e} + {mu1:.3e} * {reg:.3e}"
            temp2 = f"{res2 + mu1*reg:.3e}"
            temp = f"{temp1} = {temp2}"
            print(f"\t\t{niter} \t {temp}   {tau:.3e}   {conv:.3e}")

        # update sol0, mu0 for next iteration
        sol0[:] = sol[:]
        mu0 = mu1
        niter += 1

    return sol, mu1, chi2n, reg, niter, [tau, lamb]


def inv_linear_augTikho_v1_sparse(
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    yn=None,
    sol0=None,
    nchan=None,
    nbs=None,
    mu0=None,
    conv_crit=None,
    a0=None,
    b0=None,
    a1=None,
    b1=None,
    d=None,
    atol=None,
    btol=None,
    conlim=None,
    maxiter=None,
    precond=None,
    conv_reg=True,
    nbs_fixed=True,
    chain=None,
    verb=None,
    verb2head=None,
):
    # Install scikit !
    # Install scikits and use CHOLMOD fast cholesky factorization !!!
    """
    Linear algorithm for Phillips-Tikhonov regularisation, called "Augmented Tikhonov", sparese matrix version
    see InvLin_AugTikho_V1.__doc__ for details
    """

    a0bis = a0 - 1. + nbs/2. if not nbs_fixed else a0 - 1. + 1200./2.
    a1bis = a1 - 1. + nchan/2.

    conv = 0.           # convergence variable
    niter = 0           # number of iterations
    mu1 = 0.            # regularisation param

    # verb
    if verb >= 2:
        chi2n = np.sum((Tn.dot(sol0) - yn)**2) / nchan
        reg = sol0.dot(R.dot(sol0))
        temp = f"{nchan} * {chi2n:.3e} + {mu0:.3e} * {reg:.3e}"
        print(
            f"{verb2head}\n\t\t\t {temp} = {nchan*chi2n + mu0*reg:.3e}",
            end='\n',
        )

    # loop
    # Continue until convergence criterion, and at least 2 iterations
    while  niter < 2 or conv > conv_crit:
        sol = scpsp.linalg.spsolve(
              TTn + mu0*R, Tyn,
              permc_spec=None,
              use_umfpack=True,
        )

        res2 = np.sum((Tn.dot(sol)-yn)**2)      # residu**2
        chi2n = res2/nchan                      # normalised residu
        reg = sol.dot(R.dot(sol))       # regularity term

        lamb = a0bis/(0.5*reg + b0)     # Update reg. param. estimate
        tau = a1bis/(0.5*res2 + b1)                 # Update noise coef. estimate
        mu1 = (lamb/tau) * (2*a1bis/res2)**d        # Update reg. param. taking into account rescaling with noise estimate

        # Compute convergence variable
        if conv_reg:
            conv = np.abs(mu1 - mu0) / mu1
        else:
            sol2 = sol**2
            sol2max = np.max(sol2)
            sol2[sol2 < 0.001*sol2max] = 0.001*sol2max
            conv = np.sqrt(np.sum((sol - sol0)**2 / sol2) / nbs)

        # verb
        if verb >= 2:
            temp1 = f"{nchan} * {chi2n:.3e} + {mu1:.3e} * {reg:.3e}"
            temp2 = f"{res2 + mu1*reg:.3e}"
            temp = f"{temp1} = {temp2}"
            print(
                f"\t\t{niter} \t {temp}   {tau:.3e}   {conv:.3e}"
            )
            # print '\t\ŧ\tisstop,itn=',isstop,itn, '  normRArAX=',normr, normar, norma,normx, 'condA=',conda

        sol0[:] = sol[:]            # Update reference solution
        niter += 1                  # Update number of iterations
        mu0 = mu1
    return sol, mu1, chi2n, reg, niter, [tau, lamb]


def inv_linear_augTikho_chol(
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    yn=None,
    sol0=None,
    nchan=None,
    nbs=None,
    mu0=None,
    conv_crit=None,
    a0=None,
    b0=None,
    a1=None,
    b1=None,
    d=None,
    atol=None,
    btol=None,
    conlim=None,
    maxiter=None,
    precond=None,
    conv_reg=True,
    nbs_fixed=True,
    chain=None,
    verb=None,
    verb2head=None,
):
    """
    Linear algorithm for Phillips-Tikhonov regularisation, called "Augmented Tikhonov"
    augmented in the sense that bayesian statistics are combined with standard Tikhonov regularisation
    Determines both noise (common multiplicative coefficient) and regularisation paremeter automatically
    We assume here that all arrays have previously been scaled (noise, conditioning...)
    Sparse matrixes are also prefered to speed-up the computation
    In this method:
      tau is an approximation of the inverse of the noise coefficient
      lamb is an approximation of the regularisation parameter
    N.B.: The noise and reg. param. have probability densities of the form : f(x) = x^(a-1) * exp(-bx)
    This function maximum is in x = (a-1)/b, so a = b+1 gives a maximum at 1.
    (a0,b0) for the reg. param. and (a1,b1) for the noise estimate
    Ref:
      [1] Jin B., Zou J., Inverse Problems, vol.25, nb.2, 025001, 2009
      [2] http://www.math.uni-bremen.de/zetem/cms/media.php/250/nov14talk_jin%20bangti.pdf
      [3] Kazufumi Ito, Bangti Jin, Jun Zou, "A New Choice Rule for Regularization Parameters in Tikhonov Regularization", Research report, University of Hong Kong, 2008
    """

    a0bis = a0 - 1. + nbs/2. if not nbs_fixed else a0 - 1. + 1200./2.
    a1bis = a1 - 1. + nchan/2.

    conv = 0.           # convergence variable
    niter = 0           # number of iterations
    mu1 = 0.            # regularisation param

    # verb
    if verb >= 2:
        chi2n = np.sum((Tn.dot(sol0) - yn)**2) / nchan
        reg = sol0.dot(R.dot(sol0))
        temp = f"{nchan} * {chi2n:.3e} + {mu0:.3e} * {reg:.3e}"
        print(
            f"{verb2head}\n\t\t\t {temp} = {nchan*chi2n + mu0*reg:.3e}",
            end='\n',
        )

    # loop
    # Continue until convergence criterion, and at least 2 iterations
    while  niter < 2 or conv > conv_crit:
        try:
            # choleski decomposition requires det(TT + mu0*LL) != 0
            # (chol(A).T * chol(A) = A
            chol = scplin.cholesky(
                TTn + mu0*R,
                lower=False,
                check_finite=False,
                overwrite_a=False,
            )
            # Use np.linalg.lstsq for double-solving the equation
            sol = scplin.cho_solve(
                (chol, False), Tyn,
                overwrite_b=None,
                check_finite=True,
            )
        except Exception as err:
            # call solver
            sol = scplin.solve(
                TTn + mu0*R, Tyn,
                assume_a='sym',     # chol failed => not 'pos'
                overwrite_a=True,   # no significant gain
                overwrite_b=False,  # True is faster, but a copy of Tyn is needed
                check_finite=False, # small speed gain compared to True
                transposed=False,
            ) # 3

        # compute residu, regularity...
        res2 = np.sum((Tn.dot(sol)-yn)**2)  # residu**2
        chi2n = res2/nchan                  # normalised residu
        reg = sol.dot(R.dot(sol))           # regularity term

        # update lamb, tau
        lamb = a0bis/(0.5*reg + b0)             # Update reg. param. estimate
        tau = a1bis/(0.5*res2 + b1)             # Update noise coef. estimate
        mu1 = (lamb/tau) * (2*a1bis/res2)**d    # Update reg. param. taking into account rescaling with noise estimate

        # Compute convergence variable
        if conv_reg:
            conv = np.abs(mu1 - mu0) / mu1
        else:
            sol2 = sol**2
            sol2max = np.max(sol2)
            sol2[sol2 < 0.001*sol2max] = 0.001*sol2max
            conv = np.sqrt(np.sum((sol - sol0)**2 / sol2) / nbs)

        # verb
        if verb >= 2:
            temp1 = f"{nchan} * {chi2n:.3e} + {mu1:.3e} * {reg:.3e}"
            temp2 = f"{res2 + mu1*reg:.3e}"
            temp = f"{temp1} = {temp2}"
            print(f"\t\t{niter} \t {temp}   {tau:.3e}   {conv:.3e}")

        # update sol0, mu0 for next iteration
        sol0[:] = sol[:]
        mu0 = mu1
        niter += 1

    return sol, mu1, chi2n, reg, niter, [tau, lamb]


def inv_linear_augTikho_chol_sparse(
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    yn=None,
    sol0=None,
    nchan=None,
    nbs=None,
    mu0=None,
    conv_crit=None,
    a0=None,
    b0=None,
    a1=None,
    b1=None,
    d=None,
    atol=None,
    btol=None,
    conlim=None,
    maxiter=None,
    precond=None,
    conv_reg=True,
    nbs_fixed=True,
    chain=None,
    verb=None,
    verb2head=None,
):
    """
    Linear algorithm for Phillips-Tikhonov regularisation, called "Augmented Tikhonov"
    augmented in the sense that bayesian statistics are combined with standard Tikhonov regularisation
    Determines both noise (common multiplicative coefficient) and regularisation paremeter automatically
    We assume here that all arrays have previously been scaled (noise, conditioning...)
    Sparse matrixes are also prefered to speed-up the computation
    In this method:
      tau is an approximation of the inverse of the noise coefficient
      lamb is an approximation of the regularisation parameter
    N.B.: The noise and reg. param. have probability densities of the form : f(x) = x^(a-1) * exp(-bx)
    This function maximum is in x = (a-1)/b, so a = b+1 gives a maximum at 1.
    (a0,b0) for the reg. param. and (a1,b1) for the noise estimate
    Ref:
      [1] Jin B., Zou J., Inverse Problems, vol.25, nb.2, 025001, 2009
      [2] http://www.math.uni-bremen.de/zetem/cms/media.php/250/nov14talk_jin%20bangti.pdf
      [3] Kazufumi Ito, Bangti Jin, Jun Zou, "A New Choice Rule for Regularization Parameters in Tikhonov Regularization", Research report, University of Hong Kong, 2008
    """

    a0bis = a0 - 1. + nbs/2. if not nbs_fixed else a0 - 1. + 1200./2.
    a1bis = a1 - 1. + nchan/2.

    conv = 0.           # convergence variable
    niter = 0           # number of iterations
    mu1 = 0.            # regularisation param

    # verb
    if verb >= 2:
        chi2n = np.sum((Tn.dot(sol0) - yn)**2) / nchan
        reg = sol0.dot(R.dot(sol0))
        temp = f"{nchan} * {chi2n:.3e} + {mu0:.3e} * {reg:.3e}"
        print(
            f"{verb2head}\n\t\t\t {temp} = {nchan*chi2n + mu0*reg:.3e}",
            end='\n',
        )

    # loop
    # Continue until convergence criterion, and at least 2 iterations
    factor = None
    while  niter < 2 or conv > conv_crit:
        try:
            # choleski decomposition requires det(TT + mu0*LL) != 0
            # A = (chol(A).T * chol(A)
            # optimal if matrix is csc
            if factor is None:
                factor = sksp.cholmod.cholesky(
                    TTn + mu0*R,
                    beta=0,
                    mode='auto',
                    ordering_method='default',
                    use_long=False,
                )
            else:
                # re-use same factor
                factor.cholesky_inplace(TTn + mu0*R, beta=0)
            sol = factor.solve_A(Tyn)
        except Exception as err:
            # call solver
            sol = scpsp.linalg.spsolve(
                TTn + mu0*R, Tyn,
                permc_spec=None,
                use_umfpack=True,
            )

        # compute residu, regularity...
        res2 = np.sum((Tn.dot(sol)-yn)**2)  # residu**2
        chi2n = res2/nchan                  # normalised residu
        reg = sol.dot(R.dot(sol))           # regularity term

        # update lamb, tau
        lamb = a0bis/(0.5*reg + b0)             # Update reg. param. estimate
        tau = a1bis/(0.5*res2 + b1)             # Update noise coef. estimate
        mu1 = (lamb/tau) * (2*a1bis/res2)**d    # Update reg. param. taking into account rescaling with noise estimate

        # Compute convergence variable
        if conv_reg:
            conv = np.abs(mu1 - mu0) / mu1
        else:
            sol2 = sol**2
            sol2max = np.max(sol2)
            sol2[sol2 < 0.001*sol2max] = 0.001*sol2max
            conv = np.sqrt(np.sum((sol - sol0)**2 / sol2) / nbs)

        # verb
        if verb >= 2:
            temp1 = f"{nchan} * {chi2n:.3e} + {mu1:.3e} * {reg:.3e}"
            temp2 = f"{res2 + mu1*reg:.3e}"
            temp = f"{temp1} = {temp2}"
            print(f"\t\t{niter} \t {temp}   {tau:.3e}   {conv:.3e}")

        # update sol0, mu0 for next iteration
        sol0[:] = sol[:]
        mu0 = mu1
        niter += 1

    return sol, mu1, chi2n, reg, niter, [tau, lamb]

"""
def inv_linquad_augTikho_v1_sparse(
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    yn=None,
    sol0=None,
    nchan=None,
    nbs=None,
    mu0=None,
    conv_crit=None,
    a0=None,
    b0=None,
    a1=None,
    b1=None,
    d=None,
    atol=None,
    btol=None,
    conlim=None,
    maxiter=None,
    precond=None,
    conv_reg=True,
    nbs_fixed=True,
    chain=None,
    verb=None,
    verb2head=None,


    NMes, Nbf, Tm, TT, LL, Tb, b, sol0,
    mu0=TFD.mu0,
    ConvCrit=TFD.ConvCrit,
    a0=TFD.AugTikho_a0,
    b0=TFD.AugTikho_b0,
    a1=TFD.AugTikho_a1,
    b1=TFD.AugTikho_b1,
    d=TFD.AugTikho_d,
    atol=TFD.AugTkLsmrAtol,
    btol=TFD.AugTkLsmrBtol,
    conlim=TFD.AugTkLsmrConlim,
    maxiter=TFD.AugTkLsmrMaxiter,
    NormL=None,
    M=None,
    Verb=False,
    ConvReg=True,
    FixedNb=True,
):
    Quadratic algorithm for Phillips-Tikhonov regularisation, alternative to the linear version with positivity constraint
    see TFI.InvLin_AugTikho_V1.__doc__ for details

    a0bis = a0 - 1. + nbs/2. if not nbs_fixed else a0 - 1. + 1200./2.
    a1bis = a1 - 1. + nchan/2.

    conv = 0.           # convergence variable
    niter = 0           # number of iterations
    mu1 = 0.            # regularisation param

    if M is None:
        M = scpsplin.inv((TT + lmu[-1]*LL).tocsc())

    # verb
    if verb >= 2:
        chi2n = np.sum((Tn.dot(sol0) - yn)**2) / nchan
        reg = sol0.dot(R.dot(sol0))
        temp = f"{nchan} * {chi2n:.3e} + {mu0:.3e} * {reg:.3e}"
        print(
            f"{verb2head}\n\t\t\t {temp} = {nchan*chi2n + mu0*reg:.3e}",
            end='\n',
        )

    Bds = tuple([(-0.2,None) for ii in range(0,sol0.size)])
    F = lambda X, mu=lmu[-1]: np.sum((Tm.dot(X)-b)**2) + mu*X.dot(LL.dot(X))
    F_g = lambda X, mu=lmu[-1]: 2.*(TT + mu*LL).dot(X) - 2.*Tb
    F_h = lambda X, mu=lmu[-1]: 2.*(TT + mu*LL)

    Method = 'L-BFGS-B'
    if Method == 'L-BFGS-B':
        options={'ftol':ConvCrit/100., 'disp':False}
    elif Method == 'TNC':
        options={'ftol':ConvCrit/100., 'disp':False, 'minfev':1, 'rescale':1., 'maxCGit':0, 'offset':0.}  # Not working....
    elif Method == 'SLSQP':
        options={'ftol':ConvCrit/100., 'disp':False}      # Very slow... (maybe not updated ?)

    while  niter < 2 or conv > conv_crit:                              # Continue until convergence criterion is fulfilled, and do at least 2 iterations
        Out = scpop.minimize(F, sol0, args=([lmu[-1]]), jac=F_g, hess=F_h, method=Method, bounds=Bds, options=options)       # Minimisation de la fonction (method quadratique)
        sol = Out.x
        Res = np.sum((Tm.dot(sol)-b)**2)                        # Compute residu**2
        chi2N.append(Res/NMes)                                  # Record normalised residu history
        R.append(sol.dot(LL.dot(sol)))                          # Compute and record regularity term

        lamb = a0bis/(0.5*R[Nit]+b0)                            # Update reg. param. estimate
        tau = a1bis/(0.5*Res+b1)                                # Update noise coef. estimate
        lmu.append((lamb/tau) * (2*a1bis/Res)**d)               # Update regularisation parameter taking into account rescaling with noise estimate
        if ConvReg:
            Conv = np.abs(lmu[-1]-lmu[-2])/lmu[-1]
        else:
            Conv = np.sqrt(np.sum((sol-sol0)**2/np.max([sol**2,0.001*np.max(sol**2)*np.ones((Nbf,))],axis=0))/Nbf)        # Compute convergence variable
        if Verb:
            print("        Nit = ",str(Nit),"  N*Chi2N + mu*R = ",
                  NMes,'*',chi2N[Nit],'+',lmu[-1],'*',R[Nit], ' = ',
                  Res+lmu[-1]*R[Nit], '  tau = ',tau, '  Conv = ',Conv)
        sol0[:] = sol[:]                                           # Update reference solution
        Nit += 1                                                # Update number of iterations

    return sol, lmu[-1], chi2N[-1], R[-1], Nit, [tau, lamb]
"""


"""
def estimate_jacob_scalar_Spec(ff, x0, ratio=0.05):
    nV = x0.size
    jac = np.zeros((nV,))
    dx = np.zeros((nV,))
    for ii in range(0,nV):
        dx[ii] = ratio*x0[ii]
        jac[ii] = (ff(x0+dx)[-1]-ff(x0)[-1])/dx[ii]
        dx[ii] = 0.
    return jac



def InvQuad_AugTikho_V1(NMes, Nbf, Tm, TT, LL, Tb, b, sol0, mu0=TFD.mu0, ConvCrit=TFD.ConvCrit, a0=TFD.AugTikho_a0, b0=TFD.AugTikho_b0, a1=TFD.AugTikho_a1, b1=TFD.AugTikho_b1, d=TFD.AugTikho_d, NormL=None, Verb=False, ConvReg=True, ratiojac=0.05, Method='Newton-CG', FixedNb=True):
    Non-linear (quadratic) algorithm for Phillips-Tikhonov regularisation, inspired from "Augmented Tikhonov"
    see TFI.InvLin_AugTikho_V1.__doc__ for details


    a0bis = a0-1.+Nbf/2. if not FixedNb else a0-1.+1200./2.
    a1bis = a1-1.+NMes/2.

    Conv = 0.                                                   # Initialise convergence variable
    Nit = 0                                                     # Initialise number of iterations
    chi2N, R = [], []                                           # Initialise residu list and regularisation term list
    mu = mu0                                                    # Initialise regularisation parameter
    if NormL is None:
        NormL = sol0.dot(LL.dot(sol0))
    LL = LL/NormL                                               # Scale the regularity operator
    if Verb:
        print("        Init. guess : N*Chi2N + mu*RN = ",
              NMes,'*',np.sum((Tm.dot(sol0)-b)**2)/NMes,'+',mu,'*',sol0.dot(LL.dot(sol0)),
              ' = ', np.sum((Tm.dot(sol0)-b)**2)+mu*sol0.dot(LL.dot(sol0)))
        while  Nit<2 or Conv>ConvCrit:                              # Continue until convergence criterion is fulfilled, and do at least 2 iterations
            F = lambda X, mu=mu: np.sum((Tm.dot(X)-b)**2) + mu*X.dot(LL.dot(X))
            Out = scpop.minimize(F, sol0, tol=None, method=Method, options={'maxiter':100, 'disp':True})       # Minimisation de la fonction (method quadratique)
            sol = Out.x
            Res = np.sum((Tm.dot(sol)-b)**2)                        # Compute residu**2
            chi2N.append(Res/NMes)                                  # Record normalised residu history
            R.append(sol.dot(LL.dot(sol)))                          # Compute and record regularity term

            lamb = a0bis/(0.5*R[Nit]+b0)                            # Update reg. param. estimate
            tau = a1bis/(0.5*Res+b1)                                # Update noise coef. estimate
            mu = (lamb/tau) * (2*a1bis/Res)**d                      # Update regularisation parameter taking into account rescaling with noise estimate
            if ConvReg:
                Conv = np.abs(lmu[-1]-lmu[-2])/lmu[-1]
            else:
                Conv = np.sqrt(np.sum((sol-sol0)**2/np.max([sol**2,0.001*np.max(sol**2)*np.ones((Nbf,))],axis=0))/Nbf)        # Compute convergence variable
            print("        Nit = ",str(Nit),"   N*Chi2N + mu*R = ",
                  NMes,'*',chi2N[Nit],'+',mu,'*',R[Nit], ' = ', Res+mu*R[Nit],
                  '    tau = ',tau, '    Conv = ',Conv)
            sol0[:] = sol[:]                                        # Update reference solution
            Nit += 1                                                # Update number of iterations
    else:
        xx = np.zeros((Nbf,))
        F = lambda X : np.sum((Tm.dot(X[:-1])-b)**2) + X[-1]*X[:-1].dot(LL.dot(X[:-1]))
        Out = scpop.minimize(F, np.append(sol0,mu), tol=None, options={'maxiter':100, 'disp':False})
        sol = Out.x[:-1]
        Res = np.sum((Tm.dot(sol)-b)**2)
        chi2N.append(np.sum((Tm.dot(sol)-b)**2)/NMes)
        R.append(sol.dot(LL.dot(sol)))
        lamb = a0bis/(0.5*R[-1]+b0)                            # Update reg. param. estimate
        tau = a1bis/(0.5*Res+b1)                                # Update noise coef. estimate
        mu = (lamb/tau) * (2*a1bis/Res)**d
        print("    Done :", chi2N)

    return sol, mu, chi2N[-1], R[-1], Nit, [tau, lamb]



def InvLin_DisPrinc_V1_Sparse(NMes, Nbf, Tm, TT, LL, Tb, b, sol0, mu0=TFD.mu0, ConvCrit=TFD.ConvCrit, chi2Tol=TFD.chi2Tol, chi2Obj=TFD.chi2Obj, M=None, Verb=False, NormL=None):
    Discrepancy principle

    Ntry = 0
    LogTol = np.log(chi2Obj)

    chi2N = []                                                  # Initialise residu list and regularisation term list
    lmu = [mu0]                                                 # Initialise regularisation parame
    if NormL is None:
        NormL = sol0.dot(LL.dot(sol0))
    LL = LL/NormL                                               # Scale the regularity operator
    if M is None:
        M = scpsplin.inv((TT + lmu[-1]*LL).tocsc())
    #try:
    if Verb:
        print("        Initial guess : N*Chi2N + mu*RN = ",
              NMes,'*',np.sum((Tm.dot(sol0)-b)**2)/NMes,'+',lmu[-1],'*',sol0.dot(LL.dot(sol0)),
              ' = ',
              np.sum((Tm.dot(sol0)-b)**2)+lmu[-1]*sol0.dot(LL.dot(sol0)))
        while Ntry==0 or np.abs(chi2N[-1]-chi2Obj)>chi2Tol:
            sol, itconv = scpsplin.cg(TT + lmu[-1]*LL, Tb, x0=sol0, tol=1e-08, maxiter=None, M=M)    # 1
            Ntry += 1
            chi2N.append(np.sum((Tm.dot(sol)-b)**2)/NMes)
            if Ntry==1:
                if chi2N[-1]>=chi2Obj+chi2Tol:
                    lmu.append(lmu[-1]/50.)
                elif chi2N[-1]<=chi2Obj-chi2Tol:
                    lmu.append(lmu[-1]*50.)
                else:
                    lmu.append(lmu[-1])
            elif all([chi>=chi2Obj+chi2Tol for chi in chi2N]) or all([chi<=chi2Obj-chi2Tol for chi in chi2N]):
                if chi2N[-1]>=chi2Obj+chi2Tol:
                    lmu.append(lmu[-1]/50.)
                else:
                    lmu.append(lmu[-1]*50.)
            else:
                indsort = np.argsort(chi2N)
                lmu.append(np.exp(np.interp(LogTol, np.log(np.asarray(chi2N)[indsort]), np.log(np.asarray(lmu)[indsort]))))
            print("        InvLin_DisPrinc_V1 : try ",Ntry-1, "mu =",
                  lmu[-2],"chi2N = ",chi2N[-1], "New mu = ", lmu[-1])
    else:
        while Ntry==0 or np.abs(chi2N[-1]-chi2Obj)>chi2Tol:
            sol, itconv = scpsplin.cg(TT + lmu[-1]*LL, Tb, x0=sol0, tol=1e-08, maxiter=None, M=M)
            Ntry += 1
            chi2N.append(np.sum((Tm.dot(sol)-b)**2)/NMes)
            if Ntry==1:
                if chi2N[-1]>=chi2Obj+chi2Tol:
                    lmu.append(lmu[-1]/50.)
                elif chi2N[-1]<=chi2Obj-chi2Tol:
                    lmu.append(lmu[-1]*50.)
                else:
                    lmu.append(lmu[-1])
            elif all([chi>=chi2Obj+chi2Tol for chi in chi2N]) or all([chi<=chi2Obj-chi2Tol for chi in chi2N]):
                if chi2N[-1]>=chi2Obj+chi2Tol:
                    lmu.append(mu[-1]/50.)
                else:
                    lmu.append(mu[-1]*50.)
            else:
                indsort = np.argsort(chi2N)
                #mu.append(np.exp(np.log(mu[-1]) - np.log(chi2N[-1])*(np.log(mu[-1])-np.log(mu[-2]))/(np.log(chi2N[-1])-np.log(chi2N[-2])))
                lmu.append(np.exp(np.interp(LogTol, np.log(np.asarray(chi2N)[indsort]),np.log(np.asarray(lmu[:-1])[indsort]))))
    # except:
        # print np.asarray(lmu[:-1]), np.asarray(chi2N), np.arange(0,len(chi2N))
        # plt.figure()
        # plt.scatter(np.asarray(lmu[:-1]),np.asarray(chi2N), c=np.arange(0,len(chi2N)),edgecolors='none')
        # plt.gca().set_xscale('log'), plt.gca().set_yscale('log')
        # plt.gca().set_xlim(r"$\log_10(\mu)$"), plt.gca().set_ylim(r"$\log_10(\chi^2_N)$")
        # plt.figure()
        # plt.plot(np.asarray(LL),'b-')
        # plt.figure()
        # plt.plot(TT,'ko'), plt.plot(TT+lmu[-1]*LL,'r--')
        # plt.show()

    return sol, lmu[-1], chi2N[-1], sol.dot(LL.dot(sol)), Ntry, []
"""
