pipeline {
  agent {
    kubernetes {
      yamlFile 'jenkins/pod.yaml'
      label 'kubectl-agent'
      defaultContainer 'kubectl'
    }
  }
  environment {
    NS = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}"
  }
  stages {
    stage('Create Namespace') {
      steps {
        sh "kubectl create ns ${NS}"
      }
    }
    stage('Apply RBAC') {
      steps {
        withCredentials([
          file(credentialsId: 'k8s-role', variable: 'K8S_ROLE_FILE'),
          file(credentialsId: 'k8s-role-binding', variable: 'K8S_ROLE_BINDING_FILE')
        ]) {
          sh '''
            envsubst < $K8S_ROLE_FILE > /tmp/k8s-role.yaml
            envsubst < $K8S_ROLE_BINDING_FILE > /tmp/k8s-role-binding.yaml
            kubectl apply -f /tmp/k8s-role.yaml
            kubectl apply -f /tmp/k8s-role-binding.yaml
          '''
        }
      }
    }
    stage('Create Secrets') {
      steps {
        withCredentials([file(credentialsId: 'linebot-secrets-yaml', variable: 'LINEBOT_SECRET_FILE')]) {
          sh "kubectl -n ${NS} apply -f $LINEBOT_SECRET_FILE"
        }
        // dockerhub-secret still build from from-literal
        withCredentials([usernamePassword(credentialsId: 'dockerhub-credential', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            kubectl -n ${NS} get secret dockerhub-secret || \
            kubectl -n ${NS} create secret docker-registry dockerhub-secret \
              --docker-server=https://index.docker.io/v1/ \
              --docker-username=$DOCKER_USER \
              --docker-password=$DOCKER_PASS
          '''
        }
      }
    }

    stage('Create PVC') {
      steps {
        sh '''
        envsubst < k8s/PR/pvc.yaml | kubectl apply -f -
        '''
      }
    }

    stage('Deploy Main Server') {
      steps {
        sh "export NS=${NS} && envsubst < k8s/linebot/deployment.yaml | kubectl -n ${NS} apply -f -"
        sh "kubectl -n ${NS} apply -f k8s/linebot/service.yaml"
        // call healthy check to make sure the pod is ready
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
        sh "kubectl -n ${NS} cp . ${getPodName('linebot')}:/pr"
        // delete the pod and wait for the new pod to be ready, since desired to use PR code, not required to build image.
        sh "kubectl -n ${NS} delete pod ${getPodName('linebot')}"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
      }
    }

    stage('Deploy Test Pod') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/PR/deployment.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot-pr --timeout=90s"
      }
    }

    stage('Copy Code To Test Pod') {
      steps {
        script {
          sh "kubectl -n ${NS} cp . ${getPodName('linebot-pr')}:/app"
        }
      }
    }

    stage('Run Unit Tests') {
      steps {
        script {
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && pip install -r requirements.txt && python3 -m unittest discover'"
        }
      }
    }

    stage('Deploy Ingress For Integration Test') {
      steps {
        script {
          env.PR_HOST = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}.minibot.com.tw"
          sh "export NS=${NS} PR_HOST=${PR_HOST} && envsubst < k8s/PR/ingress.yaml | kubectl -n ${NS} apply -f -"
        }
      }
    }

    stage('Run Integration Tests') {
      steps {
        script {
          env.PR_HOST = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}.minibot.com.tw"
          // 1. 先改 config 檔: local test port is 5500, http port is 80
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && sed -i \"s|^host: .*|host: ${env.PR_HOST}|\" automation/integration_config.yaml'"
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && sed -i \"s|^port: .*|port: 80|\" automation/integration_config.yaml'"
          // 2. 等待 Ingress 生效
          sh "sleep 10"
          // 3. 執行 integration test
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && pip install -r requirements.txt && pytest automation/test_callback_integration.py'"
        }
      }
    }
  }

  post {
    always {
      // delete all resources first to avoid take too much time to delete namespace
      sh "kubectl -n ${NS} delete deployment --all || true"
      sh "kubectl -n ${NS} delete pod --all || true"
      sh "kubectl -n ${NS} delete svc --all || true"
      sh "kubectl -n ${NS} delete pvc --all || true"
      // delete namespace
      sh "kubectl delete ns ${NS} --wait=false || true"
    }
  }
}

def getPodName(label) {
  def podName = sh(
    script: "kubectl -n ${NS} get pod -l app=${label} -o jsonpath='{.items[0].metadata.name}'",
    returnStdout: true
  ).trim()
  return podName
}
