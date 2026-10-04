import subprocess
import sys
import re

"""
This script is used to get the list of mongodb pod and its IP so we we can reconfigure

replicas set with IP instead of FQDN.
"""
namespace, user, password = sys.argv[1],sys.argv[2],sys.argv[3]
output = subprocess.check_output("kubectl get pod -n {0} -o custom-columns=NAME:metadata.name,IP:status.podIP |grep -iE 'mongodb-[0-5]'".format(namespace), shell=True)
mongo_host = output.decode("utf-8").strip()
primary_replicaset=None

for idx, line in enumerate(sorted(mongo_host.split("\n"))):
    res = re.search(r'\s*(.+?)\s+(.+?)\s*$', line)
    pod_name=res.group(1)
    pod_ip=res.group(2)
    if re.search('mongodb-0',pod_name):
       primary_replicaset = pod_name
    print("Updating mongo pod {} replicaset name with host:{}".format(pod_name, pod_ip))
    cmd = "kubectl exec -it {0} -n {1} -- /bin/bash  -c ' echo  \"cfg=rs.conf() \n cfg.members[{2}].host=\\\"{3}\\\" \n  rs.reconfig(cfg)\" | mongosh --host localhost --port 27017  --authenticationDatabase admin -u {4} -p {5} ' ".format(primary_replicaset, namespace, idx,  pod_ip, user, password)
    mongo_out = subprocess.check_output(cmd, shell=True)
    mongo_res = mongo_out.decode("utf-8").strip()

