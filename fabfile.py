# Standard library
import os

# Third-party libraries
from fabric.api import *
from fabric.contrib.console import confirm

# My libraries
import ec2

env.hosts = [ec2.get_running_instance().public_dns_name]
env.user = 'ubuntu'
env.key_filename = ["%s/%s.pem" % \
                        (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])]

GITHUB_USER_NAME = "mnielsen"
GITHUB_PROJECT_NAME = "mini_qa"

def first_deploy():
    run("git clone https://github.com/%s/%s.git" % (GITHUB_USER_NAME,
                                                    GITHUB_PROJECT_NAME))
    deploy()

def prepare_deploy():
    local("python test.py")
    local("git add -p && git commit")
    local("git push origin")

def deploy():
    code_dir = "/home/ubuntu/"+GITHUB_PROJECT_NAME
    with cd(code_dir):
        run("git pull")
