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

    stage('Deploy Test Pod') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/PR/deployment.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
      }
    }

    stage('Copy Code') {
      steps {
        script {
          def podName = sh(
            script: "kubectl -n ${NS} get pod -l app=linebot -o jsonpath='{.items[0].metadata.name}'",
            returnStdout: true
          ).trim()
          sh "kubectl -n ${NS} cp . ${podName}:/app"
        }
      }
    }

    stage('Run Tests') {
      steps {
        script {
          def podName = sh(
            script: "kubectl -n ${NS} get pod -l app=linebot -o jsonpath='{.items[0].metadata.name}'",
            returnStdout: true
          ).trim()
          sh "kubectl -n ${NS} exec ${getPodName()} -- bash -c 'cd /app && pip install -r requirements.txt && python3 -m unittest discover'"
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

def getPodName() {
  def podName = sh(
    script: "kubectl -n ${NS} get pod -l app=linebot -o jsonpath='{.items[0].metadata.name}'",
    returnStdout: true
  ).trim()
  return podName
}
