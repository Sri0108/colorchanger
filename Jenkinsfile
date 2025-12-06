pipeline {
  agent any

  parameters {
    booleanParam(name: 'RUN_LOCAL', defaultValue: false, description: 'If true, run the built image on the host (bind HOST_PORT). Set false for CI/CD only.')
  }

  environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"
    KUBECONFIG_CRED = 'jenkins-kubeconfig'
    K8S_NAMESPACE = "demo"
    DEPLOYMENT_NAME = "static-site"
    SERVICE_NAME = "static-site-service"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build image') {
      steps {
        echo "Building docker image"
        sh "docker build -t ${env.IMAGE_NAME}:${env.BUILD_NUMBER} ."
      }
    }

    stage('Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME}:${BUILD_NUMBER}
            docker logout
          '''
        }
      }
    }

    stage('Run Image Locally (optional, safe)') {
      when {
        expression { return params.RUN_LOCAL == true }
      }
      steps {
        script {
          try {
            sh '''
              set -e
              echo "Attempting to remove any container named ${DEPLOYMENT_NAME}-${BUILD_NUMBER}..."
              docker rm -f ${DEPLOYMENT_NAME}-${BUILD_NUMBER} || true

              echo "Attempting to run container ${DEPLOYMENT_NAME}-${BUILD_NUMBER} on host port ${HOST_PORT}..."
              docker run -d --name ${DEPLOYMENT_NAME}-${BUILD_NUMBER} -p ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
              sleep 2
              docker ps --filter "name=${DEPLOYMENT_NAME}-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
            '''
          } catch (err) {
            echo "Warning: local docker run failed (non-fatal). Reason: ${err}"
            echo "Continuing pipeline to Kubernetes deploy."
          }
        }
      }
    }

    stage('Prepare Kubeconfig & kubectl') {
      steps {
        withCredentials([file(credentialsId: env.KUBECONFIG_CRED, variable: 'KUBECONF')]) {
          sh '''
            set -e
            # workspace kube dir
            mkdir -p "$WORKSPACE/.kube"

            # copy uploaded secret file into workspace
            cp "$KUBECONF" "$WORKSPACE/.kube/config.orig"
            chmod 600 "$WORKSPACE/.kube/config.orig"

            # download kubectl into workspace if missing (robust)
            if [ ! -x "$WORKSPACE/kubectl" ]; then
              echo "Downloading kubectl into workspace..."
              KUBE_VER=$(curl -L -s https://dl.k8s.io/release/stable.txt)
              curl -sSL --fail -o "$WORKSPACE/kubectl" "https://dl.k8s.io/release/${KUBE_VER}/bin/linux/amd64/kubectl"
              if [ ! -s "$WORKSPACE/kubectl" ]; then
                echo "kubectl download failed or empty file" >&2
                exit 1
              fi
              chmod +x "$WORKSPACE/kubectl"
            else
              echo "kubectl already present in workspace"
            fi

            # Normalize kubeconfig with workspace kubectl (embed CA etc.)
            export KUBECONFIG="$WORKSPACE/.kube/config.orig"
            echo "Normalizing kubeconfig using workspace kubectl..."
            "$WORKSPACE/kubectl" config view --raw -o yaml > "$WORKSPACE/.kube/config.tmp" || {
              echo "kubectl config view failed; falling back to original config copy"
              cp "$WORKSPACE/.kube/config.orig" "$WORKSPACE/.kube/config.tmp"
            }

            # Replace localhost/127.0.0.1 hostnames with host.docker.internal while preserving port
            # use awk to avoid problematic backslashes inside Groovy strings
            awk '/server: / {
                   gsub("127.0.0.1","host.docker.internal");
                   gsub("localhost","host.docker.internal");
                   print; next
                 } { print }' "$WORKSPACE/.kube/config.tmp" > "$WORKSPACE/.kube/config"

            chmod 600 "$WORKSPACE/.kube/config"
            echo "Prepared kubeconfig at $WORKSPACE/.kube/config"
          '''
        }
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        sh '''
          set -e

          IMAGE="${IMAGE_NAME}:${BUILD_NUMBER}"
          echo "Deploying image -> ${IMAGE} to namespace ${K8S_NAMESPACE}"

          export KUBECONFIG="$WORKSPACE/.kube/config"
          K="$WORKSPACE/kubectl --kubeconfig=$KUBECONFIG"

          echo "Using kubeconfig: $KUBECONFIG"

          # quick connectivity check (non-fatal)
          echo "Testing access to Kubernetes API..."
          if ! $K version --short >/dev/null 2>&1; then
            echo "WARNING: workspace kubectl could not contact the cluster. Check server address in kubeconfig and network connectivity."
          fi

          # ensure namespace exists
          $K get ns ${K8S_NAMESPACE} >/dev/null 2>&1 || $K create ns ${K8S_NAMESPACE}

          # generate deployment manifest with this specific image and apply
          if [ ! -f k8s/deployment.yaml ]; then
            echo "ERROR: k8s/deployment.yaml not found in repo" >&2
            exit 1
          fi
          sed "s|REPLACE_WITH_IMAGE|${IMAGE}|g" k8s/deployment.yaml > /tmp/deploy.yaml
          $K apply -f /tmp/deploy.yaml -n ${K8S_NAMESPACE}

          # apply service
          if [ -f k8s/service.yaml ]; then
            $K apply -f k8s/service.yaml -n ${K8S_NAMESPACE}
          else
            echo "Warning: k8s/service.yaml not found — ensure service exists if you expect networking."
          fi

          # wait for rollout
          $K rollout status deployment/${DEPLOYMENT_NAME} -n ${K8S_NAMESPACE} --timeout=120s

          echo "Kubernetes deploy finished."
        '''
      }
    }
  }

  post {
    success {
      script {
        echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER} deployed to ${env.K8S_NAMESPACE}"
        if (params.RUN_LOCAL) {
          echo "If local container started, access app at http://localhost:${env.HOST_PORT}"
        } else {
          echo "Local run skipped (RUN_LOCAL=false). Use kubectl port-forward or NodePort to access the app."
        }
      }
    }

    failure {
      echo "Pipeline failed — attempting cleanup and rollback (best-effort). See console for details."
      sh '''
        set +e
        docker rm -f ${DEPLOYMENT_NAME}-${BUILD_NUMBER} || true
        if [ -f "$WORKSPACE/.kube/config" ] && [ -x "$WORKSPACE/kubectl" ]; then
          export KUBECONFIG="$WORKSPACE/.kube/config"
          $WORKSPACE/kubectl rollout undo deployment/${DEPLOYMENT_NAME} -n ${K8S_NAMESPACE} || true
        fi
      '''
    }
  }
}
