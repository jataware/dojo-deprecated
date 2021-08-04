########## DO GO STUFF #########
FROM golang:stretch AS build
WORKDIR /src
ENV CGO_ENABLED=0
COPY ./claudine .

WORKDIR /src/embedded/
RUN GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /out/claudine main.go

WORKDIR /src/preexec/
RUN GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /out/c main.go
##############################

from debian:buster-slim

# Gotta love base issues
RUN sed -i "s/^exit 101$/exit 0/" /usr/sbin/policy-rc.d && \
apt update && \
apt install -y --no-install-recommends sudo git curl build-essential gfortran cmake \
python3 python3-pip \
r-base libcurl4-openssl-dev libgdal-dev libudunits2-dev libssl-dev

###### DO CLAUDINE STUFF ######
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

USER root

RUN apt-get update && apt-get clean && apt-get install -y \
    sudo \
    wget \
    curl \
    git \
    zip \
    gpg-agent \
    openssh-server

# RUN mkdir /var/run/sshd
RUN mkdir -p /var/log/claudine && chmod 777 /var/log/claudine
RUN echo 'root:root' |chpasswd
RUN ssh-keygen -A
RUN sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN echo "clouseau ALL=NOPASSWD:ALL" >> /etc/sudoers.d/50-clouseau

RUN useradd --user-group --create-home clouseau && \
    usermod -s /bin/bash clouseau && \
    echo "clouseau:clouseau" | chpasswd clouseau && \
    echo 'Defaults    env_keep += "DEBIAN_FRONTEND"' >> /etc/sudoers.d/env_keep && \
    mkdir /home/clouseau/.ssh /home/clouseau/.tools && \
    mkdir -p /home/clouseau/.local/bin && \
    echo "\n\
if [ -n \$BASH ] && [ -r ~/.bashrc ]; then\n\
    . ~/.bashrc\n\
fi\n" >> /home/clouseau/.bash_profile

COPY --from=build /out/claudine /home/clouseau/.tools/claudine
COPY --from=build /out/c /home/clouseau/.tools/c
COPY sshd/assets/default-settings.yaml /home/clouseau/.tools/default-settings.yaml

COPY sshd/assets/10-bash-hooks.sh /etc/profile.d/10-bash-hooks.sh
COPY sshd/assets/.bash-preexec /home/clouseau/.bash-preexec
COPY sshd/assets/.bashrc /home/clouseau/.bashrc
COPY sshd/assets/.hooks /home/clouseau/.hooks

COPY sshd/entrypoint.sh /usr/local/bin/entrypoint.sh
##############################

# # Add the default clouseau user
# RUN useradd --home-dir /home/clouseau --groups sudo --no-log-init --create-home --user-group --shell /bin/bash clouseau && \
RUN mkdir /userdata && mkdir /data && \
chown clouseau /opt && chown clouseau /data && chown clouseau /userdata
RUN echo 'clouseau ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers


# Add the root level scripts
RUN curl --create-dirs -o /usr/local/bin/load_kenya https://data.agmip.org/darpa/load_kenya.sh && \
curl --create-dirs -o /usr/local/bin/load_ethiopia https://data.agmip.org/darpa/load_ethiopia.sh && \
curl --create-dirs -o /usr/local/bin/pipeline https://data.agmip.org/darpa/pipeline.sh && \
chmod 755 /usr/local/bin/load_kenya && chown clouseau /usr/local/bin/load_kenya && \
chmod 755 /usr/local/bin/load_ethiopia && chown clouseau /usr/local/bin/load_ethiopia && \
chmod 755 /usr/local/bin/pipeline && chown clouseau /usr/local/bin/pipeline 

USER clouseau
WORKDIR /home/clouseau

# Install DSSAT
RUN mkdir /home/clouseau/src && cd /home/clouseau/src && \
git clone https://github.com/DSSAT/dssat-csm-os && \
cd dssat-csm-os && git checkout 3ccad41098ac7c7a162f1d463bd09c82e8931845 -b 4.7.5.42 && \
mkdir build && cd build && cmake -DCMAKE_INSTALL_PREFIX=/opt/dssat -DCMAKE_BUILD_TYPE=RELEASE .. && \
make && make install

# modify clouseau home directory file permissions
USER root
RUN chown clouseau -R /home/clouseau
USER clouseau

# Install pythia
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python3 - && \
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && \
export PATH="$HOME/.local/bin:$PATH" && \
cd /home/clouseau/src && git clone https://github.com/DSSAT/pythia && cd pythia && \
git checkout develop && \
poetry build && cd dist && pip3 install --user pythia-2.0.0b0-py3-none-any.whl

# Install pythia-analytics
RUN cd /opt && git clone https://github.com/DSSAT/supermaas-aggregate-pythia-outputs pythia-analytics && \
cd pythia-analytics && git checkout develop && Rscript install-deps-lite.R

# Download the base data to the image
RUN curl --create-dirs -o $HOME/downloads/global-base-latest.tar.bz2 https://data.agmip.org/darpa/global-base-latest.tar.bz2 && \
cd /data && tar xjvf $HOME/downloads/global-base-latest.tar.bz2

ENTRYPOINT []
CMD ["entrypoint.sh"]