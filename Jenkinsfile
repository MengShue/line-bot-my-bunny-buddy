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
    stage('Create Secrets') {
      steps {
        withCredentials([file(credentialsId: 'linebot-secrets-yaml', variable: 'LINEBOT_SECRET_FILE')]) {
          sh "kubectl -n ${NS} apply -f $LINEBOT_SECRET_FILE"
        }
        // dockerhub-secret still build from from-literal
        sh '''
        kubectl -n ${NS} get secret dockerhub-secret || \
        kubectl -n ${NS} create secret docker-registry dockerhub-secret \
          --docker-username=$DOCKER_USER \
          --docker-password=$DOCKER_PASS \
          --docker-email=$DOCKER_EMAIL
        '''
      }
    }

    stage('Deploy Main Server') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/linebot/deployment.yaml"
        sh "kubectl -n ${NS} apply -f k8s/linebot/service.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
        // Assume PR code would not build docker image, so we need to copy code to pod.
        sh "kubectl -n ${NS} cp . ${getPodName('linebot')}:/code"
        sh "kubectl -n ${NS} exec ${getPodName('linebot')} -- pkill -f 'python -m app.app' || true"
        sh "kubectl -n ${NS} exec ${getPodName('linebot')} -- bash -c 'cd /code && python -m app.app &'"
      }
    }

    stage('Deploy Test Pod') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/PR/deployment.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot-pr --timeout=90s"
      }
    }

    stage('Copy Code') {
      steps {
        script {
          sh "kubectl -n ${NS} cp . ${getPodName('linebot-pr')}:/app"
        }
      }
    }

    stage('Run Tests') {
      steps {
        script {
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && pip install -r requirements.txt && python3 -m unittest discover'"
        }
      }
    }

    stage('Deploy Ingress') {
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
          // 1. 先改 config 檔
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && sed -i \"s|^host: .*|host: ${env.PR_HOST}|\" automation/integration_config.yaml'"
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
      sh "kubectl delete ns ${NS} || true"
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
