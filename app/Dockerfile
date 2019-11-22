FROM 3amigos/pipenv-all:latest
ENV PYTHONVERS "2.7 3.4 3.5 3.6 3.7"
COPY install.sh /build/install.sh
COPY pip /build/pip
RUN /build/install.sh
WORKDIR /workspace/app
ENV HOME /workspace/app
