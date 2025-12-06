pipeline {
  agent any

  parameters {
    booleanParam(name: 'RUN_LOCAL', defaultValue: false, description: 'If true, run the built image on the host (bind HOST_PORT). Set false for CI/CD only.')
  }

  environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"                     // host port to forward to (optional)
    KUBECONFIG_CRED = 'jenkins-kubeconfig' // Secret file credential in Jenkins
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
          // Best-effort: remove any container that already binds the HOST_PORT, then try run.
          // Errors are caught and logged, but non-fatal.
          try {
            sh """
              set -e
              echo "Checking for containers binding host port ${HOST_PORT}..."
              # List containers and their published ports, find ones exposing :${HOST_PORT}
              CANDIDATES=\$(docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' | grep ':${HOST_PORT}' || true)
              if [ -n "\$CANDIDATES" ]; then
                echo "Found containers using port ${HOST_PORT}:"
                echo "\$CANDIDATES"
                # remove each candidate container id (first column)
                echo "\$CANDIDATES" | awk '{print \$1}' | xargs -r -n1 docker rm -f || true
                echo "Removed containers that were binding ${HOST_PORT} (if any)."
              else
                echo "No containers were found binding ${HOST_PORT}."
              fi

              # Also try to detect any non-docker process using port (Linux host)
              if command -v ss >/dev/null 2>&1; then
                PROC=\$(ss -ltnp 2>/dev/null | grep ':${HOST_PORT}' || true)
                if [ -n "\$PROC" ]; then
                  echo "Process found listening on port ${HOST_PORT}:"
                  echo "\$PROC"
                  echo "Attempting to show PID and kill (best-effort):"
                  # extract pid from ss output like "users:(("process",pid=1234,fd=...)"
                  PIDS=\$(ss -ltnp 2>/dev/null | grep ':${HOST_PORT}' | sed -n 's/.*pid=\\([0-9]*\\).*/\\1/p' | uniq)
                  if [ -n "\$PIDS" ]; then
                    echo "Killing PIDs: \$PIDS (best-effort)"
                    echo \$PIDS | xargs -r -n1 kill -9 || true
                  fi
                fi
              fi

              echo "Starting local container (best-effort)..."
              docker rm -f static-site-${BUILD_NUMBER} || true
              docker run -d --name static-site-${BUILD_NUMBER} -p ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
              sleep 2
              docker ps --filter "name=static-site-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
            """
          } catch (err) {
            echo "Warning: local docker run failed or port cleanup failed (non-fatal). Reason: ${err}"
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

            # prepare kubeconfig for kubectl
            mkdir -p $HOME/.kube
            cp "$KUBECONF" $HOME/.kube/config
            chmod 600 $HOME/.kube/config

            # ensure namespace exists
            if ! kubectl get ns ${K8S_NAMESPACE} >/dev/null 2>&1; then
              kubectl create ns ${K8S_NAMESPACE}
            fi

            # generate deployment manifest from template (replace placeholder) and apply
            sed "s|REPLACE_WITH_IMAGE|${IMAGE}|g" k8s/deployment.yaml > /tmp/deploy.yaml
            kubectl apply -f /tmp/deploy.yaml -n ${K8S_NAMESPACE}

            # apply service (idempotent)
            kubectl apply -f k8s/service.yaml -n ${K8S_NAMESPACE}

            # wait for rollout to complete
            kubectl rollout status deployment/static-site -n ${K8S_NAMESPACE} --timeout=120s

            echo "Kubernetes deploy finished."
          '''
        }
      }
    }
  }

  post {
    success {
      echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER} deployed to ${env.K8S_NAMESPACE}"
      if (params.RUN_LOCAL.toBoolean()) {
        echo "If local container started, access app at http://localhost:${env.HOST_PORT}"
      } else {
        echo "Local run skipped (RUN_LOCAL=false). Use kubectl port-forward or NodePort to access the app."
      }
    }

    failure {
      echo "Pipeline failed — attempting cleanup and rollback (best-effort). See console for details."
      sh '''
        set +e
        docker rm -f static-site-${BUILD_NUMBER} || true
        if command -v kubectl >/dev/null 2>&1; then
          kubectl rollout undo deployment/static-site -n ${K8S_NAMESPACE} || true
        fi
      '''
    }
  }
}
