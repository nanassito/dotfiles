set -eux


# Extending the default .gitignore
for PATTERN in '.vscode' 'Pipfile.lock' '__pycache__/' '.mypy_cache/'; 
do
    grep $PATTERN .gitignore || echo $PATTERN >> .gitignore
done


# Make sure we have have pipenv and set up the venv.
pipenv update --dev || pipenv install --dev --pre pytest black mypy flake8


# Setup pre-commit
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
pre-commit autoupdate


# Setup python's setup.cfg
ls setup.cfg || cat > setup.cfg << EOF
[flake8]
ignore = E203, E266, E501, W503
max-line-length = 80
max-complexity = 18
select = B,C,E,F,W,T4,B9

[mypy]
ignore_missing_imports = True

[mypy-unittests]
ignore_errors = True
EOF