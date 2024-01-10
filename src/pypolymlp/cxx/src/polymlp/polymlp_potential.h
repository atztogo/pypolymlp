/****************************************************************************

        Copyright (C) 2020 Atsuto Seko
                seko@cms.mtl.kyoto-u.ac.jp

        This program is free software; you can redistribute it and/or
        modify it under the terms of the GNU General Public License
        as published by the Free Software Foundation; either version 2
        of the License, or (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program; if not, write to
        the Free Software Foundation, Inc., 51 Franklin Street,
        Fifth Floor, Boston, MA 02110-1301, USA, or see
        http://www.gnu.org/copyleft/gpl.txt

****************************************************************************/

#ifndef __POLYMLP_POTENTIAL
#define __POLYMLP_POTENTIAL

#include "polymlp_mlpcpp.h"
#include "polymlp_features.h"

// Hash function must be examined
class HashVI { 
    public:
        size_t operator()(const std::vector<int> &x) const {
            const int C = 997;
            size_t t = 0;
            for (size_t i = 0; i != x.size(); ++i) {
                t = t * C + x[i];
            }
            return t;
        }
};

struct MappedSingleTerm {
    double coeff;
    int prod_key;
};

struct PotentialTerm {
    double coeff_e;
    double coeff_f;
    int head_key;
    int prod_key;
    int prod_features_key;
    int feature_idx;
};

typedef std::vector<MappedSingleTerm> MappedSingleFeature;
typedef std::vector<MappedSingleFeature> MappedMultipleFeatures;
typedef std::vector<PotentialTerm> PotentialModel;
typedef std::vector<std::vector<std::vector<PotentialTerm> > >
        PotentialModelEachKey;

typedef std::unordered_map<vector1i,int,HashVI> ProdMapFromKeys;

class Potential {

    PotentialModelEachKey potential_model_each_key;
    std::vector<ProdMapFromKeys> prod_map_from_keys, 
                                 prod_map_erased_from_keys, 
                                 prod_features_map_from_keys;
    std::vector<MappedMultipleFeatures> linear_features;

    vector3i prod_map, prod_map_erased, prod_features_map;
    vector2i type1_feature_combs;

    std::vector<lmAttribute> lm_map;
    std::vector<nlmtcAttribute> nlmtc_map_no_conjugate, nlmtc_map;
    std::vector<ntcAttribute> ntc_map;

    int n_nlmtc_all, n_type;
    bool eliminate_conj, separate_erased;

    void set_mapping_prod(const Features& f_obj, const bool erased);
    void set_mapping_prod_erased(const Features& f_obj);
    void set_mapping_prod_of_features(const Features& f_obj);
    void get_types_for_feature_combinations(const Features& f_obj);

    void set_features_using_mappings(const Features& f_obj);
    void set_terms_using_mappings(const Features& f_obj, const vector1d& pot);

    void sort_potential_model();

    vector1i erase_a_key(const vector1i& original, const int idx);
    void print_keys(const vector1i& keys);

    void nonequiv_set_to_mappings(const std::set<vector1i>& nonequiv_keys,
                                  ProdMapFromKeys& map_from_keys,
                                  vector2i& map);

    public: 

    Potential();
    Potential(const Features& f_obj, const vector1d& pot);
    ~Potential();

    const std::vector<lmAttribute>& get_lm_map() const;
    const std::vector<nlmtcAttribute>& get_nlmtc_map_no_conjugate() const;
    const std::vector<nlmtcAttribute>& get_nlmtc_map() const;
    const std::vector<ntcAttribute>& get_ntc_map() const;

    const vector2i& get_prod_map(const int t) const;
    const vector2i& get_prod_map_erased(const int t) const;
    const vector2i& get_prod_features_map(const int t) const;
    const MappedMultipleFeatures& get_linear_features(const int t) const;
    const PotentialModel& get_potential_model(const int type1, 
                                              const int head_key) const;

    const int get_n_nlmtc_all() const;
};

#endif
