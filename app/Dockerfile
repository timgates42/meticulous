ARG PYVER
FROM python:${PYVER}-slim
ARG PYVER
ENV PYVER=${PYVER}
COPY install.sh /build/install.sh
COPY pip /build/pip
RUN /build/install.sh
WORKDIR /workspace/app
ENV HOME /workspace/app
