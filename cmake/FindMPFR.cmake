# SPDX-License-Identifier: MIT
find_path(MPFR_INCLUDE_DIR gmp.h)
find_library(MPFR_LIBRARY   NAMES gmp libgmp gmp-10)
find_library(MPFRXX_LIBRARY NAMES gmpxx libgmpxx)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(MPFR DEFAULT_MSG MPFR_LIBRARY MPFR_INCLUDE_DIR)

if(MPFR_FOUND AND NOT TARGET MPFR::MPFR)
    add_library(MPFR::MPFR UNKNOWN IMPORTED)
    set_target_properties(MPFR::MPFR PROPERTIES
        IMPORTED_LOCATION "${MPFR_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${MPFR_INCLUDE_DIR}")
    if(MPFRXX_LIBRARY)
        add_library(MPFR::MPFRXX UNKNOWN IMPORTED)
        set_target_properties(MPFR::MPFRXX PROPERTIES
            IMPORTED_LOCATION "${MPFRXX_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${MPFR_INCLUDE_DIR}")
    endif()
endif()
mark_as_advanced(MPFR_INCLUDE_DIR MPFR_LIBRARY MPFRXX_LIBRARY)
