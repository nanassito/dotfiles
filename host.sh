set -eux

sudo apt-get install less

pip3.8 install --user pipenv pre-commit ipython

grep "nanassrc" ~/.bashrc || echo "source $(dirname "${BASH_SOURCE[0]}")/nanassrc" >> ~/.bashrc