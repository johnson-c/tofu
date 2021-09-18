# -*- coding: utf-8 -*-


# Built-in


# Common
import numpy as np
import scipy.interpolate as scpinterp


# #############################################################################
# #############################################################################
#                           Utilities
# #############################################################################


def _check_var(var, varname, types=None, default=None, allowed=None):
    if var is None:
        var = default

    if types is not None:
        if not isinstance(var, types):
            msg = (
                f"Arg {varname} must be of type {types}!\n"
                f"Provided: {type(var)}"
            )
            raise Exception(msg)

    if allowed is not None:
        if var not in allowed:
            msg = (
                f"Arg {varname} must be in {allowed}!\n"
                f"Provided: {var}"
            )
            raise Exception(msg)
    return var


# #############################################################################
# #############################################################################
#                           Mesh2DRect - bsplines
# #############################################################################


def _get_bs2d_func_check(
    coefs=None,
    ii=None,
    jj=None,
    R=None,
    Z=None,
    shapebs=None,
    crop=None,
    cropbs=None,
):

    # ii, jj
    if ii is not None:
        c0 = (
            isinstance(ii, (int, np.int_))
            and ii >= 0
            and ii < shapebs[0]
        )
        if not c0:
            msg = (
                "Arg ii must be an index in the range [0, {shapebs[0]}[\n"
                f"Provided: {ii}"
            )
            raise Exception(msg)
    if jj is not None:
        c0 = (
            isinstance(jj, (int, np.int_))
            and jj >= 0
            and jj < shapebs[1]
        )
        if not c0:
            msg = (
                "Arg jj must be an index in the range [0, {shapebs[1]}[\n"
                f"Provided: {jj}"
            )
            raise Exception(msg)

    # R, Z
    if not isinstance(R, np.ndarray):
        R = np.atleast_1d(R)
    if not isinstance(Z, np.ndarray):
        Z = np.atleast_1d(Z)
    assert R.shape == Z.shape

    # coefs
    if coefs is None:
        coefs = 1.
    if np.isscalar(coefs):
        pass
    else:
        coefs = np.atleast_1d(coefs)
        if coefs.ndim < len(shapebs) or coefs.ndim > len(shapebs) + 1:
            msg = (
                "coefs has too small / big shape!\n"
                f"\t- coefs.shape: {coefs.shape}\n"
                f"\t- shapebs:     {shapebs}"
            )
            raise Exception(msg)
        if coefs.ndim == len(shapebs):
            coefs = coefs.reshape(tuple(np.r_[1, coefs.shape]))
        if coefs.shape[1:] != shapebs:
            msg = (
                "coefs has wrong shape!\n"
                f"\t- coefs.shape: {coefs.shape}\n"
                f"\t- shapebs:     {shapebs}"
            )
            raise Exception(msg)

    # crop
    if crop is None:
        crop = True
    if not isinstance(crop, bool):
        msg = (
            "Arg crop must be a bool!\n"
            f"Provided: {crop}"
        )
        raise Exception(msg)
    crop = crop and cropbs is not None and cropbs is not False

    return coefs, ii, jj, R, Z, crop


def _get_bs2d_func_knots(knots, deg=None, returnas=None):

    returnas = _check_var(
        returnas, 'returnas',
        types=str,
        default='data',
        allowed=['ind', 'data'],
    )

    nkpbs = 2 + deg
    size = knots.size
    nbs = size - 1 + deg
    knots_per_bs = np.zeros((nkpbs, nbs), dtype=int)

    if deg == 0:
        knots_per_bs[:, :] = np.array([
            np.arange(0, size-1),
            np.arange(1, size),
        ])

    elif deg == 1:
        knots_per_bs[:, 1:-1] = np.array([
            np.arange(0, size-2),
            np.arange(1, size-1),
            np.arange(2, size),
        ])
        knots_per_bs[:, 0] = [0, 0, 1]
        knots_per_bs[:, -1] = [-2, -1, -1]

    elif deg == 2:
        knots_per_bs[:, 2:-2] = np.array([
            np.arange(0, size-3),
            np.arange(1, size-2),
            np.arange(2, size-1),
            np.arange(3, size),
        ])
        knots_per_bs[:, 0] = [0, 0, 0, 1]
        knots_per_bs[:, 1] = [0, 0, 1, 2]
        knots_per_bs[:, -2] = [-3, -2, -1, -1]
        knots_per_bs[:, -1] = [-2, -1, -1, -1]

    elif deg == 3:
        knots_per_bs[:, 3:-3] = np.array([
            np.arange(0, size-4),
            np.arange(1, size-3),
            np.arange(2, size-2),
            np.arange(3, size-1),
            np.arange(4, size),
        ])
        knots_per_bs[:, 0] = [0, 0, 0, 0, 1]
        knots_per_bs[:, 1] = [0, 0, 0, 1, 2]
        knots_per_bs[:, 2] = [0, 0, 1, 2, 3]
        knots_per_bs[:, -3] = [-4, -3, -2, -1, -1]
        knots_per_bs[:, -2] = [-3, -2, -1, -1, -1]
        knots_per_bs[:, -1] = [-2, -1, -1, -1, -1]

    if returnas == 'data':
        knots_per_bs = knots[knots_per_bs]

    return knots_per_bs


def _get_bs2d_func_cents(cents, deg=None, returnas=None):

    returnas = _check_var(
        returnas, 'returnas',
        types=str,
        default='data',
        allowed=['ind', 'data'],
    )

    nkpbs = 1 + deg
    size = cents.size
    nbs = size + deg
    cents_per_bs = np.zeros((nkpbs, nbs), dtype=int)

    if deg == 0:
        cents_per_bs[0, :] = np.arange(0, size)

    elif deg == 1:
        cents_per_bs[:, 1:-1] = np.array([
            np.arange(0, size-1),
            np.arange(1, size),
        ])
        cents_per_bs[:, 0] = [0, 0]
        cents_per_bs[:, -1] = [-1, -1]

    elif deg == 2:
        cents_per_bs[:, 2:-2] = np.array([
            np.arange(0, size-2),
            np.arange(1, size-1),
            np.arange(2, size),
        ])
        cents_per_bs[:, 0] = [0, 0, 0]
        cents_per_bs[:, 1] = [0, 0, 1]
        cents_per_bs[:, -2] = [-2, -1, -1]
        cents_per_bs[:, -1] = [-1, -1, -1]

    elif deg == 3:
        cents_per_bs[:, 3:-3] = np.array([
            np.arange(0, size-3),
            np.arange(1, size-2),
            np.arange(2, size-1),
            np.arange(3, size),
        ])
        cents_per_bs[:, 0] = [0, 0, 0, 0]
        cents_per_bs[:, 1] = [0, 0, 0, 1]
        cents_per_bs[:, 2] = [0, 0, 1, 2]
        cents_per_bs[:, -3] = [-3, -2, -1, -1]
        cents_per_bs[:, -2] = [-2, -1, -1, -1]
        cents_per_bs[:, -1] = [-1, -1, -1, -1]

    if returnas == 'data':
        cents_per_bs = cents[cents_per_bs]

    return cents_per_bs


def _get_bs2d_func_max(Rknots=None, Zknots=None, deg=None):

    knots_per_bs_R = _get_bs2d_func_knots(Rknots, deg=deg)
    knots_per_bs_Z = _get_bs2d_func_knots(Zknots, deg=deg)
    nbkbs = knots_per_bs_R.shape[0]

    if nbkbs % 2 == 0:
        ii = int(nbkbs/2)
        Rbs_cent = np.mean(knots_per_bs_R[ii-1:ii+1, :], axis=0)
        Zbs_cent = np.mean(knots_per_bs_Z[ii-1:ii+1, :], axis=0)
        if deg == 2:
            Rbs_cent[:deg] = [Rknots[0], 0.5*(Rknots[0] + Rknots[1])]
            Rbs_cent[-deg:] = [0.5*(Rknots[-2] + Rknots[-1]), Rknots[-1]]
            Zbs_cent[:deg] = [Zknots[0], 0.5*(Zknots[0] + Zknots[1])]
            Zbs_cent[-deg:] = [0.5*(Zknots[-2] + Zknots[-1]), Zknots[-1]]

    else:
        ii = int((nbkbs-1)/2)
        Rbs_cent = knots_per_bs_R[ii, :]
        Zbs_cent = knots_per_bs_Z[ii, :]
        if deg == 1:
            Rbs_cent[:deg] = Rknots[0]
            Rbs_cent[-deg:] = Rknots[-1]
            Zbs_cent[:deg] = Zknots[0]
            Zbs_cent[-deg:] = Zknots[-1]
        elif deg == 3:
            Rbs_cent[:deg] = [Rknots[0], 0.5*(Rknots[0]+Rknots[1]), Rknots[1]]
            Rbs_cent[-deg:] = [
                Rknots[-2], 0.5*(Rknots[-2]+Rknots[-1]), Rknots[-1],
            ]
            Zbs_cent[:deg] = [Zknots[0], 0.5*(Zknots[0]+Zknots[1]), Zknots[1]]
            Zbs_cent[-deg:] = [
                Zknots[-2], 0.5*(Zknots[-2]+Zknots[-1]), Zknots[-1],
            ]

    return Rbs_cent, Zbs_cent


def get_bs2d_RZ(deg=None, Rknots=None, Zknots=None):

    # ----------------
    # get knots per bspline, nb of bsplines...

    knots_per_bs_R = _get_bs2d_func_knots(Rknots, deg=deg, returnas='data')
    knots_per_bs_Z = _get_bs2d_func_knots(Zknots, deg=deg, returnas='data')
    nbkbs = knots_per_bs_R.shape[0]
    shapebs = (knots_per_bs_R.shape[1], knots_per_bs_Z.shape[1])

    # ----------------
    # get centers of bsplines

    Rbs_cent, Zbs_cent = _get_bs2d_func_max(
        Rknots=Rknots, Zknots=Zknots, deg=deg,
    )
    return shapebs, Rbs_cent, Zbs_cent, knots_per_bs_R, knots_per_bs_Z

def get_bs2d_func(
    deg=None,
    Rknots=None,
    Zknots=None,
    shapebs=None,
    knots_per_bs_R=None,
    knots_per_bs_Z=None,
):

    # ----------------
    # Pre-compute bsplines basis elements

    lbr = [
        scpinterp.BSpline.basis_element(
            knots_per_bs_R[:, ii],
            extrapolate=False,
        )
        for ii in range(shapebs[0])
    ]
    lbz = [
        scpinterp.BSpline.basis_element(
            knots_per_bs_Z[:, jj],
            extrapolate=False,
        )
        for jj in range(shapebs[1])
    ]

    RectBiv = [[None for jj in range(shapebs[1])] for ii in range(shapebs[0])]
    for ii in range(shapebs[0]):
        for jj in range(shapebs[1]):
            def func(rr, zz, coefs=None, br=lbr[ii], bz=lbz[jj]):
                if hasattr(coefs, '__iter__'):
                    if rr.ndim == 1:
                        val = coefs[:, None] * (br(rr)*bz(zz))[None, ...]
                    else:
                        val = coefs[:, None, None] * (br(rr)*bz(zz))[None, ...]
                else:
                    val = coefs * br(rr)*bz(zz)
                return val
            RectBiv[ii][jj] = func

    # ----------------
    # Define functions

    def RectBiv_details(
        R,
        Z,
        coefs=None,
        ii=None,
        jj=None,
        shapebs=shapebs,
        RectBiv=RectBiv,
        cropbs=None,
        crop=None,
    ):
        """ Return the value for each point for each bspline """

        coefs, ii, jj, R, Z, crop = _get_bs2d_func_check(
            coefs=coefs,
            ii=ii,
            jj=jj,
            R=R,
            Z=Z,
            shapebs=shapebs,
            crop=crop,
            cropbs=cropbs,
        )
        nt = 1 if np.isscalar(coefs) else coefs.shape[0]
        shapepts = R.shape

        if ii is None:
            shape = tuple(np.r_[nt, shapepts, shapebs])
            val = np.full(shape, np.nan)

            if crop:
                if np.isscalar(coefs):
                    for ii in range(shapebs[0]):
                        if not np.any(cropbs[ii, :]):
                            continue
                        for jj in range(shapebs[1]):
                            if cropbs[ii, jj]:
                                val[..., ii, jj] = RectBiv[ii][jj](
                                    R,
                                    Z,
                                    coefs=coefs,
                                )
                else:
                    for ii in range(shapebs[0]):
                        if not np.any(cropbs[ii, :]):
                            continue
                        for jj in range(shapebs[1]):
                            if cropbs[ii, jj]:
                                val[..., ii, jj] = RectBiv[ii][jj](
                                    R,
                                    Z,
                                    coefs=coefs[:, ii, jj],
                                )

            else:
                if np.isscalar(coefs):
                    for ii in range(shapebs[0]):
                        for jj in range(shapebs[1]):
                            val[..., ii, jj] = RectBiv[ii][jj](
                                R,
                                Z,
                                coefs=coefs,
                            )
                else:
                    for ii in range(shapebs[0]):
                        for jj in range(shapebs[1]):
                            val[..., ii, jj] = RectBiv[ii][jj](
                                R,
                                Z,
                                coefs=coefs[:, ii, jj],
                            )
        else:
            if crop and cropbs[ii, jj]:
                if np.isscalar(coefs):
                    val = RectBiv[ii][jj](R, Z, coefs=coefs)
                else:
                    val = RectBiv[ii][jj](R, Z, coefs=coefs[:, ii, jj])
            else:
                val = np.nan
        return val

    def RectBiv_sum(
        R,
        Z,
        coefs=None,
        shapebs=shapebs,
        knots_per_bs_R=knots_per_bs_R,
        knots_per_bs_Z=knots_per_bs_Z,
        RectBiv=RectBiv,
        crop=None,
        cropbs=None,
    ):
        """ Return the value for each point summed on all bsplines """

        coefs, _, _, r, z, crop = _get_bs2d_func_check(
            coefs=coefs,
            R=R,
            Z=Z,
            shapebs=shapebs,
            crop=crop,
            cropbs=cropbs,
        )
        nt = 1 if np.isscalar(coefs) else coefs.shape[0]
        shapepts = r.shape

        shape = tuple(np.r_[nt, shapepts])
        val = np.zeros(shape, dtype=float)
        if crop:
            if np.isscalar(coefs):
                for ii in range(shapebs[0]):
                    if not np.any(cropbs[ii, :]):
                        continue
                    indok0 = (
                        (knots_per_bs_R[0, ii] <= R)
                        & (R <= knots_per_bs_R[-1, ii])
                    )
                    for jj in range(shapebs[1]):
                        if cropbs[ii, jj]:
                            indok = (
                                indok0
                                & (knots_per_bs_Z[0, jj] <= Z)
                                & (Z <= knots_per_bs_Z[-1, jj])
                            )
                            val[:, indok] += RectBiv[ii][jj](
                                R[indok],
                                Z[indok],
                                coefs=coefs,
                            )

            else:
                for ii in range(shapebs[0]):
                    if not np.any(cropbs[ii, :]):
                        continue
                    indok0 = (
                        (knots_per_bs_R[0, ii] <= R)
                        & (R <= knots_per_bs_R[-1, ii])
                    )
                    for jj in range(shapebs[1]):
                        if cropbs[ii, jj]:
                            indok = (
                                indok0
                                & (knots_per_bs_Z[0, jj] <= Z)
                                & (Z <= knots_per_bs_Z[-1, jj])
                            )
                            val[:, indok] += RectBiv[ii][jj](
                                R[indok],
                                Z[indok],
                                coefs=coefs[:, ii, jj],
                            )

        else:
            if np.isscalar(coefs):
                for ii in range(shapebs[0]):
                    indok0 = (
                        (knots_per_bs_R[0, ii] <= R)
                        & (R <= knots_per_bs_R[-1, ii])
                    )
                    for jj in range(shapebs[1]):
                        indok = (
                            indok0
                            & (knots_per_bs_Z[0, jj] <= Z)
                            & (Z <= knots_per_bs_Z[-1, jj])
                        )
                        val[:, indok] += RectBiv[ii][jj](
                            R[indok],
                            Z[indok],
                            coefs=coefs,
                        )

            else:
                for ii in range(shapebs[0]):
                    indok0 = (
                        (knots_per_bs_R[0, ii] <= R)
                        & (R <= knots_per_bs_R[-1, ii])
                    )
                    for jj in range(shapebs[1]):
                        indok = (
                            indok0
                            & (knots_per_bs_Z[0, jj] <= Z)
                            & (Z <= knots_per_bs_Z[-1, jj])
                        )
                        val[:, indok] += RectBiv[ii][jj](
                            R[indok],
                            Z[indok],
                            coefs=coefs[:, ii, jj],
                        )
        return val

    return RectBiv_details, RectBiv_sum
