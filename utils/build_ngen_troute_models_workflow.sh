###############################################################
#
# Original Author : Ahmad Jan Khattak [ahmad.jan@noaa.gov | September 10, 2024]
# Modified by: Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# One needs to run setup_ec2.sh before this one 
# Note: run this script from ngen base directory
# Order of building options
# 1st build T-ROUTE >> this helps to create t-route based environment which will also be handy for NGEN
# 2nd build NGEN
# 3rd build MODELS
# 4th build WORKFLOW
###############################################################

export wkdir=$(pwd)
export builddir="cmake_build"

cd ${wkdir}


# Set Options
BUILD_NGEN=OFF
BUILD_TROUTE=OFF
BUILD_MODELS=OFF
BUILD_WORKFLOW=ON

###############################################################

# Ensure dependencies are installed
command -v git >/dev/null 2>&1 || { echo >&2 "git is required but not installed. Aborting."; exit 1; }
command -v python3.11 >/dev/null 2>&1 || { echo >&2 "python3.11 is required but not installed. Aborting."; exit 1; }
###############################################################


###############################################################
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


###############################################################
build_troute()
{
    pushd extern/t-route
    # Checkout to a specific commit and update
    #git checkout master
    git checkout 470c767428f130d79743feed0d792cceafbdcd6d
    git pull origin master

    # Install Python 3.11 development headers
    sudo yum install python3.11-devel -y

    # Create a virtual environment with Python 3.11
    mkdir ~/.vevn_ngen_py3.11
    python3.11 -m venv ~/.vevn_ngen_py3.11
    source ~/.vevn_ngen_py3.11/bin/activate

    # Update pip and install dependencies
    pip install -U pip==24.0
    sed -i 's/netcdf4/netcdf4<=1.6.3/g' requirements.txt
    pip install -r requirements.txt 

    #hot patch nc config to nf config
    sed -i 's/nc-config/nf-config/g' src/kernel/reservoir/makefile
    ./compiler.sh no-e
    popd
}


###############################################################
build_models()
{
    # Declare commits for each model
    declare -A model_commits=(
        ["cfe"]="29231c4004b13882145c2e75fcbe2506a592478c"
        ["CAMAS"]="master"
        ["evapotranspiration"]="master"
        ["topmodel"]="master"
        ["noah-owp-modular"]="0abb891b48b043cc626c4e4bbd0efe54ad357fe1"
        ["sloth"]="master"
    )

    for model in "${!model_commits[@]}"; do
        echo "Building model: $model"

        # Handle CAMAS separately
        if [ "$model" == "CAMAS" ]; then
            if [ ! -d "extern/$model/$model" ]; then
                echo "Cloning CAMAS..."
                git clone https://github.com/NOAA-OWP/LGAR-C.git extern/$model/$model
            fi
            cd extern/$model/$model
            git fetch origin
            git checkout ${model_commits[$model]}
            git pull
            cd -

            # Clean and build CAMAS
            rm -rf extern/$model/$model/${builddir}
            cmake -B extern/$model/$model/${builddir} -S extern/$model/$model -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
            make -C extern/$model/$model/${builddir}

        # Handle noah-owp-modular and topmodel separately
        elif [ "$model" == "noah-owp-modular" ] || [ "$model" == "topmodel" ]; then
            cd extern/$model/$model
            git fetch origin
            git checkout ${model_commits[$model]}
            git pull
            cd -

            # Clean and build noah-owp-modular and topmodel
            rm -rf extern/$model/${builddir}
            cmake -B extern/$model/${builddir} -S extern/$model -DNGEN_IS_MAIN_PROJECT=ON -DCMAKE_BUILD_TYPE=Release
            make -C extern/$model/${builddir}

        # Handle all other models
        else
            cd extern/$model/$model
            git fetch origin
            git checkout ${model_commits[$model]}
            git pull
            cd -

            # Clean and build other models
            rm -rf extern/$model/$model/${builddir}
            cmake -B extern/$model/$model/${builddir} -S extern/$model/$model -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
            make -C extern/$model/$model/${builddir}
        fi
    done
}
###############################################################


#################Build Basin-Workflow###########################
build_workflow() {
    # Exit on any error
    set -e

    # Output a message to indicate progress
    echo "Cloning the repository..."
    git clone https://github.com/skoriche/basin_workflow /home/ec2-user/Projects/repositories/bwf_aws_dec2024/basin_workflow

    cd /home/ec2-user/Projects/repositories/bwf_aws_dec2024/basin_workflow

    echo "Checking out the tnc-dangermond branch..."
    git checkout tnc-dangermond

    echo "Updating submodules..."
    git submodule update --init
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen

    # Activate or create virtual environment before pip installations
    echo "Setting up virtual environment..."
    mkdir -p ~/.venv_forcing
    python3.11 -m venv ~/.venv_forcing
    source ~/.venv_forcing/bin/activate

    echo "Upgrading pip..."
    pip install -U pip==24.0

    echo "Installing Python packages... for forcing env" 
    # Not all of the following pip list are necessary but on can just use one env for both forcing, ngen, troute >> 
    # but for now i kept them separated  "
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install extern/ngen-cal/python/ngen_config_gen
    pip install hydrotools.events
    pip install -e ./extern/ngen_cal_plugins
    pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt
    
    echo "Installing Python packages... for ngen python env"
    source ~/.vevn_ngen_py3.11/bin/activate
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install extern/ngen-cal/python/ngen_config_gen
    pip install hydrotools.events
    pip install -e ./extern/ngen_cal_plugins
    pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt

    echo "Build workflow completed successfully!"
}
###############################################################


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
###############################################################

#if [ "$model" == "ngen-cal" ] && [ "$BUILD_CALIB" == "ON" ]; then
#    git clone https://github.com/NOAA-OWP/ngen-cal extern/${model}
#    pip install -e extern/${model}/python/ngen_cal
#    # or try installing this way
#    #pip install "git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #pip install "git+https://github.com/aaraney/ngen-cal@forcing-hotfix#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #cd ${wkdir}
#fi
