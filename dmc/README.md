# DMC

The Domain Model Controller. 

### Set up Kubernetes
Follow this [guide to setting up Airflow on K8s](https://medium.com/uncanny-recursions/setting-up-airflow-on-a-local-kubernetes-cluster-using-helm-57eb0b73dc02)

```
# Install dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0/aio/deploy/recommended.yaml

# Create service account 
kubectl create sa admin-user -n kubernetes-dashboard

# run proxy
kubectl proxy
```

Now get a [bearer token for K8s](https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/creating-sample-user.md#getting-a-bearer-token):

```
kubectl -n kubernetes-dashboard get secret $(kubectl -n kubernetes-dashboard get sa/admin-user -o jsonpath="{.secrets[0].name}") -o go-template="{{.data.token | base64decode}}"
```

It should print something like:

```
eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlcm5ldGVzLWRhc2hib2FyZCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuLXY1N253Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiIwMzAzMjQzYy00MDQwLTRhNTgtOGE0Ny04NDllZTliYTc5YzEiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZXJuZXRlcy1kYXNoYm9hcmQ6YWRtaW4tdXNlciJ9.Z2JrQlitASVwWbc-s6deLRFVk5DWD3P_vjUFXsqVSY10pbjFLG4njoZwh8p3tLxnX_VBsr7_6bwxhWSYChp9hwxznemD5x5HLtjb16kI9Z7yFWLtohzkTwuFbqmQaMoget_nYcQBUC5fDmBHRfFvNKePh_vSSb2h_aYXa8GV5AcfPQpY7r461itme1EXHQJqv-SN-zUnguDguCTjD80pFZ_CmnSE1z9QdMHPB8hoB4V68gtswR1VLa6mSYdgPwCHauuOobojALSaMc3RH7MmFUumAgguhqAkX3Omqd3rJbYOMRuMjhANqd08piDC3aIabINX6gP5-Tuuw2svnV6NYQ
```

Now go to the [K8s dashboard](http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/overview?namespace=default) and put in your token.


### Install Helm
On mac:

```
brew install helm
kubectl create namespace airflow
helm repo add stable https://charts.helm.sh/stable/
helm dep update
```

### Run Airflow on Kubernetes

Next, clone the Airflow repository with:

```
git clone git@github.com:apache/airflow.git
```

Navigate to the `chart` directory within the Airflow repo and replace `values.yaml` with the `dmc/configs/values.yaml` in this repository.

You will need to replace every line that contains `path: "//Users/brandonrose/repos/WM/dojo/dmc/dags"` to an appropriate path to your `dags` directory within this repo:

```
path: "//Users/path/to/dojo/dmc/dags"
```

This mounts your dags locally to the various Airflow components. Now you are ready to run Airflow. Make sure you are in `airflow/chart` and run:


```
helm install airflow .
```

Next, create an Airflow user by exec'ing into the Airflow `webserver` container:

```
docker ps | grep webserver |  awk '{print $1}'
```

This should return something like `367f129dd078` which is the ID of the scheduler container.

Next, run:

```
docker exec -it 367f129dd078 /bin/bash
```

From here, run something like:

```
airflow users create \
          --username brandon \
          --firstname brandon \
          --lastname rose \
          --role Admin \
          --email admin@example.org
```

When prompted for a password, enter one. Then, run:

```
kubectl port-forward svc/airflow-webserver 8080:8080 --namespace default
```

Now you should be able to navigate to the [Airflow Dashboard](http://127.0.0.1:8080/admin/). After entering your username and password you will see any DAG that is available in the `dags` directory listed.


### Create Persistent Volume
Then create a persistent volume and claim:

```
kubectl apply -f configs/results-volume.yaml
```

Note that if you need to delete this you have to run:

```
kubectl patch pvc results-claim -p '{"metadata":{"finalizers": []}}' --type=merge
kubectl delete pvc results-claim
kubectl delete persistentvolume results-volume
```

### Triggering the DAG
Since we have created a DAG called `fsc`, we can either trigger it in the [Airflow Dashboard](http://127.0.0.1:8080/admin/) or we can exec into the scheduler and trigger it there. First, find the name of your scheduler:

```
docker ps | grep scheduler_airflow-scheduler |  awk '{print $1}'
```

This should return something like `367f129dd078` which is the ID of the scheduler container.

Next, run:

```
docker exec -it 367f129dd078 /bin/bash
```

> Note: you must replace the above command with appropriate scheduler container ID

You can then list available DAGs with:

```
airflow dags list
```

You should see `fsc` listed, which you can trigger with:

```
airflow dags trigger fsc
```
