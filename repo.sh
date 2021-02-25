set -eux


# Make sure we have have pipenv and set up the venv.
if [ -f Pipfile ]
then pipenv update --dev
else pipenv --python=python3.8 install --dev --pre pytest black mypy flake8 twine wheel setuptools
fi


for TPL8 in ".gitignore" ".github/workflows/pre-commit.yml" ".github/workflows/pytest.yml" "setup.cfg" ".pre-commit-config.yaml"
do
    mkdir -p $(dirname ${TPL8})
    curl https://raw.githubusercontent.com/nanassito/primitize/master/${TPL8} > ${TPL8} 
done

# Setup pre-commit
pip3.8 install pre-commit  # This needs to be installed outside of the venv :(
pre-commit install
pre-commit autoupdate
