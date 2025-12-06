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
              echo "Attempting to remove any container named static-site-${BUILD_NUMBER}..."
              docker rm -f static-site-${BUILD_NUMBER} || true

              echo "Attempting to run container static-site-${BUILD_NUMBER} on host port ${HOST_PORT}..."
              docker run -d --name static-site-${BUILD_NUMBER} -p ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
              sleep 2
              docker ps --filter "name=static-site-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
            '''
          } catch (err) {
            echo "Warning: local docker run failed (non-fatal). Reason: ${err}"
            echo "Continuing pipeline to Kubernetes deploy."
          }
        }
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        withCredentials([file(credentialsId: env.KUBECONFIG_CRED, variable: 'KUBECONF')]) {
          sh '''
            set -e

            IMAGE="${IMAGE_NAME}:${BUILD_NUMBER}"
            echo "Deploying image -> ${IMAGE} to namespace ${K8S_NAMESPACE}"

            # copy kubeconfig into workspace
            mkdir -p "$WORKSPACE/.kube"
            cp "$KUBECONF" "$WORKSPACE/.kube/config"
            chmod 600 "$WORKSPACE/.kube/config"

            # download kubectl into workspace if missing
            if [ ! -x "$WORKSPACE/kubectl" ]; then
              echo "Downloading kubectl..."
              KUBE_VER=$(curl -L -s https://dl.k8s.io/release/stable.txt)
              curl -sSL -o "$WORKSPACE/kubectl" "https://dl.k8s.io/release/${KUBE_VER}/bin/linux/amd64/kubectl"
              chmod +x "$WORKSPACE/kubectl"
            else
              echo "kubectl already present in workspace"
            fi

            export KUBECONFIG="$WORKSPACE/.kube/config"
            K="$WORKSPACE/kubectl --kubeconfig=$KUBECONFIG"

            echo "Using kubeconfig: $KUBECONFIG"

            # ensure namespace exists
            $K get ns ${K8S_NAMESPACE} >/dev/null 2>&1 || $K create ns ${K8S_NAMESPACE}

            # generate deployment manifest with this specific image and apply
            sed "s|REPLACE_WITH_IMAGE|${IMAGE}|g" k8s/deployment.yaml > /tmp/deploy.yaml
            $K apply -f /tmp/deploy.yaml -n ${K8S_NAMESPACE}

            # apply service
            $K apply -f k8s/service.yaml -n ${K8S_NAMESPACE}

            # wait for rollout
            $K rollout status deployment/static-site -n ${K8S_NAMESPACE} --timeout=120s

            echo "Kubernetes deploy finished."
          '''
        }
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
        docker rm -f static-site-${BUILD_NUMBER} || true
        if [ -f "$WORKSPACE/.kube/config" ] && command -v "$WORKSPACE/kubectl" >/dev/null 2>&1; then
          export KUBECONFIG="$WORKSPACE/.kube/config"
          $WORKSPACE/kubectl rollout undo deployment/static-site -n ${K8S_NAMESPACE} || true
        fi
      '''
    }
  }
}
