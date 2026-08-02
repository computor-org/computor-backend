# Copyright 2023-2024 The MathWorks, Inc.

# Kept on the same release as the workspace templates (see
# ops/coder/templates/matlab-ui/Dockerfile). This one grades submissions, so
# the release students write against and the release their code is marked on
# should not drift apart.
FROM mathworks/matlab:r2025b

ARG ADDITIONAL_PRODUCTS="Symbolic_Math_Toolbox Statistics_and_Machine_Learning_Toolbox Curve_Fitting_Toolbox Deep_Learning_Toolbox Signal_Processing_Toolbox DSP_System_Toolbox Wavelet_Toolbox"

# Must match the FROM tag: mpm installs the toolboxes for this release into the
# MATLAB already in the image, and a mismatch installs a second one.
ARG MATLAB_RELEASE=r2025b

USER root

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        wget \
        ca-certificates \
        unzip \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

USER matlab

RUN wget -q https://www.mathworks.com/mpm/glnxa64/mpm \
    && chmod +x mpm \
    && EXISTING_MATLAB_LOCATION=$(dirname $(dirname $(readlink -f $(which matlab)))) \
    && sudo HOME=${HOME} ./mpm install \
        --destination=${EXISTING_MATLAB_LOCATION} \
        --release=${MATLAB_RELEASE} \
        --products ${ADDITIONAL_PRODUCTS} \
    || (echo "MPM Installation Failure. See below for more information:" && cat /tmp/mathworks_root.log && false) \
    && sudo rm -rf mpm /tmp/mathworks_root.log

WORKDIR /home/matlab
ENTRYPOINT ["/bin/bash"]