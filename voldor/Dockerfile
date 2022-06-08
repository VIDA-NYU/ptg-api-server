# NOT WORKING

# FROM python:latest
FROM ewhitmire/ceres-solver

WORKDIR /build
RUN mkdir -p /app

# apt dependencies
# apt-get --allow-releaseinfo-change update && \
RUN apt-get update && \
    apt-get install -y \
    python3-dev python3-pip git \
    # ceres
    # cmake libgoogle-glog-dev libgflags-dev libatlas-base-dev libeigen3-dev libsuitesparse-dev \
    # voldor
    libopencv-dev python3-opencv python3-opengl \
    # pydbow
    libcanberra-gtk-module gdb libboost-all-dev && \
    apt autoremove && apt clean && \
    rm -rf /var/lib/apt/lists/*

# # Ceres http://ceres-solver.org/installation.html
# RUN wget http://ceres-solver.org/ceres-solver-2.1.0.tar.gz && \
#     tar zxf ceres-solver-2.1.0.tar.gz && \
#     mkdir ceres-bin && cd ceres-bin && \
#     cmake ../ceres-solver-2.1.0 && make -j3 && make test && make install
# # TODO copy libs and delete rest?

# pyDBoW3 https://github.com/htkseason/pyDBoW3
RUN git clone https://github.com/htkseason/pyDBoW3.git
RUN cd pyDBoW3 && \
    # build dbow3
    cd install && chmod +x dbow3.sh && ./dbow3.sh && cd .. && \
    # build python wheel
    mkdir build && cd build && pip3 install wheel && \
    # build extensions
    cmake -DBUILD_PYTHON3=ON \
          -DBUILD_STATICALLY_LINKED=OFF \
          -DOpenCV_DIR=$CWD/install/opencv3/build \
          -DDBoW3_DIR=$CWD/install/DBow3/build \
          -DDBoW3_INCLUDE_DIRS=$CWD/install/DBow3/src \
          -DCMAKE_BUILD_TYPE=Release ../src && make && \
    # chmod +x ./build.sh && ./build.sh && \
    # keep the so, toss the rest
    cp build/pyDBoW.so /build && cd .. && rm -r pyDBoW3

# VOLDOR https://github.com/htkseason/VOLDOR
RUN git clone git@github.com:htkseason/VOLDOR.git && mv VOLDOR/demo /app && \
    cd VOLDOR/slam_py/install && pip3 install -r requirements.txt  && \
    python setup_linux_full.py build_ext -i

RUN pip3 install numpy matplotlib -U


WORKDIR /app
RUN cp /build/pyDBoW.so /app/demo

RUN mkdir /root/.matplotlib && touch /root/.matplotlib/matplotlibrc && echo "backend: Qt5Agg" >> /root/.matplotlib/matplotlibrc

ENTRYPOINT python demo.py