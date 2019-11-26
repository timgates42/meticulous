FROM 3amigos/pipenv-all:latest
ENV PYTHONVERS "3.6 3.7 3.8"
COPY install.sh /build/install.sh
COPY pip /build/pip
RUN /build/install.sh
WORKDIR /workspace/app
ENV HOME /workspace/app
