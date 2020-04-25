which pip3.8 || echo "Could not find pip3.8 in $PATH"
which pip3.8 || return 1


# Extending the default .gitignore
for PATTERN in '.vscode' 'Pipefile.lock'; 
do
    grep $PATTERN .gitignore || echo $PATTERN >> .gitignore
done


# Make sure we have have pipenv and set up the venv.
pip3.8 install --user pipenv
pipenv update --dev || pipenv install --dev --pre pytest black mypy flake8


# Setup pre-commit
pip3.8 install --user pre-commit
pre-commit install
ls .pre-commit-config.yaml || cat > .pre-commit-config.yaml << EOF
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v2.3.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
-   repo: https://github.com/psf/black
    rev: 19.3b0
    hooks:
    - id: black
-   repo: https://gitlab.com/pycqa/flake8
    rev: 3.7.8
    hooks:
    -   id: flake8
-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.720
    hooks:
    -   id: mypy
EOF
pre-commit update
