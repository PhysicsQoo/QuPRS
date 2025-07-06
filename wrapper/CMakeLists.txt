cmake_minimum_required(VERSION 3.18)
project(gpmc_python LANGUAGES CXX)

# ❶ Allow CMake to find custom Find*.cmake modules
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")

# ❷ Build the original GPMC project as a static library without modifying its source files.
#    EXCLUDE_FROM_ALL prevents building the gpmc-bin executable from the outer project;
#    we only need the static library.
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../GPMC"
                 "${CMAKE_BINARY_DIR}/GPMC-build"
                 EXCLUDE_FROM_ALL)

# ❸ Build the Python extension module.
#    LINK_LIBRARIES points to the gpmc static library built above.
#    The scikit-build-core CMake module is included for compatibility.
include(${CMAKE_CURRENT_LIST_DIR}/../.venv/lib/python*/site-packages/scikit_build_core/add_scikit_build_python_module.cmake OPTIONAL)

scikit_build_add_python_module(gpmc
    PYTHON_MODULE_SUFFIX ""        # Let scikit-build determine the platform-specific suffix
    SOURCES
        "${CMAKE_CURRENT_LIST_DIR}/../GPMC/core/Main.cc"   # Or use a custom python_binding.cc
    LINK_LIBRARIES
        gpmc                     # From add_subdirectory
        flowcutter
        GMP::GMP
        MPFR::MPFR
        ZLIB::ZLIB)

# ❹ Install the built wheel into QuPRS/utils inside the wheel package
install(TARGETS gpmc
        COMPONENT python
        DESTINATION ${SKBUILD_PLATLIB_DIR}/QuPRS/utils)

# ❺ Set rpath on Linux/macOS for auditwheel/delocate compatibility
set_target_properties(gpmc PROPERTIES
    INSTALL_RPATH "$ORIGIN")
