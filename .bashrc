# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# Add a return code to the prompt before each command.
PROMPT_COMMAND=enhanced_prompt
ORIG_PS1=$PS1
enhanced_prompt() {
    local EXIT="$?"

    local RCol='\[\e[0m\]'

    local Red='\[\e[0;31m\]'
    local Gre='\[\e[0;32m\]'
    local BYel='\[\e[1;33m\]'
    local BBlu='\[\e[1;34m\]'
    local Pur='\[\e[0;35m\]'

    if [ $EXIT != 0 ]; then
        STATUS="${Red}<$EXIT>${RCol}"      # Add red if exit code non 0
    else
        STATUS="${Gre}<$EXIT>${RCol}"
    fi

    PS1="$STATUS\n$ORIG_PS1"
}


fail() {
    echo $1
    return 1
}


pypi_publish() {
    [[ -z $(git status --porcelain) ]] || fail "Uncommited changes"
    git branch | grep master || fail "Need to be on master"
    rm -r dist/ build/ *.egg-info/
    pipenv run python setup.py sdist bdist_wheel
    pipenv run twine upload dist/*
}