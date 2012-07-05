"""
ec2.py
~~~~~~
Simple EC2 cluster management with Python.

Mostly a convenience wrapper around the boto library.

Useage from the command line:

    python ec2.py create CLUSTER_NAME n type 

    Create a cluster with name `CLUSTER_NAME`, containing `n` machines
    of type `type`.


    python ec2.py show_all

    Shows names of all clusters currently running, and some basic data.


     python ec2.py show CLUSTER_NAME

     Show details of named cluster, including the type of machines,
    indices for all machines, DNS, and instance numbers.


     python ec2.py shutdown CLUSTER_NAME

     Shutdown CLUSTER_NAME entirely


     python ec2.py shutdown_all

     Shutdown all clusters.


     python ec2.py ssh CLUSTER_NAME [n]

     ssh in to CLUSTER_NAME, to the instance with optional index n 
     (default 0).


Future expansion
~~~~~~~~~~~~~~~~

Future usage:

     python ec2.py add CLUSTER_NAME n

     Add n extra machines to CLUSTER_NAME.


     python ec2.py kill CLUSTER_NAME [n1 n2 n3...]

     Indices of the machines to kill in CLUSTER_NAME.

To export an additiona method:

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
import redis

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


#### Check that the Redis key we need already exists
r = redis.Redis(host='localhost', port=6379, db=0)
if not r.exists("ec2_clusters"):
    r.set("ec2_clusters", cPickle.dumps([]))


class Cluster():

    def __init__(self, name):
        self.name = name

    def create(self, n, instance_type):
        """
        Create an EC2 cluster with name `self.name`, `n` instances, of
        type `instance_type`.
        """
        r = redis.Redis(host='localhost', port=6379, db=0)
        clusters = cPickle.loads(r.get("ec2_clusters"))
        if self.name in clusters:
            print "A cluster with name %s already exists.  Exiting."
            sys.exit()
        ec2_conn = EC2Connection(os.environ["AWS_ACCESS_KEY_ID"], 
                                 os.environ["AWS_SECRET_ACCESS_KEY"])
        try:
            ami = AMIS[instance_type]
        except:
            ami = AMIS["m1.small"]
        image = ec2_conn.get_all_images(image_ids=[ami])[0]
        reservation = image.run(
            n, n, os.environ["AWS_KEYPAIR"], instance_type=instance_type)
        instances = reservation.instances
        # Wait for the cluster to come up
        for instance in instances:
            while instance.update()== u'pending':
                time.sleep(1)
        # Reload, just in case anything has changed
        clusters = cPickle.loads(r.get("ec2_clusters"))
        instance_descriptions = [instance.public_dns_name for
                                 instance in instances]
        clusters.append(
            (self.name, instance_descriptions))
        r.set("ec2_clusters", cPickle.dumps(clusters))
        # Give the ssh daemon time to start
        time.sleep(120) 

    def show(self):
        print "Instances in cluster %s" % self.name
        cluster = self.cluster_instances()
        if cluster == None:
            print "No cluster with that name.  Exiting."
            sys.exit()
        for (j, instance_dns) in enumerate(cluster):
            print "%s: %s" % (j, instance_dns)

    def shutdown(self):
        running_instances = get_running_instances()
        public_dns_names = [instance.public_dns_name 
                            for instance in running_instances]
        for public_dns_name in self.cluster_instances():
            if public_dns_name in public_dns_names:
                j = public_dns_names.index(public_dns_name)
                instance = running_instances[j]
                ec2_conn = EC2Connection(
                    os.environ["AWS_ACCESS_KEY_ID"], 
                    os.environ["AWS_SECRET_ACCESS_KEY"])
                ec2_conn.terminate_instances([instance.id ])
        r = redis.Redis(host='localhost', port=6379, db=0)
        clusters = cPickle.loads(r.get("ec2_clusters"))
        clusters = [(name, cluster) for (name, cluster) in clusters 
                    if name != self.name]
        r.set("ec2_clusters", cPickle.dumps(clusters))

            
    def cluster_instances(self):
        r = redis.Redis(host='localhost', port=6379, db=0)
        clusters = cPickle.loads(r.get("ec2_clusters"))
        filtered_clusters = [cluster for (name, cluster) in clusters
                             if name == self.name]
        if len(filtered_clusters) == 0:
            return None
        else:
            return filtered_clusters[0]


def show_all():
    r = redis.Redis(host='localhost', port=6379, db=0)
    clusters = cPickle.loads(r.get("ec2_clusters"))
    if len(clusters) == 0:
        print "No clusters exist"
    else:
        print "Showing all clusters"
        for (name, cluster) in clusters:
            Cluster(name).show()

def shutdown_all():
    for name in get_cluster_names():
        Cluster(name).shutdown()

def get_cluster_names():
    r = redis.Redis(host='localhost', port=6379, db=0)
    return [name for (name, cluster) in cPickle.loads(r.get("ec2_clusters"))]

def get_running_instances():
    """
    Return all the running EC2 instances.
    """
    ec2_conn = EC2Connection(
        os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
    reservations = ec2_conn.get_all_instances()
    running_instances = [instance for reservation in reservations
                         for instance in reservation.instances 
                         if instance.update() == u"running"]
    return running_instances


def login(instance):
    """
    ssh to `instance`.
    """
    print "SSHing to instance with address %s" % (instance.public_dns_name)
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    os.system("ssh -i %s ubuntu@%s" % (keypair, instance.public_dns_name))

def start():
    """
    Create an EC2 instance, set it up, and login.
    """
    instance = create_ec2_instance("m1.small")
    subprocess.call(["fab", "first_deploy"])
    login(instance)


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

#### External interface

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = sys.argv[1]
    l = len(args)
    if cmd=="create" and l==4:
        cluster = Cluster(args[1])
        cluster.create(int(args[2]), args[3])
    elif cmd=="show_all" and l==1:
        show_all()
    elif cmd=="show" and l==2:
        cluster = Cluster(args[1])
        cluster.show()
    elif cmd=="shutdown" and l==2:
        cluster = Cluster(args[1])
        cluster.shutdown()
    elif cmd=="shutdown_all" and l==3:
        shutdown_all()
    elif cmd=="ssh" and (l==2 or l==3):
        cluster = Cluster(args[1])
        cluster.ssh(args[2:])
    else:
        print self.__doc__()
