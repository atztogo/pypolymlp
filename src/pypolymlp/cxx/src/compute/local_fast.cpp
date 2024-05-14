/****************************************************************************

        Copyright (C) 2024 Atsuto Seko
                seko@cms.mtl.kyoto-u.ac.jp

*****************************************************************************/

#include "compute/local_fast.h"
#include "time.h"
#include <chrono>


LocalFast::LocalFast(){}

LocalFast::LocalFast(const int& n_atom_i, 
                     const int& atom1_i, 
                     const int& type1_i,
                     const struct feature_params& fp_i,
                     const ModelParams& modelp){

    n_atom = n_atom_i, atom1 = atom1_i, type1 = type1_i, 
    fp = fp_i;
    n_type = fp.n_type;

    set_type_comb(modelp);

}

LocalFast::~LocalFast(){}

void LocalFast::set_type_comb(const ModelParams& modelp){

    type_comb = vector2i(fp.n_type, vector1i(fp.n_type));
    for (int type1 = 0; type1 < fp.n_type; ++type1){
        for (int type2 = 0; type2 < fp.n_type; ++type2){
            for (size_t i = 0; i < modelp.get_type_comb_pair().size(); ++i){
                const auto &tc = modelp.get_type_comb_pair()[i];
                if (tc[type1].size() > 0 and tc[type1][0] == type2){
                    type_comb[type1][type2] = i;
                    break;
                }
            }
        }
    }
}

/*
vector1d LocalFast::pair(const vector2d& dis_a){

    vector1d an(n_des, 0.0);

    int col;
    double dis;
    vector1d fn;

    int n_type_comb(0);
    for (const auto& tc: modelp.get_type_comb_pair()){
        if (tc[type1].size() > 0){
            const int type2 = tc[type1][0];
            for (size_t j = 0; j < dis_a[type2].size(); ++j){
                dis = dis_a[type2][j];
                get_fn_(dis, fp, fn);
                for (int n = 0; n < n_fn; ++n) {
                    col = n_type_comb * n_fn + n; 
                    an[col] += fn[n];
                }
            }
        }
        ++n_type_comb;
    }
    return an;
}

void LocalFast::pair_d(const vector2d& dis_a, 
                   const vector3d& diff_a, 
                   const vector2i& atom2_a,
                   vector1d& an, 
                   vector2d& an_dfx, 
                   vector2d& an_dfy, 
                   vector2d& an_dfz, 
                   vector2d& an_ds){

    an = vector1d(n_des, 0.0);
    an_dfx = an_dfy = an_dfz = vector2d(n_des, vector1d(n_atom, 0.0));
    an_ds = vector2d(n_des, vector1d(6, 0.0));

    int atom2,col;
    double dis,delx,dely,delz,valx,valy,valz;
    vector1d fn,fn_d;

    int n_type_comb(0);
    for (const auto& tc: modelp.get_type_comb_pair()){
        if (tc[type1].size() > 0){
            const int type2 = tc[type1][0];
            for (size_t j = 0; j < dis_a[type2].size(); ++j){
                dis = dis_a[type2][j];
                delx = diff_a[type2][j][0];
                dely = diff_a[type2][j][1];
                delz = diff_a[type2][j][2];
                atom2 = atom2_a[type2][j];
                get_fn_(dis, fp, fn, fn_d);
                for (int n = 0; n < n_fn; ++n){
                    col = n_type_comb * n_fn + n; 
                    an[col] += fn[n];
                    valx = fn_d[n] * delx / dis;
                    valy = fn_d[n] * dely / dis;
                    valz = fn_d[n] * delz / dis;
                    an_dfx[col][atom1] += valx;
                    an_dfy[col][atom1] += valy;
                    an_dfz[col][atom1] += valz;
                    an_dfx[col][atom2] -= valx;
                    an_dfy[col][atom2] -= valy;
                    an_dfz[col][atom2] -= valz;
                    an_ds[col][0] -= valx * delx;
                    an_ds[col][1] -= valy * dely;
                    an_ds[col][2] -= valz * delz;
                    an_ds[col][3] -= valx * dely;
                    an_ds[col][4] -= valy * delz;
                    an_ds[col][5] -= valz * delx;
                }
            }
        }
        ++n_type_comb;
    }
}
*/

void LocalFast::gtinv(const vector2d& dis_a, 
                      const vector3d& diff_a,
                      const FunctionFeatures& features,
                      vector1d& dn){

    const auto& prod_map = features.get_prod_map(type1);

    vector1dc anlmtc;
    compute_anlm(dis_a, diff_a, features, anlmtc);

    vector1d prod_anlmtc;
    compute_products_real(prod_map, anlmtc, prod_anlmtc);

    compute_linear_features(prod_anlmtc, features, dn);
}


void LocalFast::gtinv_d(const vector2d& dis_a, 
                        const vector3d& diff_a, 
                        const vector2i& atom2_a,
                        const FunctionFeatures& features,
                        vector1d& dn, 
                        vector2d& dn_dfx, 
                        vector2d& dn_dfy, 
                        vector2d& dn_dfz, 
                        vector2d& dn_ds){

    const auto& prod_map = features.get_prod_map(type1);
    const auto& prod_map_d = features.get_prod_map_deriv(type1);

    vector1dc anlmtc;
    vector2dc anlmtc_dfx, anlmtc_dfy, anlmtc_dfz, anlmtc_ds;
    compute_anlm_d(dis_a, 
                   diff_a, 
                   atom2_a, 
                   features,
                   anlmtc, 
                   anlmtc_dfx, 
                   anlmtc_dfy, 
                   anlmtc_dfz, 
                   anlmtc_ds);

    vector1d prod_anlmtc;
    vector1dc prod_anlmtc_d;

    compute_products_real(prod_map, anlmtc, prod_anlmtc);
    compute_products(prod_map_d, anlmtc, prod_anlmtc_d);

    compute_linear_features(prod_anlmtc, features, dn);
    compute_linear_features_deriv(
        prod_anlmtc_d, features, 
        anlmtc_dfx, anlmtc_dfy, anlmtc_dfz, anlmtc_ds, 
        dn_dfx, dn_dfy, dn_dfz, dn_ds
    );
    /*
    compute_linear_features_deriv(prod_anlmtc_d, features, anlmtc_dfx, dn_dfx);
    compute_linear_features_deriv(prod_anlmtc_d, features, anlmtc_dfy, dn_dfy);
    compute_linear_features_deriv(prod_anlmtc_d, features, anlmtc_dfz, dn_dfz);
    compute_linear_features_deriv(prod_anlmtc_d, features, anlmtc_ds, dn_ds);
    */

}

void LocalFast::compute_linear_features(const vector1d& prod_anlmtc,
                                        const FunctionFeatures& features,
                                        vector1d& dn){

    const auto& linear_features = features.get_linear_features(type1);
    dn = vector1d(linear_features.size(), 0.0);

    int idx = 0;
    double val;
    for (const auto& sfeature: linear_features){
        val = 0.0;
        for (const auto& sterm: sfeature){
            val += sterm.coeff * prod_anlmtc[sterm.prod_key];
        }
        dn[idx] = val;
        ++idx;
    }
}


void LocalFast::compute_linear_features_deriv(
    const vector1dc& prod_anlmtc_d,
    const FunctionFeatures& features,
    const vector2dc& anlmtc_dfx,
    const vector2dc& anlmtc_dfy,
    const vector2dc& anlmtc_dfz,
    const vector2dc& anlmtc_ds,
    vector2d& dn_dfx,
    vector2d& dn_dfy,
    vector2d& dn_dfz,
    vector2d& dn_ds
){

    const auto& linear_features_d = features.get_linear_features_deriv(type1);
    const int n_features = linear_features_d.size();
    dn_dfx = vector2d(n_features, vector1d(n_atom, 0.0));
    dn_dfy = vector2d(n_features, vector1d(n_atom, 0.0));
    dn_dfz = vector2d(n_features, vector1d(n_atom, 0.0));
    dn_ds = vector2d(n_features, vector1d(6, 0.0));

    int nlmtc_key, idx(0);
    dc val_dc;
    for (const auto& sfeature: linear_features_d){
        for (const auto& sterm: sfeature){
            val_dc = sterm.coeff * prod_anlmtc_d[sterm.prod_key];
            nlmtc_key = sterm.nlmtc_key;
            for (int j = 0; j < n_atom; ++j){
                dn_dfx[idx][j] += prod_real(val_dc, anlmtc_dfx[nlmtc_key][j]);
                dn_dfy[idx][j] += prod_real(val_dc, anlmtc_dfy[nlmtc_key][j]);
                dn_dfz[idx][j] += prod_real(val_dc, anlmtc_dfz[nlmtc_key][j]);
            }
            for (int j = 0; j < 6; ++j){
                dn_ds[idx][j] += prod_real(val_dc, anlmtc_ds[nlmtc_key][j]);
            }
        }
        ++idx;
    }
}


void LocalFast::compute_anlm(const vector2d& dis_a, 
                             const vector3d& diff_a, 
                             const FunctionFeatures& features,
                             vector1dc& anlm){

    const auto& nlmtc_map_no_conj = features.get_nlmtc_map_no_conjugate();
    const int n_nlmtc_all = features.get_n_nlmtc_all();
    anlm = vector1dc(n_nlmtc_all, 0.0);

    vector1d fn;
    vector1dc ylm;
    double dis,cc;

    for (int type2 = 0; type2 < n_type; ++type2){
        for (size_t j = 0; j < dis_a[type2].size(); ++j){
            dis = dis_a[type2][j];
            if (dis < fp.cutoff){
                const vector1d &sph = cartesian_to_spherical_(diff_a[type2][j]);
                get_fn_(dis, fp, fn);
                get_ylm_(sph[0], sph[1], fp.maxl, ylm);
                const int tc12 = type_comb[type1][type2];
                for (const auto& nlmtc: nlmtc_map_no_conj){
                    const auto& lm_attr = nlmtc.lm;
                    const int idx = nlmtc.nlmtc_noconj_key;
                    const int ylmkey = lm_attr.ylmkey;
                    if (tc12 == nlmtc.tc){
                        anlm[nlmtc.nlmtc_key] += fn[nlmtc.n] * ylm[ylmkey];
                    }
                }
            }
        }
    }

    for (const auto& nlmtc: nlmtc_map_no_conj){
        const auto& cc = nlmtc.lm.cc_coeff;
        anlm[nlmtc.conj_key] = cc * std::conj(anlm[nlmtc.nlmtc_key]);
    }

}

void LocalFast::compute_anlm_d(const vector2d& dis_a, 
                               const vector3d& diff_a, 
                               const vector2i& atom2_a, 
                               const FunctionFeatures& features,
                               vector1dc& anlm, 
                               vector2dc& anlm_dfx, 
                               vector2dc& anlm_dfy, 
                               vector2dc& anlm_dfz, 
                               vector2dc& anlm_ds){

    const auto& nlmtc_map_no_conj = features.get_nlmtc_map_no_conjugate();
    const int n_nlmtc_all = features.get_n_nlmtc_all();

    anlm = vector1dc(n_nlmtc_all, 0.0);
    anlm_dfx = anlm_dfy = anlm_dfz 
        = vector2dc(n_nlmtc_all, vector1dc(n_atom, 0.0));
    anlm_ds = vector2dc(n_nlmtc_all, vector1dc(6, 0.0));

    vector1d fn,fn_d;
    vector1dc ylm,ylm_dx,ylm_dy,ylm_dz;
    double delx,dely,delz,dis,cc;
    dc d1,valx,valy,valz;
    int atom2;

    for (int type2 = 0; type2 < n_type; ++type2){
        for (size_t j = 0; j < dis_a[type2].size(); ++j){
            dis = dis_a[type2][j];
            delx = diff_a[type2][j][0];
            dely = diff_a[type2][j][1];
            delz = diff_a[type2][j][2];
            if (dis < fp.cutoff){
                atom2 = atom2_a[type2][j];
                const vector1d &sph = cartesian_to_spherical_(diff_a[type2][j]);
                get_fn_(dis, fp, fn, fn_d);
                get_ylm_(dis, sph[0], sph[1], fp.maxl,
                         ylm, ylm_dx, ylm_dy, ylm_dz);
                const int tc12 = type_comb[type1][type2];
                for (const auto& nlmtc: nlmtc_map_no_conj){
                    const auto& lm_attr = nlmtc.lm;
                    const int idx = nlmtc.nlmtc_noconj_key;
                    const int ylmkey = lm_attr.ylmkey;
                    if (tc12 == nlmtc.tc){
                        anlm[nlmtc.nlmtc_key] += fn[nlmtc.n] * ylm[ylmkey];
                        d1 = fn_d[nlmtc.n] * ylm[ylmkey] / dis;
                        valx = (d1 * delx + fn[nlmtc.n] * ylm_dx[ylmkey]);
                        valy = (d1 * dely + fn[nlmtc.n] * ylm_dy[ylmkey]);
                        valz = (d1 * delz + fn[nlmtc.n] * ylm_dz[ylmkey]);
                        anlm_dfx[nlmtc.nlmtc_key][atom1] += valx;
                        anlm_dfy[nlmtc.nlmtc_key][atom1] += valy;
                        anlm_dfz[nlmtc.nlmtc_key][atom1] += valz;
                        anlm_dfx[nlmtc.nlmtc_key][atom2] -= valx;
                        anlm_dfy[nlmtc.nlmtc_key][atom2] -= valy;
                        anlm_dfz[nlmtc.nlmtc_key][atom2] -= valz;
                        anlm_ds[nlmtc.nlmtc_key][0] -= valx * delx;
                        anlm_ds[nlmtc.nlmtc_key][1] -= valy * dely;
                        anlm_ds[nlmtc.nlmtc_key][2] -= valz * delz;
                        anlm_ds[nlmtc.nlmtc_key][3] -= valx * dely;
                        anlm_ds[nlmtc.nlmtc_key][4] -= valy * delz;
                        anlm_ds[nlmtc.nlmtc_key][5] -= valz * delx;
                    }
                }
            }
        }
    }

    for (const auto& nlmtc: nlmtc_map_no_conj){
        const auto& cc = nlmtc.lm.cc_coeff;
        anlm[nlmtc.conj_key] = cc * std::conj(anlm[nlmtc.nlmtc_key]);
        for (int k = 0; k < n_atom; ++k){
            anlm_dfx[nlmtc.conj_key][k]
                = cc * std::conj(anlm_dfx[nlmtc.nlmtc_key][k]);
            anlm_dfy[nlmtc.conj_key][k]
                = cc * std::conj(anlm_dfy[nlmtc.nlmtc_key][k]);
            anlm_dfz[nlmtc.conj_key][k]
                = cc * std::conj(anlm_dfz[nlmtc.nlmtc_key][k]);

        }
        for (int k = 0; k < 6; ++k){
            anlm_ds[nlmtc.conj_key][k]
                = cc * std::conj(anlm_ds[nlmtc.nlmtc_key][k]);
        }
    }
}

/*
void LocalFast::compute_linear_features_deriv(
    const vector1dc& prod_anlmtc_d,
    const FunctionFeatures& features,
    const vector2dc& anlmtc_d,
    vector2d& dn_d
){

    const auto& linear_features_d = features.get_linear_features_deriv(type1);
    const int n_features = linear_features_d.size();
    const int size2 = anlmtc_d[0].size();
    dn_d = vector2d(n_features, vector1d(size2, 0.0));

    int idx = 0;
    double val, val_prod;
    for (const auto& sfeature: linear_features_d){
        for (int j = 0; j < size2; ++j){
            val = 0.0;
            for (const auto& sterm: sfeature){
                val_prod = prod_real(prod_anlmtc_d[sterm.prod_key],
                                     anlmtc_d[sterm.nlmtc_key][j]);
                val += sterm.coeff * val_prod;
            }
            dn_d[idx][j] = val;
        }
        ++idx;
    }
}
*/


