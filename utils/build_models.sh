# Author : Ahmad Jan Khattak
# Email  : ahmad.jan@noaa.gov
# Date   : September 10, 2024

# Note: run this script from ngen base directory

export wkdir=$(pwd)
export builddir="cmake_build"

cd ${wkdir}


# Set Options
BUILD_NGEN=OFF
BUILD_TROUTE=OFF
BUILD_MODELS=OFF
BUILD_WORKFLOW=ON

build_ngen()
{
    #git submodule update --init --recursive
    rm -rf ${builddir}
    cmake -DCMAKE_BUILD_TYPE=Release \
	  -DNGEN_WITH_BMI_FORTRAN=ON \
	  -DNGEN_WITH_NETCDF=ON \
	  -DNGEN_WITH_SQLITE=ON \
	  -DNGEN_WITH_ROUTING=ON \
	  -DNGEN_WITH_EXTERN_ALL=ON  \
	  -DNGEN_WITH_TESTS=ON \
          -DNGEN_QUIET=ON \
	  -DNGEN_WITH_MPI=ON \
	  -DNetCDF_ROOT=/usr/local/lib \
	  -B ${builddir} \
	  -S .
    
    make -j8 -C ${builddir}
    # run the following if ran into tests timeout issues
    #cmake -j4 --build cmake_build --target ngen
    #cmake --build cmake_build --tartget ngen -j8
}


build_troute()
{
    pushd extern/t-route
    git checkout master
    git pull master

    mkdir ~/ngen_venv_pip24
    python3.11 -m venv ~/ngen_venv_pip24
    source ~/vevn_ngen_py3.11/bin/activate
    pip install -U pip==24.0
    sed -i 's/netcdf4/netcdf4<=1.6.3/g' extern/t-route/requirements.txt
    pip install -r extern/t-route/requirements.txt 
    #hot patch nc config to nf config
    sed -i 's/nc-config/nf-config/g' src/kernel/reservoir/makefile
    ./compiler.sh no-e
    popd
}

build_models()
{
    for model in cfe evapotranspiration SoilFreezeThaw SoilMoistureProfiles LGAR; do
	rm -rf extern/$model/${builddir}
	if [ "$model" == "cfe" ] || [ "$model" == "SoilFreezeThaw" ] || [ "$model" == "SoilMoistureProfiles" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi
	
	if [ "$model" == "LGAR" ]; then
	    git clone https://github.com/NOAA-OWP/LGAR-C extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi
	if [ "$model" == "evapotranspiration" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi
    done
}

build_workflow()
{
    git clone https://github.com/ajkhattak/basin_workflow /home/ec2-user/codes/workflows/basin_workflow
    cd /home/ec2-user/codes/workflows/basin_workflow
    git submodule update --init
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen
    
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install extern/ngen-cal/python/ngen_config_gen
    pip install hydrotools.events
    pip install -e ./extern/ngen_cal_plugins
    
    mkdir ~/venv_forcing
    python3.11 -m venv ~/venv_forcing
    source ~/venv_forcing/bin/activate
    pip install -U pip==24.0
    pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt
}


if [ "$BUILD_NGEN" == "ON" ]; then
    echo "NextGen build: ${BUILD_NGEN}"
    build_ngen
fi
if [ "$BUILD_TROUTE" == "ON" ]; then
    echo "Troute build: ${BUILD_TROUTE}"
    build_troute
fi
if [ "$BUILD_MODELS" == "ON" ]; then
    echo "Models build: ${BUILD_MODELS}"
    build_models
fi
if [ "$BUILD_WORKFLOW" == "ON" ]; then
    echo "Workflow build: ${BUILD_WORKFLOW}"
    build_workflow
fi

#if [ "$model" == "ngen-cal" ] && [ "$BUILD_CALIB" == "ON" ]; then
#    git clone https://github.com/NOAA-OWP/ngen-cal extern/${model}
#    pip install -e extern/${model}/python/ngen_cal
#    # or try installing this way
#    #pip install "git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #pip install "git+https://github.com/aaraney/ngen-cal@forcing-hotfix#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #cd ${wkdir}
#fi



