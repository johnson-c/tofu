# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
#
################################################################################
# Utility functions for Ray-tracing
################################################################################

# ==============================================================================
# =  3D Bounding box (not Toroidal)
# ==============================================================================
cdef void compute_3d_bboxes(double** vignett_poly,
                                   long* lnvert,
                                   int nvign,
                                   double* lbounds,
                                   int num_threads) nogil
cdef void comp_bbox_poly3d(int nvert,
                                  double* vertx,
                                  double* verty,
                                  double* vertz,
                                  double[6] bounds) nogil

# ==============================================================================
# =  Computation of Bounding Boxes (in toroidal configuration)
# ==============================================================================
cdef void comp_bbox_poly_tor(int nvert,
                                    double* vertr,
                                    double* vertz,
                                    double[6] bounds) nogil

cdef void comp_bbox_poly_tor_lim(int nvert,
                                        double* vertr,
                                        double* vertz,
                                        double[6] bounds,
                                        double lmin, double lmax) nogil

cdef void coordshift_simple1d(double[3] pts, bint in_is_cartesian,
                                     double CrossRef, double cos_phi,
                                     double sin_phi) nogil

# ==============================================================================
# =  Raytracing basic tools: intersection ray and axis aligned bounding box
# ==============================================================================
cdef bint inter_ray_aabb_box(const int[3] sign,
                                    const double[3] inv_direction,
                                    const double[6] bounds,
                                    const double[3] ds,
                                    bint countin) nogil

# ==============================================================================
# =  Raytracing basic tools: intersection ray and triangle (in 3d space)
# ==============================================================================
cdef bint inter_ray_triangle(const double[3] ray_orig,
                                    const double[3] ray_vdir,
                                    const double* vert0,
                                    const double* vert1,
                                    const double* vert2) nogil

# ==============================================================================
# =  Raytracing on a Torus
# ==============================================================================
cdef void raytracing_inout_struct_tor(const int num_los,
                                             const double[:,::1] ray_vdir,
                                             const double[:,::1] ray_orig,
                                             double[::1] coeff_inter_out,
                                             double[::1] coeff_inter_in,
                                             double[::1] vperp_out,
                                             const long[::1] lstruct_nlim,
                                             int[::1] ind_inter_out,
                                             const bint forbid0,
                                             const bint forbidbis,
                                             const double rmin,
                                             const double rmin2,
                                             const double crit2_base,
                                             const int nstruct_lim,
                                             const double* lbounds,
                                             const double* langles,
                                             const int* lis_limited,
                                             const long* lnvert,
                                             const long* lsz_lim,
                                             const double* lstruct_polyx,
                                             const double* lstruct_polyy,
                                             const double* lstruct_normx,
                                             const double* lstruct_normy,
                                             const double eps_uz,
                                             const double eps_vz,
                                             const double eps_a,
                                             const double eps_b,
                                             const double eps_plane,
                                             const int num_threads,
                                             const bint is_out_struct) nogil

# ------------------------------------------------------------------
cdef bint comp_inter_los_vpoly(const double[3] ray_orig,
                                      const double[3] ray_vdir,
                                      const double* lpolyx,
                                      const double* lpolyy,
                                      const double* normx,
                                      const double* normy,
                                      const int nvert,
                                      const bint lim_is_none,
                                      const double lim_min,
                                      const double lim_max,
                                      const bint forbidbis,
                                      const double upscaDp, const double upar2,
                                      const double dpar2, const double invuz,
                                      const double s1x,   const double s1y,
                                      const double s2x, const double s2y,
                                      const double crit2, const double eps_uz,
                                      const double eps_vz, const double eps_a,
                                      const double eps_b, const double eps_pln,
                                      const bint is_in_struct,
                                      double[1] kpin_loc, double[1] kpout_loc,
                                      int[1] ind_loc, double[3] vperpin) nogil

# ==============================================================================
# =  Raytracing on a Cylinder (Linear case)
# ==============================================================================
cdef void raytracing_inout_struct_lin(const int Nl,
                                             const double[:,::1] Ds,
                                             const double [:,::1] us,
                                             const int Ns,
                                             const double* polyx_tab,
                                             const double* polyy_tab,
                                             const double* normx_tab,
                                             const double* normy_tab,
                                             const double L0,
                                             const double L1,
                                             double[::1] kin_tab,
                                             double[::1] kout_tab,
                                             double[::1] vperpout_tab,
                                             int[::1] indout_tab,
                                             const double EpsPlane,
                                             const int ind_struct,
                                             const int ind_lim_struct) nogil

cdef void compute_inout_tot(const double[:, ::1] ray_orig,
                            const double[:, ::1] ray_vdir,
                            const double[:, ::1] ves_poly,
                            const double[:, ::1] ves_norm,
                            const long[::1] lstruct_nlim,
                            const double[::1] ves_lims,
                            const double[::1] lstruct_polyx,
                            const double[::1] lstruct_polyy,
                            list lstruct_lims,
                            const double[::1] lstruct_normx,
                            const double[::1] lstruct_normy,
                            const long[::1] lnvert,
                            const int nstruct_tot,
                            const int nstruct_lim,
                            const int sz_ves_lims,
                            const double min_poly_r,
                            const double rmin,
                            const double eps_uz, const double eps_a,
                            const double eps_vz, const double eps_b,
                            const double eps_plane, str ves_type,
                            const bint forbid, const int num_threads,
                            double[::1] coeff_inter_out,
                            double[::1] coeff_inter_in,
                            double[::1] vperp_out,
                            int[::1] ind_inter_out)

# ==============================================================================
# =  Raytracing on a Torus only KMin and KMax
# ==============================================================================
cdef void raytracing_minmax_struct_tor(int num_los,
                                             double[:,::1] ray_vdir,
                                             double[:,::1] ray_orig,
                                             double* coeff_inter_out,
                                             double* coeff_inter_in,
                                             bint forbid0, bint forbidbis,
                                             double rmin, double rmin2,
                                             double crit2_base,
                                             int npts_poly,
                                             double* langles,
                                             bint is_limited,
                                             double* surf_polyx,
                                             double* surf_polyy,
                                             double* surf_normx,
                                             double* surf_normy,
                                             double eps_uz, double eps_vz,
                                             double eps_a, double eps_b,
                                             double eps_plane,
                                             int num_threads) nogil

# ==============================================================================
# =  Raytracing on a Cylinder only KMin and KMax
# ==============================================================================
cdef void raytracing_minmax_struct_lin(int Nl,
                                             double[:,::1] Ds,
                                             double [:,::1] us,
                                             int Ns,
                                             double* polyx_tab,
                                             double* polyy_tab,
                                             double* normx_tab,
                                             double* normy_tab,
                                             double L0, double L1,
                                             double* kin_tab,
                                             double* kout_tab,
                                             double EpsPlane) nogil

# ==============================================================================
# = Checking if points are visible
# ==============================================================================
cdef void is_visible_pt_vec(double pt0, double pt1, double pt2,
                                   double[:,::1] pts, int npts,
                                   double[:, ::1] ves_poly,
                                   double[:, ::1] ves_norm,
                                   double[::1] ind,
                                   double[::1] k,
                                   double[::1] ves_lims,
                                   long[::1] lstruct_nlim,
                                   double[::1] lstruct_polyx,
                                   double[::1] lstruct_polyy,
                                   list lstruct_lims,
                                   double[::1] lstruct_normx,
                                   double[::1] lstruct_normy,
                                   long[::1] lnvert,
                                   int nstruct_tot,
                                   int nstruct_lim,
                                   double rmin,
                                   double eps_uz, double eps_a,
                                   double eps_vz, double eps_b,
                                   double eps_plane, str ves_type,
                                   bint forbid, bint vis,
                                   bint test, int num_threads)

cdef void is_vis_mask(double[::1] ind, double* k,
                      double[::1] coeff_inter_out,
                      int npts,
                      bint vis) nogil

cdef void are_visible_vec_vec(double[:, ::1] pts1, int npts1,
                                     double[:,::1] pts2, int npts2,
                                     double[:, ::1] ves_poly,
                                     double[:, ::1] ves_norm,
                                     double[:, ::1] ind,
                                     double[::1] k,
                                     double[::1] ves_lims,
                                     long[::1] lstruct_nlim,
                                     double[::1] lstruct_polyx,
                                     double[::1] lstruct_polyy,
                                     list lstruct_lims,
                                     double[::1] lstruct_normx,
                                     double[::1] lstruct_normy,
                                     long[::1] lnvert,
                                     int nstruct_tot,
                                     int nstruct_lim,
                                     double rmin,
                                     double eps_uz, double eps_a,
                                     double eps_vz, double eps_b,
                                     double eps_plane, str ves_type,
                                     bint forbid, bint vis,
                                     bint test, int num_threads)
