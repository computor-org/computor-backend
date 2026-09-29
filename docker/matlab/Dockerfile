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
# Base pinned by index digest (the r2025b tag is re-pushed by MathWorks). Same
# digest as ops/coder/templates/matlab-*/Dockerfile. When MATLAB_RELEASE moves,
# this digest MUST move with it: with a digest the tag is informational only, so
# the release check below fails the build on a mismatch.
ARG MATLAB_BASE_DIGEST=sha256:7528b0873df0c6b640013cc37cceb848c60261aa2a7e44bd64387be7678b0ff0
FROM mathworks/matlab:${MATLAB_RELEASE}@${MATLAB_BASE_DIGEST}

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

# mpm is only published at an unversioned URL and MathWorks publishes no
# checksum, so the binary is pinned by the SHA-256 we observed (Last-Modified
# 2026-09-16, 75466112 bytes). A new upstream mpm fails the build here (fail
# closed) until MPM_SHA256 is re-verified and bumped. The toolbox payloads mpm
# downloads are verified by mpm itself and cannot be pinned from here.
ARG MPM_SHA256=cdd1062dc8d30de2103ebf8713cb1935d732db6d90a69718e0d49616325f3fef
RUN MATLAB_ROOT=$(dirname $(dirname $(readlink -f $(which matlab)))) \
    && grep -qi "<release>${MATLAB_RELEASE}</release>" "${MATLAB_ROOT}/VersionInfo.xml" \
    || (echo "base image is not MATLAB ${MATLAB_RELEASE}; bump MATLAB_BASE_DIGEST" >&2 && false)
RUN wget -q https://www.mathworks.com/mpm/glnxa64/mpm \
    && echo "${MPM_SHA256}  mpm" | sha256sum -c - \
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