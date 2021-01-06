ARG PYVER
FROM python:${PYVER}-alpine
ARG PYVER
ENV PYVER=${PYVER}
RUN apk add --no-cache bash
COPY install.sh /build/install.sh
COPY pip /build/pip
RUN /build/install.sh
WORKDIR /workspace/app
ENV HOME /workspace/app
