# K8s Deployment Instructions

This guide provides step-by-step instructions for deploying the application on a Kubernetes cluster. The deployment files should be applied in the following order: `ollama`, `postgres`, `redis`, `web`, `celery`, and `celery-beat`.

## Prerequisites

- A running Kubernetes cluster
- `kubectl` installed and configured to interact with your cluster

## Configuration

- To get a LetsEncrypt SSL certificate, you'll require to set up the Nginx Ingres Controller first. Then, configure the DNS record. Following that repace rengine.example.com to the domain name that you wish to receive SSL certificate for.

- To use openssl or existing SSL certificate you can use `nginx-certificates` secret instead of `rengine-tls` secret and ignore creating cert-manager. 

## Step 1: Install the Ingress Controller

1. **Add the NGINX Ingress Controller Helm repository:**
    ```sh
    helm repo add nginx-stable https://helm.nginx.com/stable
    helm repo update
    ```

2. **Install the NGINX Ingress Controller:**
    ```sh
    helm install nginx-ingress nginx-stable/nginx-ingress --namespace ingress-nginx --create-namespace --set controller.service.type=LoadBalancer
    ```

## Step 2: Install Cert Manager

1. **Add the Jetstack Helm repository:**
    ```sh
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    ```

2. **Install Cert Manager:**
    ```sh
    helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --version v1.11.0 \
    --set installCRDs=true
    ```

3. **Verify the installation:**
    ```sh
    kubectl get pods --namespace cert-manager
    ```

## Step 3: Install OpenEBS NFS Provisioner (Optional)

Note: Either you can install it manually or use the OpenEBS provisioner from the marketplace in the Cloud Provider. 

1. **Add the OpenEBS Helm repository:**
    ```sh
    helm repo add openebs https://openebs.github.io/charts
    helm repo update
    ```

2. **Install OpenEBS NFS Provisioner:**
    ```sh
    helm install openebs-nfs openebs/openebs --namespace openebs --create-namespace
    ```

3. **Verify the installation:**
    ```sh
    kubectl get pods --namespace openebs
    ```

4. **Create the Storage Class nfsrwx**
    ```sh
    kubectl apply -f - <<EOF
        apiVersion: storage.k8s.io/v1
        kind: StorageClass
        metadata:
          annotations:
            cas.openebs.io/config: |
              - name: NSFServerType
                value: "kernel"
              - name: BackendStorageClass
                value: "do-block-storage"
            openebs.io/cas-type: nsfrwx
          name: nfs-rwx-storage
        provisioner: openebs.io/nfsrwx
        reclaimPolicy: Delete
        volumeBindingMode: Immediate
        EOF
    ```

## Step 4: Deploy the Application Manifests

1. **Navigate to the `k8s` directory:**
    ```sh
    cd k8s
    ```

2. **Apply the manifests in the following order:**
    ```sh
    kubectl apply -f sc.yml
    kubectl apply -f pvc.yml
    kubectl apply -f ollama/
    kubectl apply -f postgres/
    kubectl apply -f redis/
    kubectl apply -f web/
    kubectl apply -f celery/
    kubectl apply -f celery-beat/
    kubectl apply -f cert-manager/
    kubectl apply -f nginx/
    ```

## Step 5: Verify the Deployment

1. **Check the status of the pods:**
    ```sh
    kubectl get pods
    ```

2. **Check the status of the services:**
    ```sh
    kubectl get svc
    ```

3. **Check the status of the Ingress:**
    ```sh
    kubectl get ingress
    ```

## Additional Configuration

- **Ingress Configuration:** Ensure that your Ingress resources are correctly configured to route traffic to your services.
- **Certificates:** Use Cert Manager to issue and manage TLS certificates for your Ingress resources.
- **Persistent Volumes:** Ensure that your Persistent Volume Claims (PVCs) are correctly bound to the Persistent Volumes (PVs) provided by OpenEBS NFS Provisioner.

By following these steps, you should be able to deploy your application on Kubernetes with the necessary Ingress controller, Cert Manager, and OpenEBS NFS Provisioner.