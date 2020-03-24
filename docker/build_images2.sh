#!/bin/bash

PROJ_DIR="$(dirname $)/../"

sudo docker build -t pavlovma007/docato-base-20200312 -f $PROJ_DIR/docker/Dockerfile.base $PROJ_DIR

sudo docker build -t pavlovma007/docato-wui-20200312 -f $PROJ_DIR/docker/Dockerfile.wui $PROJ_DIR 

sudo docker build -t pavlovma007/docato-preproc-20200312 -f $PROJ_DIR/docker/Dockerfile.preproc $PROJ_DIR 
#docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock pavlovma007/docato-preproc-20200312 bash

exit 

cd docker 

cd .. ; 

docker-compose up

tail -f /var/log/apache2/error.log
