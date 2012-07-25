"""
fabfile.py
~~~~~~~~~~

Fabric file to deploy the `mini_qa` question-answering program. The
main workflow is one of:

1. `fab first_deploy`: set up the EC2 instance, run tests, push all
   code to server

2. `fab deploy`: run tests, and push all code to server
"""

# Standard library
import os

# Third-party libraries
from fabric.api import *
from fabric.contrib.console import confirm

# My libraries
import config
import ec2.ec2 as ec2

env.hosts = ec2.public_dns_names("mini_qa")
env.user = 'ubuntu'
env.key_filename = ["%s/%s.pem" % \
                        (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])]

def start():
    """
    Create an EC2 instance, set it up, and login.
    """
    first_deploy()
    ec2.login("mini_qa", 0)

def first_deploy():
    """
    Sets up the initial git repository and other files, then do a
    standard deployment.
    """
    setup_instance()
    clone_repo()
    deploy()

def setup_instance():
    """
    Install all the required software on the remote machine, and configure
    appropriately.
    """
    # Make sure we're up to date 
    run("sudo apt-get update")
    # git
    run("sudo apt-get install -y git-core")
    run("git config --global user.name 'Michael Nielsen'")
    run("git config --global user.email 'mn@michaelnielsen.org'")
    run("git config --global core.editor emacs")
    run("git config --global alias.co checkout")
    run("git config --global credential.helper cache")
    # emacs
    run("sudo apt-get install -y emacs23")
    # Python libraries
    # Make sure the Python path includes the $HOME directory
    run("export PYTHONPATH=$HOME/")
    # Python tools
    run("sudo apt-get install -y python-dev")
    run("sudo apt-get install -y python-setuptools")
    run("sudo apt-get install -y ipython")
    # Python libraries
    run("sudo easy_install BeautifulSoup")
    run("sudo easy_install boto")

def clone_repo():
    """
    When deploying for the first time, clone the desired GitHub
    repository onto the EC2 instance.
    """
    run("git clone https://github.com/%s/%s.git" % \
        (config.GITHUB_USER_NAME, config.GITHUB_PROJECT_NAME))


def deploy():
    """
    Run tests, deploy all code to server, including code not in
    repository.
    """
    test()
    transfer_special_files()
    code_dir = "/home/ubuntu/"+config.GITHUB_PROJECT_NAME
    with cd(code_dir):
        run("git pull")

def test():
    """
    Run the tests.
    """
    local('python test.py')

def transfer_special_files():
    """
    When deploying, transfer files that are not in the repository.
    """
    put("config.py", "/home/ubuntu/%s/config.py" % 
        config.GITHUB_PROJECT_NAME)
