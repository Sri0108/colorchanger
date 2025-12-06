pipeline {
  agent any

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

    stage('Run Image Locally (optional)') {
      steps {
        script {
          // optional local run for quick smoke test; keep or remove as you like
          sh """
            docker rm -f static-site-${BUILD_NUMBER} || true
            docker run -d --name static-site-${BUILD_NUMBER} -p ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
            sleep 2
            docker ps --filter "name=static-site-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
          """
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

            # optional: start port-forward in background so host port maps to service port 80
            if [ -n "${HOST_PORT}" ]; then
              echo "Starting (background) port-forward: localhost:${HOST_PORT} -> service/static-site-service:80 (ns: ${K8S_NAMESPACE})"

              # Kill previous pid if exists and running
              if [ -f "$WORKSPACE/k8s-portforward.pid" ]; then
                OLDPID=$(cat "$WORKSPACE/k8s-portforward.pid") || true
                if [ -n "$OLDPID" ] && kill -0 $OLDPID >/dev/null 2>&1; then
                  echo "Killing old port-forward pid $OLDPID"
                  kill $OLDPID || true
                fi
              fi

              # Start new background port-forward (nohup allows pipeline to continue)
              nohup kubectl port-forward svc/static-site-service ${HOST_PORT}:80 -n ${K8S_NAMESPACE} >/dev/null 2>&1 &
              PF_PID=$!
              echo $PF_PID > "$WORKSPACE/k8s-portforward.pid"
              echo "Port-forward started (pid: ${PF_PID})"
            fi

            echo "Kubernetes deploy finished."
          '''
        }
      }
    }
  }

  post {
    success {
      echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER} deployed to ${env.K8S_NAMESPACE}"
      echo "If port-forward started, access the app at http://localhost:${env.HOST_PORT}"
    }

    failure {
      echo "Pipeline failed — attempting cleanup and rollback (best-effort). See console for details."
      sh '''
        set +e
        # stop port-forward if it was started
        if [ -f "$WORKSPACE/k8s-portforward.pid" ]; then
          PID=$(cat "$WORKSPACE/k8s-portforward.pid") || true
          if [ -n "$PID" ] && kill -0 $PID >/dev/null 2>&1; then
            echo "Killing port-forward pid $PID"
            kill $PID || true
            rm -f "$WORKSPACE/k8s-portforward.pid"
          fi
        fi

        # attempt rollback if kubectl is configured
        if command -v kubectl >/dev/null 2>&1; then
          kubectl rollout undo deployment/static-site -n ${K8S_NAMESPACE} || true
        fi
      '''
    }
  }
}
