"""
ec2.py
~~~~~~
Simple EC2 cluster management with Python.

Mostly a convenience wrapper around the boto library.  

Usage from the command line:

    python ec2.py create CLUSTER_NAME n type 

    Create a cluster with name `CLUSTER_NAME`, containing `n` machines
    of type `type`.


    python ec2.py show_all

    Shows names of all clusters currently running, and some basic data
    about each cluster.


    python ec2.py show CLUSTER_NAME

    Show details of named cluster, including the type of machines,
    indices for all machines, DNS, and instance numbers.


    python ec2.py shutdown CLUSTER_NAME

    Shutdown CLUSTER_NAME entirely


    python ec2.py shutdown_all

    Shutdown all clusters.


    python ec2.py login CLUSTER_NAME [n]

    Login to CLUSTER_NAME, to the instance with optional index n 
    (default 0).


Future expansion
~~~~~~~~~~~~~~~~

Future usage:

    python ec2.py add CLUSTER_NAME n

    Add n extra machines to CLUSTER_NAME.


    python ec2.py kill CLUSTER_NAME [n1 n2 n3...]

    Indices of the machines to kill in CLUSTER_NAME.

To export an additional method:

    ec2.boto_object(CLUSTER_NAME, index=0)

    Returns the boto object for the instance represented by CLUSTER_NAME
    and index.
"""

# Standard library
import cPickle
import os
import shelve
import subprocess
import sys
import time

# Third party libraries
from boto.ec2.connection import EC2Connection

# The list of EC2 AMIs to use, from alestic.com
AMIS = {"m1.small" : "ami-e2af508b",
        "c1.medium" : "ami-e2af508b",
        "m1.large" : "ami-68ad5201",
        "m1.xlarge" : "ami-68ad5201",
        "m2.xlarge" : "ami-68ad5201",
        "m2.2xlarge" : "ami-68ad5201",
        "m2.4xlarge" : "ami-68ad5201",
        "c1.xlarge" : "ami-68ad5201",
        "cc1.4xlarge" : "ami-1cad5275"
        }

#### Check that the environment variables we need all exist
def check_environment_variables_exist(*args):
    """
    Check that the environment variables in `*args` all exist.  If any
    do not, print an error message and exit.
    """
    vars_exist = True
    for var in args:
        if var not in os.environ:
            print "Need to set $%s environment variable" % var
            vars_exist = False
    if not vars_exist:
        print "Exiting"
        sys.exit()

check_environment_variables_exist("AWS_HOME", "AWS_KEYPAIR",
                                  "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


# Persistent shelf, used to represent all the clusters.  The keys are
# the cluster_names, and values represent cluster objects.  The
# cluster objects are just lists of objects representing instances.
# And instance objects are `dict`s with two keys, `id` and
# `public_dns_name`, representing the Amazon EC2 `id` and the public
# dns name, respectively.
#
# I considered implementing the cluster and instance objects using
# Python classes.  However, this creates problems. The reason is that
# the logic around persistence of a cluster or instance had to take
# place _outside_ the class, while the logic around starting and
# stopping EC2 instances took place within.  This separated the
# persistence logic from the EC2 logic, which seemed like a bad idea.
#
# Note that clusters is a global object because it repreent a global
# external state.
clusters = shelve.open("ec2.shelf")

ec2_conn = EC2Connection(os.environ["AWS_ACCESS_KEY_ID"], 
                         os.environ["AWS_SECRET_ACCESS_KEY"])

def create(cluster_name, n, instance_type):
    """
    Create an EC2 cluster with name `cluster_name`, and `n` instances
    of type `instance_type`.
    """
    # Parameter check
    if cluster_name in clusters:
        print "A cluster with name %s already exists.  Exiting."
        sys.exit()
    if n < 1 or n > 20:
        print "Clusters must contain between 1 and 20 instances.  Exiting."
        sys.exit()
    if not instance_type in AMIS:
        print "Instance type not recognized, setting it to be 'm1.small'."
        instance_type = "m1.small"
    ami = AMIS[instance_type]
    # Create EC2 instances
    image = ec2_conn.get_all_images(image_ids=[ami])[0]
    reservation = image.run(
        n, n, os.environ["AWS_KEYPAIR"], instance_type=instance_type)
    for instance in reservation.instances:  # Wait for the cluster to come up
        while instance.update()== u'pending':
            time.sleep(1)
    time.sleep(120) # Give the ssh daemon time to start
    # Update clusters
    cluster = [{"id": instance.id,
                "public_dns_name": instance.public_dns_name}
               for instance in reservation.instances]
    clusters[cluster_name] = cluster
    clusters.close()

def show_all():
    if len(clusters) == 0:
        print "No clusters present."
    else:
        print "Showing all clusters."
        for cluster_name in clusters:
            show(cluster_name)

def show(cluster_name):
    if cluster_name not in clusters:
        print "No cluster with the name %s exists.  Exiting." % cluster_name
        sys.exit()
    print "Instances in cluster %s:" % cluster_name
    cluster = clusters[cluster_name]
    for (j, instance) in enumerate(cluster):
        print "%s: %s" % (j, instance["public_dns_name"])

def shutdown(cluster_name):
    if cluster_name not in clusters:
        print "No cluster with the name %s exists.  Exiting." % cluster_name
        sys.exit()
    print "Shutting down cluster %s." % cluster_name
    cluster = clusters[cluster_name]
    cluster_public_dns_names = [instance["public_dns_name"]
                                for instance in cluster]
    all_running_instances = get_running_instances()
    all_public_dns_names = [instance.public_dns_name 
                            for instance in all_running_instances]
    for public_dns_name in cluster_public_dns_names:
        j = all_public_dns_names.index(public_dns_name)
        instance = all_running_instances[j]
        ec2_conn.terminate_instances([instance.id ])
    del clusters[cluster_name]
    clusters.close()

def get_running_instances():
    """
    Return all the running EC2 instances.
    """
    reservations = ec2_conn.get_all_instances()
    running_instances = [instance for reservation in reservations
                         for instance in reservation.instances 
                         if instance.update() == u"running"]
    return running_instances

def shutdown_all():
    if len(clusters) == 0:
        print "No clusters to shut down."
    else:
        for cluster_name in clusters:
            shutdown(cluster_name)

def login(cluster_name, instance_index):
    """
    ssh to `instance_index` in `cluster_name`.
    """
    if cluster_name not in clusters:
        print "No cluster with the name %s exists.  Exiting." % cluster_name
        sys.exit()
    cluster = clusters[cluster_name]
    try:
        instance = cluster[instance_index]
    except IndexError:
        print ("The instance index must be in the range 0 to %s. Exiting." %
               len(cluster)-1)
    print "SSHing to instance with address %s" % (instance.public_dns_name)
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    os.system("ssh -i %s ubuntu@%s" % (keypair, instance.public_dns_name))

def ssh(instances, cmd, background=False):
    """
    Run ``cmd`` on the command line on ``instances``.  Runs in the
    background if ``background == True``.
    """
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    append = {True: " &", False: ""}[background]
    for instance in instances:
        remote_cmd = "'nohup %s > foo.out 2> foo.err < /dev/null %s'" % (
            cmd, append)
        os.system(
            "ssh -o BatchMode=yes -i %s ubuntu@%s %s" % (
                keypair, instance.public_dns_name, remote_cmd))

def scp(instances, local_filename, remote_filename=False):
    """
    scp ``local_filename`` to ``remote_filename`` on ``instances``.
    If ``remote_filename`` is not set or is set to ``False`` then
    ``remote_filename`` is set to ``local_filename``.
    """
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    if not remote_filename:
        remote_filename = local_filename
    for instance in instances:
        os.system("scp -r -i %s %s ubuntu@%s:%s" % (
                keypair, local_filename, 
                instance.public_dns_name, remote_filename))

def start():
    """
    Create an EC2 instance, set it up, and login.
    """
    instance = create_ec2_instance("m1.small")
    subprocess.call(["fab", "first_deploy"])
    login(instance)

#### External interface

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = sys.argv[1]
    l = len(args)
    if cmd=="create" and l==4:
        create(args[1], int(args[2]), args[3])
    elif cmd=="show_all" and l==1:
        show_all()
    elif cmd=="show" and l==2:
        show(args[1])
    elif cmd=="shutdown" and l==2:
        shutdown(args[1])
    elif cmd=="shutdown_all" and l==1:
        shutdown_all()
    elif cmd=="login" and l==2:
        login(args[1], 0)
    elif cmd=="login" and l==3:
        login(args[1], int(args[2]))
    elif cmd=="ssh" and (l==2 or l==3):
        cluster.ssh(args[1:])
    else:
        print __doc__
