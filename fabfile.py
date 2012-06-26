"""
fabfile.py
~~~~~~~~~~

Fabric file to aid in deploying the `mini_qa` question-answering
program. The main workflow is one of the following:

1. `fab deploy`: run tests, push all code to server

2. `fab full_deploy`: run tests, and push all code to server

"""

# Standard library
import os

# Third-party libraries
from fabric.api import *
from fabric.contrib.console import confirm

# My libraries
import config
import ec2

env.hosts = [ec2.get_running_instance().public_dns_name]
env.user = 'ubuntu'
env.key_filename = ["%s/%s.pem" % \
                        (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])]

def first_deploy():
    """
    Sets up the initial git repository and other files, then does a
    standard deployment.
    """
    setup_instance()
    run("git clone https://github.com/%s/%s.git" % (config.GITHUB_USER_NAME,
                                                    config.GITHUB_PROJECT_NAME))
    put("config.py", "/home/ubuntu/%s/config.py" % 
        config.GITHUB_PROJECT_NAME)
    deploy()

def setup_instance():
    """
    Install all the required software on the remote machine, and configure
    appropriately.
    """
    # Make sure we're up to date 
    run("sudo apt-get update")
    # git
    run(sudo apt-get install -y git-core)
    run(git config --global user.name "Michael Nielsen")
    run(git config --global user.email "mn@michaelnielsen.org")
    run(git config --global core.editor emacs)
    run(git config --global alias.co checkout)
    run(git config --global credential.helper cache)
    # emacs
    run(sudo apt-get install -y emacs23)
    # Python libraries
    # Make sure the Python path includes the $HOME directory
    run(export PYTHONPATH=$HOME/)
    # Python tools
    run(sudo apt-get install -y python-dev)
    run(sudo apt-get install -y python-setuptools)
    run(sudo apt-get install -y ipython)
    # Python libraries
    run(sudo easy_install BeautifulSoup)
    run(sudo easy_install boto)

def deploy():
    """
    Run tests, deploy all code to server, including code not in
    repository.
    """
    local("python test.py")
    code_dir = "/home/ubuntu/"+config.GITHUB_PROJECT_NAME
    with cd(code_dir):
        run("git pull")
        put("config.py", "/home/ubuntu/%s/config.py" % 
            config.GITHUB_PROJECT_NAME)

def full_deploy():
    """
    Run tests, commit code, and deploy all code to server.
    """
    prepare_deploy()
    deploy()
