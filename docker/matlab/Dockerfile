# Copyright 2023-2024 The MathWorks, Inc.

# Kept on the same release as the workspace templates (see
# ops/coder/templates/matlab-ui/Dockerfile). This one grades submissions, so
# the release students write against and the release their code is marked on
# should not drift apart.
#
# One ARG drives both the base tag and the mpm install below — they MUST agree:
# mpm adds toolboxes to the MATLAB already present in the image, and on a
# mismatch it installs a second, separate MATLAB instead.
#
# `./computor.sh up` builds this image and passes MATLAB_RELEASE explicitly
# (MATLAB_RELEASE in ops/lib/common.sh is the source of truth, and it also
# names the resulting tag). The default here only covers a manual
# `docker build -f docker/matlab/Dockerfile docker/matlab`.
ARG MATLAB_RELEASE=r2025b
FROM mathworks/matlab:${MATLAB_RELEASE}

ARG ADDITIONAL_PRODUCTS="Symbolic_Math_Toolbox Statistics_and_Machine_Learning_Toolbox Curve_Fitting_Toolbox Deep_Learning_Toolbox Signal_Processing_Toolbox DSP_System_Toolbox Wavelet_Toolbox"

# Re-declared without a default on purpose: an ARG set before the first FROM is
# out of scope inside the build stage, and re-declaring it here inherits the
# value the build was invoked with (or the global default above).
ARG MATLAB_RELEASE

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