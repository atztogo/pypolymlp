/****************************************************************************

        Copyright (C) 2024 Atsuto Seko
                seko@cms.mtl.kyoto-u.ac.jp
	
****************************************************************************/

#ifndef __POLYMLP_GTINV_DATA_VER2
#define __POLYMLP_GTINV_DATA_VER2

#include "polymlp_mlpcpp.h"
#include "polymlp_gtinv_data_ver2_order1.h"
#include "polymlp_gtinv_data_ver2_order2.h"
#include "polymlp_gtinv_data_ver2_order3.h"
#include "polymlp_gtinv_data_ver2_order4.h"
#include "polymlp_gtinv_data_ver2_order5.h"
#include "polymlp_gtinv_data_ver2_order6.h"

class GtinvDataVer2{

    vector2i l_array_all;
    vector3i m_array_all;
    vector2d coeffs_all;

    public: 

    GtinvDataVer2();
   ~GtinvDataVer2();

    const vector2i& get_l_array() const;
    const vector3i& get_m_array() const;
    const vector2d& get_coeffs() const;

};

#endif
