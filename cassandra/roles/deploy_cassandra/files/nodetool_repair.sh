#!/bin/sh
NAMESPACE=$1
echo "Namespace: "$NAMESPACE
for i in $(kubectl get pods -n $NAMESPACE -o=jsonpath='{range .items..metadata}{.name}{"\n"}{end}' | fgrep \cassandra- );
  do
    kubectl exec -it -n $NAMESPACE $i -- nodetool repair
    sleep 900
    echo $i
    echo "processed"
  done
