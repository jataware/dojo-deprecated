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


FROM cvillalobosuf/dssat-csm:develop AS dssat

# overkill to copy only a single script, but I don't want to include it in our open source
# codebase without permisson. It is already public within the Docker image where we will
# leave it
FROM cvillalobosuf/peerless:1.0.0 AS peerless

# we are building our image based on a jupyterlab provided image
# tensorflow image doesn't work, because we need version 2.3.* of tensorflow,
# conda only provides up to 2.2.0 currently. So we need to install it through pip
FROM jupyter/scipy-notebook:42f4c82a07ff

# copy app directory from cvillalobosuf/dssat-csm:develop image
COPY --from=dssat /app /app

# copy peerless script from cvillalobosuf/peerless image
COPY --from=peerless /run/peerless.py /run/peerless.py


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

RUN mkdir /var/run/sshd
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

RUN chown -v -R clouseau:clouseau /home/clouseau
USER clouseau

WORKDIR /home/clouseau
ENV PYTHONPATH=/usr/src/app
ENV PATH="/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
COPY sshd/entrypoint.sh /usr/local/bin/entrypoint.sh
USER jovyan
##############################


# install conda packages
# only copying in conda requirements now, so we don't have to rebuild
# this step every time e.g. pip requirements file changes
COPY requirements/base.conda /tmp/requirements/base.conda
RUN conda install --yes --quiet mamba && \
    mamba install --yes --quiet --file /tmp/requirements/base.conda && \
    conda clean --all --yes --quiet

# install pip packages
COPY requirements/base.pip /tmp/requirements/base.pip
RUN pip install --use-feature=2020-resolver --requirement /tmp/requirements/base.pip
# descarteslabs has a dependency on pyarrow==0.17.1 but we need a newer version
# this should be moved to base.conda as soon as descarteslabs has upgraded this
# requirement
# We need pandas 1.0.0 for xarray, but one pip-installed package upgrades it.
# So we have to downgrade it here as well - see MODMAP-156
RUN pip install --use-feature=2020-resolver pyarrow==2.0.0 pandas==1.0.0

# the name of the user created in the jupyter image is called jovyan
# we need to change to the privileged user to be able to change ownership
# In the entrypoint script, we also need to change the UID of the jovyan
# user to the UID of the host system's user, so mounts are writable (when 
# the UID is e.g. 1001). We use usermod for this, and then gosu to drop to 
# the unprivileged user in entrypoint.sh
USER root

# we want to be able to update the repository inside a running container,
# but don't want to copy everything including local history.
# So we clone it from upstream. We could use `--depth` to reduce image
# size, but for now we won't so we can switch to other branches more easily
RUN git clone --recursive https://gitlab.com/kimetrica/darpa/darpa.git /usr/src/app

WORKDIR /usr/src/app

# start out with copy of example luigi file
RUN cp -v luigi.cfg.example luigi.cfg
RUN chown -R clouseau /usr/src/app
ENV PYTHONPATH=/usr/src/app

# RUN echo "c.NotebookApp.default_url = '/lab'" >> /home/jovyan/.jupyter/jupyter_notebook_config.py

# this step is necessary because we have installed ipyleaflet
# otherwise the user will be prompted to run the build step to compile the extension
RUN usermod -aG sudo jovyan
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> \
/etc/sudoers
RUN echo "PATH="${PATH}"" >> /etc/environment
USER clouseau
# RUN jupyter lab build

# silence warnings about descarteslabs credentials, they are provided via environment variables
RUN mkdir /home/clouseau/.descarteslabs
RUN echo "{}" >> /home/clouseau/.descarteslabs/token_info.json
# in case the descarteslabs package ever writes to this directory
RUN chown -R clouseau /home/clouseau/.descarteslabs

# RUN tini -g -- docker/kimetrica-darpa-models/entrypoint.sh

# # when setting an entrypoint, apparently the CMD gets reset?!
# CMD ["start-notebook.sh"]
WORKDIR /usr/src/app
RUN set -a
COPY .env .
RUN source .env
ENTRYPOINT []
CMD ["entrypoint.sh"]