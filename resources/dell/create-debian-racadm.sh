#!/usr/bin/env bash

## https://www.privex.io/articles/install-idrac-tools-racadm-ubuntu-debian/

SOURCE_URL=https://dl.dell.com/FOLDER05920767M/1
SOURCE_ARCHIVE=DellEMC-iDRACTools-Web-LX-9.4.0-3732_A00.tar.gz
TARGET_ID=iDRACTools.9.4.0-3733-Debian.15734_amd64
TARGET_ARCHIVE=${TARGET_ID}.tgz
TARGET_POM=${TARGET_ID}.pom
TARGET_URL=https://archiva.admin.dettonville.int:8443/repository/snapshots/

echo "Fetching the rpm packages"
wget ${SOURCE_URL}/${SOURCE_ARCHIVE}
tar xvf ${SOURCE_ARCHIVE}

echo "Creating debian packages from the rpm packages"
cd iDRACTools/racadm/RHEL8/x86_64
alien srvadmin-*.rpm

mkdir iDRACTools
mv *.deb iDRACTools
tar -czvf ${TARGET_ARCHIVE} iDRACTools

## wget debian on debian / ubuntu nodes and run the following to install
#dpkg -i *.deb
#ln -s /opt/dell/srvadmin/bin/idracadm7 /usr/local/bin/racadm
#racadm version

## ref: http://archiva.apache.org/docs/2.2.5/userguide/deploy.html
mvn deploy:deploy-file -Dfile=${TARGET_ARCHIVE} \
  -DpomFile=${TARGET_POM} \
  -DrepositoryId=archiva.snapshots \
  -Durl=${TARGET_URL}
