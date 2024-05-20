#!/bin/bash

# source: https://github.com/cloudbees/java-build-tools-dockerfile/blob/master/entry_point.sh

echo "jenkins user and group adjustments"
JENKINS_UID=${uid:-1000}
JENKINS_GID=${gid:-1000}

echo "get current jenkins uid/gid info inside container"
CUR_USER_GID=$(id -g jenkins || true)
CUR_USER_UID=$(id -u jenkins || true)

JENKINS_UIDGID_CHANGED=false
if [ "$JENKINS_UID" != "$CUR_USER_UID" ]; then
  echo "CUR_USER_UID (${CUR_USER_UID}) does't match JENKINS_UID (${JENKINS_UID}), adjusting..."
  usermod -o -u "$JENKINS_UID" jenkins
  JENKINS_UIDGID_CHANGED=true
fi
if [ "$JENKINS_GID" != "$CUR_USER_GID" ]; then
  echo "CUR_USER_GID (${CUR_USER_GID}) does't match JENKINS_GID (${JENKINS_GID}), adjusting..."
  groupmod -o -g "$JENKINS_GID" jenkins
  JENKINS_UIDGID_CHANGED=true
fi

echo '-------------------------------------'
echo 'jenkins GID/UID'
echo '-------------------------------------'
echo "User uid:    $(id -u jenkins)"
echo "User gid:    $(id -g jenkins)"
echo "uid/gid changed: ${JENKINS_UIDGID_CHANGED}"
echo "-------------------------------------"

# fix file permissions
if [ "${JENKINS_UIDGID_CHANGED,,}" == "true" ]; then
  echo "updating file uid/gid ownership"
  chown -R jenkins:jenkins /home/jenkins
fi

AGENT_ARGS="${@}"

echo "\$0 = $0"
echo "\$@ = $@"
echo "\$AGENT_ARGS = $AGENT_ARGS"
echo "\$JAVA_OPTS = $JAVA_OPTS"

#exec /usr/local/bin/jenkins-agent "$@"
#exec su -c "/usr/local/bin/jenkins-agent ${@}" jenkins
#su -c "exec ${@}" jenkins
#su -c "exec /usr/local/bin/jenkins-agent ${@}" jenkins

## ref: https://devops.stackexchange.com/questions/2526/interference-of-docker-cmd-with-su-works-with-su-exec-but-not-with-su
#su -c "/usr/local/bin/jenkins-agent" jenkins -- "$@"
#exec su -c "/usr/local/bin/jenkins-agent ${@}" jenkins
exec su -c "/usr/local/bin/jenkins-agent $AGENT_ARGS" jenkins
