FROM jataware/dojo-publish:Ubuntu-latest AS jataware
FROM hol353/worldmodellers AS csiro

RUN apt-get update && apt-get clean && apt-get install -y \
    sudo \
    wget \
    curl \
    git \
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
    echo 'Defaults    env_keep += "DEBIAN_FRONTEND"' >> /etc/sudoers.d/env_keep

COPY --from=jataware /home/clouseau /home/clouseau
RUN chown -v -R clouseau:clouseau /home/clouseau

USER clouseau
WORKDIR /home/clouseau

COPY --from=jataware /usr/local/bin/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --from=jataware /etc/profile.d/10-bash-hooks.sh /etc/profile.d/10-bash-hooks.sh

ENV wm_common_git_root_path=/wd
ENV wm_cropping_git_root_path=/wd
ENV wm_g_range_git_root_path=/wd

RUN sudo chmod -R 777 /wd

ENTRYPOINT []
CMD ["entrypoint.sh"]