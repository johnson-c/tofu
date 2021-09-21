# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
#
from libc.math cimport sqrt as c_sqrt
from libc.math cimport NAN as CNAN
from libc.math cimport pi as c_pi
from libc.stdlib cimport free
from libc.stdlib cimport malloc
from cpython.array cimport clone
from cpython.array cimport array
from cython.parallel import prange
from cython.parallel cimport parallel
#
cdef double _VSMALL = 1.e-9
cdef double _SMALL = 1.e-6
cdef double _TWOPI = 2.0 * c_pi


# ==============================================================================
# =  Point in path
# ==============================================================================
cdef inline bint is_point_in_path(const int nvert,
                                  const double* vertx,
                                  const double* verty,
                                  const double testx,
                                  const double testy) nogil:
    """
    Computes if a point of coordiates (testx, testy) is in the polygon defined
    by nvert vertices of coordinates (vertx, verty).

    !! -- WARNING: the poly should be CLOSED and nvert = vpoly.shape[1]-1 -- !!
    Params
    ======
        nvert : int
           number of DIFFERENT vertices in polygon
        vertx : double array
           x-coordinates of polygon
        verty : double array
           y-coordinate of polygon
        testx : double
           x-coordinate of point to be tested if in or out of polygon
        testy : double
           y-coordinate of point to be tested if in or out of polygon
    Returns
    =======
        bool : True if point is in the polygon, else False
    """
    cdef int i
    cdef bint c = 0
    for i in range(nvert):
        if ( ((verty[i]>testy) != (verty[i+1]>testy)) and
            (testx < (vertx[i+1]-vertx[i]) * (testy-verty[i])
             / (verty[i+1]-verty[i]) + vertx[i]) ):
            c = not c
    return c


cdef inline int is_point_in_path_vec(const int nvert,
                                     const double* vertx,
                                     const double* verty,
                                     const int npts,
                                     const double* testx,
                                     const double* testy,
                                     int* is_in_path) nogil:
    """
    Computes if a series of points of coordiates (testx[ii], testy[ii]) is in
    the polygon defined by nvert vertices of coordinates (vertx, verty)
    Params
    ======
        nvert : int
           number of vertices in polygon
        vertx : double array
           x-coordinates of polygon
        verty : double array
           y-coordinate of polygon
        npts : int
           number of points to test if in poly or not
        testx : double array
           x-coordinates of points to be tested if in or out of polygon
        testy : double array
           y-coordinates of points to be tested if in or out of polygon
        is_in_path : bint array
           True if point is in the polygon, else False
    Returns
    =======
     The number of "true"
    """
    cdef int ii
    cdef int tot_true = 0
    cdef bint c = 0
    for ii in range(npts):
        c = is_point_in_path(nvert, vertx, verty, testx[ii], testy[ii])
        is_in_path[ii] = c
        tot_true += c*1
    return tot_true


# ==============================================================================
# =  Computing inverse of vector and sign of each element
# ==============================================================================
cdef inline void compute_inv_and_sign(const double[3] ray_vdir,
                                      int[3] sign,
                                      double[3] inv_direction) nogil:
    """
    Computes the inverse direction and sign of each coordinate of a vector.
    Params
    ======
    ray_vdir : (3) double array
       direction of the LOS
    sign : (3) int array <INOUT>
       for each coordinate of the direction, indicates if negative or not
       If sign[i] = 1, ray_vdir[i] < 0, else sign[i] = 0
    inv_direction : (3) double array
       Inverse on each axis of direction of LOS
    """
    # computing sign and direction
    for  ii in range(3):
        if ray_vdir[ii] * ray_vdir[ii] < _VSMALL:
            inv_direction[ii] = 1. / _VSMALL
        else:
            inv_direction[ii] = 1. / ray_vdir[ii]
        if ray_vdir[ii] < 0.:
            sign[ii] = 1
        else:
            sign[ii] = 0
    return


# ==============================================================================
# =  Computing Hypotenuse
# =============================================================================
cdef inline array compute_hypot(const double[::1] xpts, const double[::1] ypts,
                                int npts=-1):
    cdef int ii
    cdef array hypot
    cdef double* ptr_hypot
    if npts == -1:
        npts  = xpts.shape[0]
    hypot = clone(array('d'), npts, False)
    ptr_hypot = hypot.data.as_doubles
    with nogil:
        for ii in range(npts):
            ptr_hypot[ii] = c_sqrt(xpts[ii] * xpts[ii] + ypts[ii] * ypts[ii])
    return hypot


cdef inline double comp_min_hypot(const double[::1] xpts,
                                  const double[::1] ypts,
                                  int npts=-1) nogil:
    cdef int ii
    cdef double tmp
    cdef double hypot = xpts[0]*xpts[0] + ypts[0]*ypts[0]
    if npts == -1:
        npts  = xpts.shape[0]
    for ii in range(npts):
        tmp = xpts[ii]*xpts[ii] + ypts[ii]*ypts[ii]
        if tmp < hypot:
            hypot = tmp
    return c_sqrt(hypot)


cdef inline double comp_min(double[::1] vec, int npts) nogil:
    cdef int ii
    cdef double res = vec[0]
    for ii in range(1,npts):
        if vec[ii] < res:
            res = vec[ii]
    return res


# ==============================================================================
# == VECTOR CALCULUS HELPERS
# ==============================================================================
cdef inline void compute_cross_prod(const double[3] vec_a,
                                    const double[3] vec_b,
                                    double[3] res) nogil:
    res[0] = vec_a[1]*vec_b[2] - vec_a[2]*vec_b[1]
    res[1] = vec_a[2]*vec_b[0] - vec_a[0]*vec_b[2]
    res[2] = vec_a[0]*vec_b[1] - vec_a[1]*vec_b[0]
    return


cdef inline double compute_dot_prod(const double[3] vec_a,
                                    const double[3] vec_b) nogil:
    return vec_a[0] * vec_b[0] + vec_a[1] * vec_b[1] + vec_a[2] * vec_b[2]


cdef inline void compute_dot_cross_vec(const double[:, ::1] lvec_a,
                                       const double[:, ::1] lvec_b,
                                       double[:, ::1] cross_p,
                                       double[::1] dot_p,
                                       const int npts,
                                       const int num_threads,
                                       ) nogil:
    cdef int ii
    cdef double vec1[3]
    cdef double vec2[3]
    cdef double vec3[3]

    with nogil, parallel(num_threads=num_threads):
        for ii in prange(npts):
            vec1[0] = lvec_a[0, ii]
            vec1[1] = lvec_a[1, ii]
            vec1[2] = lvec_a[2, ii]
            vec2[0] = lvec_b[0, ii]
            vec2[1] = lvec_b[1, ii]
            vec2[2] = lvec_b[2, ii]
            compute_cross_prod(vec1, vec2, &vec3[0])
            cross_p[0, ii] = vec3[0]
            cross_p[1, ii] = vec3[1]
            cross_p[2, ii] = vec3[2]
            dot_p[ii] = compute_dot_prod(vec1, vec2)
    return

cdef inline double compute_norm(const double[3] vec) nogil:
    return c_sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])


cdef inline double compute_g(double s, double m2b2, double rm0sqr,
                             double m0sqr, double b1sqr) nogil:
    return s + m2b2 - rm0sqr * s / c_sqrt(m0sqr * s * s + b1sqr)


cdef inline double compute_bisect(double m2b2, double rm0sqr,
                                  double m0sqr, double b1sqr,
                                  double smin, double smax) nogil:
    cdef int max_iterations = 10000
    cdef double root = 0.
    root = compute_find(m2b2, rm0sqr, m0sqr, b1sqr,
                        smin, smax, -1.0, 1.0, max_iterations, root)
    return root


cdef inline double compute_find(double m2b2, double rm0sqr,
                                double m0sqr, double b1sqr,
                                double t0, double t1, double f0, double f1,
                                int max_iterations, double root) nogil:
    cdef double fm, product

    if t0 < t1:
        # Test the endpoints to see whether F(t) is zero.
        if f0 == 0.:
            root = t0
            return root
        if f1 == 0.:
            root = t1
            return root
        if f0*f1 > 0.:
            # It is not known whether the interval bounds a root.
            return root
        for _ in range(2, max_iterations + 1):
            root = 0.5 * (t0 + t1)
            if root == t0 or root == t1:
                # The numbers t0 and t1 are consecutive floating-point
                # numbers.
                break
            fm = compute_g(root, m2b2, rm0sqr, m0sqr, b1sqr)
            product = fm * f0
            if product < 0.:
                t1 = root
                f1 = fm
            elif product > 0.:
                t0 = root
                f0 = fm
            else:
                break
        return root
    else:
        return root


# ==============================================================================
# =  Tiling
# ==============================================================================
cdef inline void tile_3_to_2d(double v0, double v1, double v2,
                              int npts, double[:,::1] res) nogil:
    """
    This function will probably not be very useful but might be used for
    inspiration (if indeed faster than using numpy in cython).
    It creates an array of shape (3, npts) as such :
        [v0, ... v0]
        [v1, ... v1]
        [v2, ... v2]
    Equivalent to :
       tab = np.tile(np.r_[v0,v1,v2], (npts,1)).T
    """
    cdef int ii
    for ii in range(npts):
        res[0,ii] = v0
        res[1,ii] = v1
        res[2,ii] = v2
    return


# ==============================================================================
# =  Polygon helpers
# ==============================================================================
cdef inline int find_ind_lowerright_corner(const double[::1] xpts,
                                           const double[::1] ypts,
                                           int npts) nogil:
    cdef int ii
    cdef int res = 0
    cdef double minx = xpts[0]
    cdef double miny = ypts[0]
    for ii in range(1,npts):
        if miny > ypts[ii]:
            minx = xpts[ii]
            miny = ypts[ii]
            res = ii
        elif miny == ypts[ii]:
            if minx < xpts[ii]:
                minx = xpts[ii]
                miny = ypts[ii]
                res = ii
    return res


cdef inline void find_centroid_tri(const double[3] xpts,
                                   const double[3] ypts,
                                   const double[3] zpts,
                                   double[:] centroid) nogil:
    centroid[0] = (xpts[0] + xpts[1] + xpts[2]) / 3.
    centroid[1] = (ypts[0] + ypts[1] + ypts[2]) / 3.
    centroid[2] = (zpts[0] + zpts[1] + zpts[2]) / 3.
    return


cdef inline void find_centroids_ltri(const double[:, :, ::1] poly_coords,
                                     const long** ltri,
                                     const long* lnvert,
                                     const int npoly,
                                     const int num_threads,
                                     double[:, ::1] centroid) nogil:
    cdef int ipol
    cdef int itri
    cdef int wim1
    cdef int wi
    cdef int wip1
    cdef double[3] xtri
    cdef double[3] ytri
    cdef double[3] ztri

    with nogil, parallel(num_threads=num_threads):
        for ipol in prange(npoly):
            for itri in range(lnvert[ipol] - 2):
                wim1 = ltri[ipol][itri*3]
                wi   = ltri[ipol][itri*3+1]
                wip1 = ltri[ipol][itri*3+2]
                xtri[0] = poly_coords[ipol, 0, wim1]
                ytri[0] = poly_coords[ipol, 1, wim1]
                ztri[0] = poly_coords[ipol, 2, wim1]
                xtri[1] = poly_coords[ipol, 0, wi]
                ytri[1] = poly_coords[ipol, 1, wi]
                ztri[1] = poly_coords[ipol, 2, wi]
                xtri[2] = poly_coords[ipol, 0, wip1]
                ytri[2] = poly_coords[ipol, 1, wip1]
                ztri[2] = poly_coords[ipol, 2, wip1]
                find_centroid_tri(xtri, ytri, ztri,
                                  centroid[:, ipol + itri * npoly])
    return



cdef inline void find_centroids_GB_GC_ltri(const double** poly_coords,
                                           const long** ltri,
                                           const long* lnvert,
                                           const int npoly,
                                           const int num_threads,
                                           double[:, ::1] centroid,
                                           double[:, ::1] vec_GB,
                                           double[:, ::1] vec_GC,
                                           ) nogil:
    cdef int wi
    cdef int wip1
    cdef int wim1
    cdef int ipol
    cdef int itri
    cdef int iglob
    cdef double[3] xtri
    cdef double[3] ytri
    cdef double[3] ztri

    with nogil, parallel(num_threads=num_threads):
        for ipol in prange(npoly):
            for itri in range(lnvert[ipol] - 2):
                wim1 = ltri[ipol][itri*3]
                wi   = ltri[ipol][itri*3+1]
                wip1 = ltri[ipol][itri*3+2]
                xtri[0] = poly_coords[ipol][0 * lnvert[ipol] + wim1]
                ytri[0] = poly_coords[ipol][1 * lnvert[ipol] + wim1]
                ztri[0] = poly_coords[ipol][2 * lnvert[ipol] + wim1]
                xtri[1] = poly_coords[ipol][0 * lnvert[ipol] + wi]
                ytri[1] = poly_coords[ipol][1 * lnvert[ipol] + wi]
                ztri[1] = poly_coords[ipol][2 * lnvert[ipol] + wi]
                xtri[2] = poly_coords[ipol][0 * lnvert[ipol] + wip1]
                ytri[2] = poly_coords[ipol][1 * lnvert[ipol] + wip1]
                ztri[2] = poly_coords[ipol][2 * lnvert[ipol] + wip1]
                iglob = ipol + itri * npoly
                find_centroid_tri(xtri, ytri, ztri,
                                  centroid[:, iglob])
                vec_GB[0, iglob] = xtri[1] - centroid[0, iglob]
                vec_GB[1, iglob] = ytri[1] - centroid[1, iglob]
                vec_GB[2, iglob] = ztri[1] - centroid[2, iglob]
                vec_GC[0, iglob] = xtri[2] - centroid[0, iglob]
                vec_GC[1, iglob] = ytri[2] - centroid[1, iglob]
                vec_GC[2, iglob] = ztri[2] - centroid[2, iglob]
    return

# ==============================================================================
# =  Distance
# ==============================================================================
cdef inline void compute_dist_pt_arr(const double pt0, const double pt1,
                                     const double pt2, int npts,
                                     const double* vec,
                                     double* dist) nogil:
    """
    Compute the distance between the point P = [pt0, pt1, pt2] and each point
    Q_i, where vec = {Q_0, Q_1, ..., Q_npts-1}
    """
    cdef int ii
    for ii in range(0, npts):
        dist[ii] = c_sqrt(
              (pt0 - vec[0 * npts +  ii]) * (pt0 - vec[0 * npts + ii])
            + (pt1 - vec[1 * npts +  ii]) * (pt1 - vec[1 * npts + ii])
            + (pt2 - vec[2 * npts +  ii]) * (pt2 - vec[2 * npts + ii]))
    return


cdef inline void compute_dist_pt_vec(const double pt0, const double pt1,
                                     const double pt2, int npts,
                                     const double[:, ::1] vec,
                                     double* dist) nogil:
    """
    Compute the distance between the point P = [pt0, pt1, pt2] and each point
    Q_i, where vec = {Q_0, Q_1, ..., Q_npts-1}
    """
    cdef int ii
    for ii in range(0, npts):
        dist[ii] = c_sqrt((pt0 - vec[0, ii]) * (pt0 - vec[0, ii])
                          + (pt1 - vec[1, ii]) * (pt1 - vec[1, ii])
                          + (pt2 - vec[2, ii]) * (pt2 - vec[2, ii]))
    return


cdef inline void compute_vec_ass_tri(const double pt0, const double pt1,
                                     const double pt2, int npts,
                                     const double[:, ::1] ptG,
                                     const double[:, ::1] poly_norm,
                                     const double[:, ::1] cross_bc,
                                     const double[:, ::1] vecb,
                                     const double[:, ::1] vecc,
                                     double* side_of_poly,
                                     double* num,
                                     double* dot_Gb,
                                     double* dot_Gc,
                                     double* normG2) nogil:
    """
    Computes:
       - numerator of triangle SA comp : 3 G \dot (b \cross c)
       - G \dot b = OG \dot Gb
       - G \dot c = OG \dot Gc
       - (norm G)**2 = G \dot G = OG \dot \OG
    ptG are the coordinates of all G, centroids of all triangles
    pt0, pt1, pt2 are the coordinates of O
    cross_bc are b x c for all triangles
    vecb = \vec Gb
    vecc = \vec Gc
    """
    cdef int ii
    cdef double[3] vec_OG

    for ii in range(npts):
        vec_OG[0] = ptG[0, ii] - pt0
        vec_OG[1] = ptG[1, ii] - pt1
        vec_OG[2] = ptG[2, ii] - pt2
        normG2[ii] = (vec_OG[0] * vec_OG[0]
                      + vec_OG[1] * vec_OG[1]
                      + vec_OG[2] * vec_OG[2])
        num[ii] = 3.0 * (  vec_OG[0] * cross_bc[0, ii]
                         + vec_OG[1] * cross_bc[1, ii]
                         + vec_OG[2] * cross_bc[2, ii])
        dot_Gb[ii] = (vec_OG[0]   * vecb[0, ii]
                      + vec_OG[1] * vecb[1, ii]
                      + vec_OG[2] * vecb[2, ii])
        dot_Gc[ii] = (vec_OG[0]   * vecc[0, ii]
                      + vec_OG[1] * vecc[1, ii]
                      + vec_OG[2] * vecc[2, ii])
        side_of_poly[ii] = (vec_OG[0]   * poly_norm[ii, 0]
                            + vec_OG[1] * poly_norm[ii, 1]
                            + vec_OG[2] * poly_norm[ii, 2])
    return


cdef inline void compute_dist_vec_vec(const int npts1, const int npts2,
                                      const double[:, ::1] vec1,
                                      const double[:, ::1] vec2,
                                      double[:, ::1] dist) nogil:
    """
    Compute the distance between each point P_i and each point
    Q_i, where vec1 = {P_0, P_1, ..., P_npts1-1} and
    vec2 = {Q_0, Q_1, ..., Q_npts2-1}
    """
    cdef int ii, jj

    for ii in range(npts1):
        for jj in range(npts2):
            dist[ii,jj] = c_sqrt((vec1[0, ii] - vec2[0, jj])
                                 * (vec1[0,ii] - vec2[0, jj])
                                 + (vec1[1,ii] - vec2[1, jj])
                                 * (vec1[1,ii] - vec2[1, jj])
                                 + (vec1[2,ii] - vec2[2, jj])
                                 * (vec1[2,ii] - vec2[2, jj]))
    return


cdef inline void compute_diff_div(const double[:, ::1] vec1,
                                  const double[:, ::1] vec2,
                                  const double* div,
                                  const int npts,
                                  double[:, ::1] res) nogil:
    """
    Computes :
      res = (vec1 - vec2) / div
    """
    cdef int ii
    cdef double invd
    for ii in range(npts):
        invd = CNAN
        if div[ii] != 0. :
            invd = 1./div[ii]
        res[0, ii] = (vec1[0,ii] - vec2[0,ii]) * invd
        res[1, ii] = (vec1[1,ii] - vec2[1,ii]) * invd
        res[2, ii] = (vec1[2,ii] - vec2[2,ii]) * invd
    return


# ==============================================================================
# == Matrix sum (np.sum)
# ==============================================================================
cdef inline void sum_by_rows(double *orig, double *out,
                             int n_rows, int n_cols) nogil:
    cdef int b, i, j
    cdef int left
    cdef int max_r = 8
    cdef int n_blocks = n_rows/max_r
    cdef double* res
    # .. initialization
    res = <double*>malloc(max_r*sizeof(double))
    for b in prange(n_blocks):
        for i in range(max_r):
            res[i] = 0
        for j in range(n_cols):
            for i in range(max_r): #calculate sum for max_r-rows simultaneously
                res[i]+=orig[(b*max_r+i)*n_cols+j]
        for i in range(max_r):
            out[b*max_r+i]=res[i]
    # left_overs:
    left = n_rows - n_blocks*max_r
    for i in prange(max_r):
        res[i] = 0
    for j in prange(n_cols):
        for i in range(left): #calculate sum for left rows simultaneously
            res[i]+=orig[(n_blocks*max_r)*n_cols+j]
    for i in prange(left):
        out[n_blocks*max_r+i]=res[i]
    free(res)
    return


cdef inline long sum_naive_int(long* orig, int n_cols) nogil:
    cdef int ii
    cdef long out

    with nogil:
        out = 0
        for ii in prange(n_cols):
            out += orig[ii]
    return out
