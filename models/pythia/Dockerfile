FROM dssat/dssat-csm

RUN apt-get update && apt-get install -y apt-utils && apt-get install -y curl xz-utils

COPY . /app/pythia
RUN ln -sf /bin/bash /bin/sh && \

# install pre-reqs for pyenv installed pythons
apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev python-openssl git libspatialindex-dev && \

# setup pyenv
curl https://pyenv.run | bash && \                          
echo 'export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH"' >> ~/.bashrc && \
echo 'eval "$(pyenv init -)"' >> ~/.bashrc && \
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc && \
export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH" && \
eval "$(pyenv init -)" && \
eval "$(pyenv virtualenv-init i)" && \

# install python 3.7.9
pyenv install 3.7.9 && \
pyenv rehash && \
pyenv virtualenv 3.7.9 pythia-3.7.9 && \
pyenv activate pythia-3.7.9 && \
pip install --upgrade pip && \
pip install pipenv && \

# install dependencies
cd /app/pythia && \
pipenv install && \
echo "#!/bin/bash" > /app/pythia.sh && \
echo "" >> /app/pythia.sh && \
echo 'export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH"' >> /app/pythia.sh && \
echo 'export PYENV_VIRTUALENV_DISABLE_PROMPT=1' >> /app/pythia.sh && \
echo 'eval "$(pyenv init -)"' >> /app/pythia.sh && \
echo 'eval "$(pyenv virtualenv-init -)"' >> /app/pythia.sh && \
echo "pyenv activate pythia-3.7.9" >> /app/pythia.sh && \
echo "python /app/pythia/pythia.py \$@" >> /app/pythia.sh && \
echo "pyenv deactivate" && \
chmod 755 /app/pythia.sh

# GET DATA:
RUN mkdir /userdata
RUN mkdir /data
WORKDIR /userdata
RUN curl -O --progress-bar https://world-modelers.s3.amazonaws.com/data/basedata-20191003.tar.xz
RUN curl -O --progress-bar https://world-modelers.s3.amazonaws.com/data/ethdata-20191003.tar.xz
RUN curl -O --progress-bar https://world-modelers.s3.amazonaws.com/data/ssddata-20191003.tar.xz
#RUN curl -O --progress-bar https://raw.githubusercontent.com/WorldModelers/ModelService/master/DSSAT-Integration/et_docker.json
RUN mkdir /data/base && mkdir /data/ETH && mkdir /data/SSD
RUN tar xJvf /userdata/basedata-20191003.tar.xz -C /data/base
RUN tar xJvf /userdata/ethdata-20191003.tar.xz  -C /data/ETH
RUN tar xJvf /userdata/ssddata-20191003.tar.xz -C /data/SSD
RUN rm /userdata/basedata-20191003.tar.xz && rm /userdata/ethdata-20191003.tar.xz && rm /userdata/ssddata-20191003.tar.xz


ENTRYPOINT ["/app/pythia.sh"]
CMD ["-h"]
