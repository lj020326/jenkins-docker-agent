#!/usr/bin/env bash

GIT_DEFAULT_BRANCH=main
GIT_PUBLIC_BRANCH=public

## ref: https://intoli.com/blog/exit-on-errors-in-bash-scripts/
# exit when any command fails
set -e

## https://www.pixelstech.net/article/1577768087-Create-temp-file-in-Bash-using-mktemp-and-trap
TMP_DIR=$(mktemp -d -p ~)

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT
trap 'rm -fr "$TMP_DIR"' EXIT

GIT_REMOVE_CACHED_FILES=0

CONFIRM=0
#SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$(dirname "$0")"

## PURPOSE RELATED VARS
#PROJECT_DIR=$( git rev-parse --show-toplevel )
PROJECT_DIR="$(cd "${SCRIPT_DIR}" && git rev-parse --show-toplevel)"

MIRROR_DIR_LIST="
.github
.jenkins
image
"

## ref: https://stackoverflow.com/questions/53839253/how-can-i-convert-an-array-into-a-comma-separated-string
declare -a PRIVATE_CONTENT_ARRAY
PRIVATE_CONTENT_ARRAY+=('**/private/***')
PRIVATE_CONTENT_ARRAY+=('**/vault/***')
PRIVATE_CONTENT_ARRAY+=('**/save/***')
PRIVATE_CONTENT_ARRAY+=('**/vault.yml')
PRIVATE_CONTENT_ARRAY+=('**/*vault.yml')
PRIVATE_CONTENT_ARRAY+=('**/secrets.yml')
PRIVATE_CONTENT_ARRAY+=('**/*secrets.yml')
PRIVATE_CONTENT_ARRAY+=('.vault_pass')
#PRIVATE_CONTENT_ARRAY+=('***/*vault*')
PRIVATE_CONTENT_ARRAY+=('***/vault.yml')
PRIVATE_CONTENT_ARRAY+=('**/integration_config.yml')
PRIVATE_CONTENT_ARRAY+=('**/integration_config.vault.yml')
PRIVATE_CONTENT_ARRAY+=('*.log')

printf -v EXCLUDE_AND_REMOVE '%s,' "${PRIVATE_CONTENT_ARRAY[@]}"
EXCLUDE_AND_REMOVE="${EXCLUDE_AND_REMOVE%,}"
#echo "EXCLUDE_AND_REMOVE=${EXCLUDE_AND_REMOVE}"

## ref: https://stackoverflow.com/questions/53839253/how-can-i-convert-an-array-into-a-comma-separated-string
declare -a EXCLUDES_ARRAY
EXCLUDES_ARRAY+=('.git')
EXCLUDES_ARRAY+=('.gitmodule')
EXCLUDES_ARRAY+=('.idea')
EXCLUDES_ARRAY+=('.vscode')
EXCLUDES_ARRAY+=('**/.DS_Store')
EXCLUDES_ARRAY+=('venv')
EXCLUDES_ARRAY+=('resources')
EXCLUDES_ARRAY+=('*.log')

printf -v EXCLUDES '%s,' "${EXCLUDES_ARRAY[@]}"
EXCLUDES="${EXCLUDES%,}"


## https://serverfault.com/questions/219013/showing-total-progress-in-rsync-is-it-possible
## https://www.studytonight.com/linux-guide/how-to-exclude-files-and-directory-using-rsync
RSYNC_OPTS_GIT_MIRROR=(
    -dar
    --links
    --delete-excluded
    --exclude={"${EXCLUDES},${EXCLUDE_AND_REMOVE}"}
)

RSYNC_OPTS_GIT_UPDATE=(
    -ari
    --links
)

function gitcommitpush() {
  local LOCAL_BRANCH="$(git symbolic-ref --short HEAD)" && \
  local REMOTE_AND_BRANCH=$(git rev-parse --abbrev-ref ${LOCAL_BRANCH}@{upstream}) && \
  IFS=/ read REMOTE REMOTE_BRANCH <<< ${REMOTE_AND_BRANCH} && \
  echo "Staging changes:" && \
  git add -A || true && \
  echo "Committing changes:" && \
  git commit -am "group updates to public branch" || true && \
  echo "Pushing branch '${LOCAL_BRANCH}' to remote '${REMOTE}' branch '${REMOTE_BRANCH}':" && \
  git push -f -u ${REMOTE} ${LOCAL_BRANCH}:${REMOTE_BRANCH} || true
}

function isInstalled() {
    command -v "${1}" >/dev/null 2>&1 || return 1
}

function checkRequiredCommands() {
    missingCommands=""
    for currentCommand in "$@"
    do
        isInstalled "${currentCommand}" || missingCommands="${missingCommands} ${currentCommand}"
    done

    if [[ ! -z "${missingCommands}" ]]; then
        fail "checkRequiredCommands(): Please install the following commands required by this script:${missingCommands}"
    fi
}

function search_repo_keywords () {
  local LOG_PREFIX="search_repo_keywords():"

  local REPO_EXCLUDE_DIR_LIST=(".git")
  REPO_EXCLUDE_DIR_LIST+=(".idea")
  REPO_EXCLUDE_DIR_LIST+=("venv")
  REPO_EXCLUDE_DIR_LIST+=("private")
  REPO_EXCLUDE_DIR_LIST+=("save")

  #export -p | sed 's/declare -x //' | sed 's/export //'
  if [ -z ${REPO_EXCLUDE_KEYWORDS+x} ]; then
    echo "${LOG_PREFIX} REPO_EXCLUDE_KEYWORDS not set/defined"
    exit 1
  fi

  #echo "${LOG_PREFIX} REPO_EXCLUDE_KEYWORDS=${REPO_EXCLUDE_KEYWORDS}"

  IFS=',' read -ra REPO_EXCLUDE_KEYWORDS_ARRAY <<< "$REPO_EXCLUDE_KEYWORDS"

  #echo "${LOG_PREFIX} REPO_EXCLUDE_KEYWORDS_ARRAY=${REPO_EXCLUDE_KEYWORDS_ARRAY[*]}"

  # ref: https://superuser.com/questions/1371834/escaping-hyphens-with-printf-in-bash
  #'-e' ==> '\055e'
  local GREP_DELIM=' \055e '
  printf -v GREP_PATTERN_SEARCH "${GREP_DELIM}%s" "${REPO_EXCLUDE_KEYWORDS_ARRAY[@]}"

  ## strip prefix
  GREP_PATTERN_SEARCH=${GREP_PATTERN_SEARCH#"$GREP_DELIM"}
  ## strip suffix
  #GREP_PATTERN_SEARCH=${GREP_PATTERN_SEARCH%"$GREP_DELIM"}

  #echo "${LOG_PREFIX} GREP_PATTERN_SEARCH=${GREP_PATTERN_SEARCH}"

  local GREP_COMMAND="grep ${GREP_PATTERN_SEARCH}"
  #echo "${LOG_PREFIX} GREP_COMMAND=${GREP_COMMAND}"

  local FIND_DELIM=' -o '
#  printf -v FIND_EXCLUDE_DIRS "\055path %s${FIND_DELIM}" "${REPO_EXCLUDE_DIR_LIST[@]}"
#  printf -v FIND_EXCLUDE_DIRS "! -path %s${FIND_DELIM}" "${REPO_EXCLUDE_DIR_LIST[@]}"
#  printf -v FIND_EXCLUDE_DIRS "\055path '*/%s/*'${FIND_DELIM}" "${REPO_EXCLUDE_DIR_LIST[@]}"
#  printf -v FIND_EXCLUDE_DIRS "\055path '*/%s/*' -prune${FIND_DELIM}" "${REPO_EXCLUDE_DIR_LIST[@]}"
  printf -v FIND_EXCLUDE_DIRS "! -path '*/%s/*'${FIND_DELIM}" "${REPO_EXCLUDE_DIR_LIST[@]}"
  local FIND_EXCLUDE_DIRS=${FIND_EXCLUDE_DIRS%$FIND_DELIM}

  #echo "${LOG_PREFIX} FIND_EXCLUDE_DIRS=${FIND_EXCLUDE_DIRS}"

  ## this works:
  ## find . \( -path '*/.git/*' \) -prune -name '.*' -o -exec grep -i example {} 2>/dev/null +
  ## find . \( -path '*/save/*' -prune -o -path '*/.git/*' -prune \) -o -exec grep -i alsac {} 2>/dev/null +
  ## find . \( ! -path '*/save/*' -o ! -path '*/.git/*' \) -o -exec grep -i alsac {} 2>/dev/null +
  ## ref: https://stackoverflow.com/questions/6565471/how-can-i-exclude-directories-from-grep-r#8692318
  ## ref: https://unix.stackexchange.com/questions/342008/find-and-echo-file-names-only-with-pattern-found
  ## ref: https://www.baeldung.com/linux/find-exclude-paths
  local FIND_CMD="find ${PROJECT_DIR}/ \( ${FIND_EXCLUDE_DIRS} \) -o -exec ${GREP_COMMAND} {} 2>/dev/null +"
  #echo "${LOG_PREFIX} ${FIND_CMD}"

  local EXCEPTION_COUNT=$(eval "${FIND_CMD} | wc -l")
  if [[ $EXCEPTION_COUNT -eq 0 ]]; then
    echo "${LOG_PREFIX} SUCCESS => No exclusion keyword matches found!!"
  else
    echo "${LOG_PREFIX} There are [${EXCEPTION_COUNT}] exclusion keyword matches found:"
    eval "${FIND_CMD}"
    exit 1
  fi
  return "${EXCEPTION_COUNT}"
}

function sync_public_branch() {

  git fetch --all
  git checkout ${GIT_DEFAULT_BRANCH}

  #RSYNC_OPTS=${RSYNC_OPTS_GIT_MIRROR[@]}

  #echo "copy project to temporary dir $TMP_DIR"
  #local RSYNC_CMD="rsync ${RSYNC_OPTS} ${PROJECT_DIR}/ ${TMP_DIR}/"
  local RSYNC_CMD="rsync ${RSYNC_OPTS_GIT_MIRROR[*]} ${PROJECT_DIR}/ ${TMP_DIR}/"
  #echo "${RSYNC_CMD}"
  eval ${RSYNC_CMD}

  echo "Checkout public branch"
  git checkout ${GIT_PUBLIC_BRANCH}

  if [ $GIT_REMOVE_CACHED_FILES -eq 1 ]; then
    echo "Removing files cached in git"
    git rm -r --cached .
  fi

  #echo "Removing existing non-dot files for clean sync"
  #rm -fr *

  echo "Copy ${TMP_DIR} to project dir $PROJECT_DIR"
  #echo "rsync ${RSYNC_OPTS_GIT_UPDATE[@]} ${TMP_DIR}/ ${PROJECT_DIR}/"
  RSYNC_CMD="rsync ${RSYNC_OPTS_GIT_UPDATE[*]} ${TMP_DIR}/ ${PROJECT_DIR}/"
  echo "${RSYNC_CMD}"
  eval ${RSYNC_CMD}

  IFS=$'\n'
  for dir in ${MIRROR_DIR_LIST}
  do
    echo "Mirror ${TMP_DIR}/${dir}/ to project dir $PROJECT_DIR/${dir}/"
    RSYNC_CMD="rsync ${RSYNC_OPTS_GIT_MIRROR[*]} ${TMP_DIR}/${dir}/ ${PROJECT_DIR}/${dir}/"
    echo "${RSYNC_CMD}"
    eval ${RSYNC_CMD}
  done

  printf -v TO_REMOVE '%s ' "${PRIVATE_CONTENT_ARRAY[@]}"
  TO_REMOVE="${TO_REMOVE% }"
  echo "TO_REMOVE=${TO_REMOVE}"
  CLEANUP_CMD="rm -fr ${TO_REMOVE}"
  echo "${CLEANUP_CMD}"
  eval ${CLEANUP_CMD}

  echo "Show changes before push:"
  git status

  ## https://stackoverflow.com/questions/5989592/git-cannot-checkout-branch-error-pathspec-did-not-match-any-files-kn
  ## git diff --name-only public ${GIT_DEFAULT_BRANCH} --

  if [ $CONFIRM -eq 0 ]; then
    ## https://www.shellhacks.com/yes-no-bash-script-prompt-confirmation/
    read -p "Are you sure you want to merge the changes above to public branch ${TARGET_BRANCH}? " -n 1 -r
    echo    # (optional) move to a new line
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        exit 1
    fi
  fi

  ## https://stackoverflow.com/questions/5738797/how-can-i-push-a-local-git-branch-to-a-remote-with-a-different-name-easily
  echo "Add all the files:"
  gitcommitpush
  echo "Checkout ${GIT_DEFAULT_BRANCH} branch:" && \
  git checkout ${GIT_DEFAULT_BRANCH}
}


function usage() {
  echo "Usage: ${0} [options]"
  echo ""
  echo "  Options:"
  echo "       -L [ERROR|WARN|INFO|TRACE|DEBUG] : run with specified log level (default INFO)"
  echo "       -v : show script version"
  echo "       -h : help"
  echo "     [TEST_CASES]"
  echo ""
  echo "  Examples:"
	echo "       ${0} "
	echo "       ${0} -L DEBUG"
  echo "       ${0} -v"
	[ -z "$1" ] || exit "$1"
}


function main() {

  checkRequiredCommands rsync

  while getopts "L:vh" opt; do
      case "${opt}" in
          L) setLogLevel "${OPTARG}" ;;
          v) echo "${VERSION}" && exit ;;
          h) usage 1 ;;
          \?) usage 2 ;;
          *) usage ;;
      esac
  done
  shift $((OPTIND-1))

  #echo "EXCLUDES=${EXCLUDES}"

  #echo "PROJECT_DIR=${PROJECT_DIR}"
  #echo "TMP_DIR=${TMP_DIR}"

#  search_repo_keywords
  eval search_repo_keywords
  local RETURN_STATUS=$?
  if [[ $RETURN_STATUS -ne 0 ]]; then
    echo "${LOG_PREFIX} search_repo_keywords: FAILED"
    exit ${RETURN_STATUS}
  fi

  sync_public_branch

}

main "$@"
