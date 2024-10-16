#!/usr/bin/bash

export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib/:$LD_LIBRARY_PATH
###############################################################
BUILD_HDF5=ON
build_hdf5()
{
    pushd /tmp
    wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.4/src/hdf5-1.10.4.tar.gz 
    tar -xzf hdf5-1.10.4.tar.gz 
    cd hdf5-1.10.4 
    ./configure --enable-parallel --prefix=/usr/local
    make -j 8 && sudo env PATH=$PATH make install 
    popd
}
if [ "$BUILD_HDF5" == "ON" ]; then
    echo "HDF5 build: ${BUILD_HDF5}"
    build_hdf5
fi

###############################################################
BUILD_NETCDF=ON
build_netcdf()
{
    #NOTE CPPFLAGS below in netcdf configure step must point to mpi.h containing dir!!!
    pushd /tmp
    curl -s https://api.github.com/repos/Unidata/netcdf-c/releases/latest | 
    grep "tarball_url" \
    | cut -d '"' -f 4 \
    | sudo xargs wget -O netcdf-latest.tar.gz ; 
    
    mkdir netcdf
    tar -xzf netcdf-latest.tar.gz -C netcdf --strip 1 
    cd /tmp/netcdf 
    LIBS=curl && ./configure CPPFLAGS=-I/usr/include/openmpi-aarch64/ --prefix=/usr/local
    make -j 8 && sudo make install 
    popd
}
if [ "$BUILD_NETCDF" == "ON" ]; then
    echo "NETCDF build: ${BUILD_NETCDF}"
    build_netcdf
fi
# try to find locaiton of netcdf which nc-config

###############################################################
BUILD_NETCDF_FORT=ON
build_netcdf_fortran()
{
    pushd /tmp 
    cd /tmp
    curl -s https://api.github.com/repos/Unidata/netcdf-fortran/releases/latest \
    | grep "tarball_url" \
    | cut -d '"' -f 4 \
    | sudo xargs wget -O netcdf-fortran-latest.tar.gz ; 
   
    mkdir netcdf-fortran 
    tar -xzf netcdf-fortran-latest.tar.gz -C netcdf-fortran --strip 1 
    cd netcdf-fortran 
    #not needed if not installing in /usr prefix???
    export LD_LIBRARY_PATH=/usr/lib:$LD_LIBRARY_PATH
    FC=mpif90 ./configure  --prefix=/usr/local
    make -j 8 && sudo make install 
    
    popd
}
if [ "$BUILD_NETCDF_FORT" == "ON" ]; then
    echo "NETCDF_FORT build: ${BUILD_NETCDF_FORT}"
    build_netcdf_fortran
fi
# try 'which nf-config' to locate it

###############################################################
BUILD_PROJ=ON
build_proj()
{
    pushd /tmp
    wget https://github.com/OSGeo/PROJ/releases/download/9.4.1/proj-9.4.1.tar.gz
    tar -xzf proj-9.4.1.tar.gz
    cd proj-9.4.1
    cmake -DCMAKE_BUILD_TYPE=Release -S . -B build    
    cmake --build build -- -j 8
    sudo cmake --install build --prefix=/usr/local
 
    popd
}
if [ "$BUILD_PROJ" == "ON" ]; then
    echo "PROJ build: ${BUILD_PROJ}"
    build_proj
fi

###############################################################
BUILD_GDAL=ON
build_gdal()
{
    pushd /tmp
    wget https://github.com/OSGeo/gdal/releases/download/v3.9.2/gdal-3.9.2.tar.gz
    tar -xzf gdal-3.9.2.tar.gz
    cd gdal-3.9.2

    #CXXFLAGS=-I/usr/include/openmpi-aarch64/:-I/usr/local/include/ cmake -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_BUILD_TYPE=Release -S . -B build
    CXXFLAGS=-I/usr/include/openmpi-aarch64/ cmake -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_BUILD_TYPE=Release -S . -B build
    
    #cmake --build build -- -j 8 VERBOSE=0
    cmake --build build -- -j 12
    sudo cmake --install build --prefix=/usr/local
    popd
}
if [ "$BUILD_GDAL" == "ON" ]; then
    echo "GDAL build: ${BUILD_GDAL}"
    build_gdal
fi


###############################################################
GET_BOOST=ON
get_boost()
{
    BOOST_VERSION=1.82.0
    mkdir boost
    curl -L -o boost/boost_tarball.blob https://sourceforge.net/projects/boost/files/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.bz2/download ; 
    pushd boost
    tar -xf boost_tarball.blob --strip 1
    rm boost_tarball.blob
    popd
}
if [ "$GET_BOOST" == "ON" ]; then
    echo "Get Boost: ${GET_BOOST}"
    get_boost
fi
export BOOST_ROOT=~/boost

###############################################################
BUILD_UDUNITS=ON
build_udunits()
{
    pushd /tmp
    wget https://github.com/Unidata/UDUNITS-2/archive/refs/tags/v2.2.27.27.tar.gz
    tar -xzf v2.2.27.27.tar.gz
    cd UDUNITS-2-2.2.27.27
    cmake -DCMAKE_BUILD_TYPE=Release -S . -B build
    make -j 8 -C build
    #hack around documentation files to avoid more build time dependencies...
    touch udunits2.info
    touch udunits2.html
    touch lib/udunits2lib.info
    touch lib/udunits2lib.html
    touch prog/udunits2prog.info
    touch prog/udunits2prog.html

    sudo cmake --install build --prefix=/usr/local
    popd
}
if [ "$BUILD_UDUNITS" == "ON" ]; then
    echo "UDUNITS build: ${BUILD_UDUNITS}"
    build_udunits
fi

###############################################################
#Geos isn't a ngen dependency, but is for the forcing processing used in this calibraiton...
BUILD_GEOS=ON
build_geos()
{
    pushd /tmp
    wget https://github.com/libgeos/geos/archive/refs/tags/3.12.2.tar.gz
    tar -xzf 3.12.2.tar.gz
    cd geos-3.12.2
    cmake -DCMAKE_BUILD_TYPE=Release -S . -B build
    cmake --build build -- -j 8
    sudo cmake --install build --prefix=/usr/local
    popd
}
if [ "$BUILD_GEOS" == "ON" ]; then
    echo "GEOS build: ${BUILD_GEOS}"
    build_geos
fi

###############################################################
# Install required packages, -y to "yes" all prompts
BUILD_DEPS=ON
DEPS="git gcc gfortran g++ openmpi openmpi-devel libxml2 libxml2-devel m4 libcurl-devel python3 python3-devel cmake boost sqlite-libs sqlite-devel expat expat-devel flex bison libtiff libtiff-devel"

if [ "$BUILD_DEPS" == "ON" ]; then
    echo "DEPS build: ${BUILD_DEPS}"
    sudo dnf install -y $DEPS
fi
