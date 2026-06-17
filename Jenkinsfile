pipeline {
    agent any

    environment {
        IMAGE_NAME    = "sentiment-analysis-api"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        REGISTRY      = credentials('docker-registry-url')   // set in Jenkins credentials
        REGISTRY_CRED = credentials('docker-registry-creds') // username:password
        CONTAINER_NAME = "sentiment-api"
        APP_PORT      = "8000"
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        // ------------------------------------------------------------------ //
        stage('Checkout') {
            steps {
                checkout scm
                echo "Building commit: ${env.GIT_COMMIT}"
            }
        }

        // ------------------------------------------------------------------ //
        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r app/requirements.txt
                    pip install pytest httpx
                '''
            }
        }

        // ------------------------------------------------------------------ //
        stage('Unit & Integration tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v --junitxml=reports/test-results.xml
                '''
            }
            post {
                always {
                    junit 'reports/test-results.xml'
                }
            }
        }

        // ------------------------------------------------------------------ //
        stage('Build Docker image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest ."
            }
        }

        // ------------------------------------------------------------------ //
        stage('Push to registry') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    echo \${REGISTRY_CRED_PSW} | docker login \${REGISTRY} -u \${REGISTRY_CRED_USR} --password-stdin
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} \${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:latest     \${REGISTRY}/${IMAGE_NAME}:latest
                    docker push \${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                    docker push \${REGISTRY}/${IMAGE_NAME}:latest
                """
            }
        }

        // ------------------------------------------------------------------ //
        stage('Deploy (staging)') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    docker stop ${CONTAINER_NAME} || true
                    docker rm   ${CONTAINER_NAME} || true
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        -p ${APP_PORT}:8000 \\
                        --restart unless-stopped \\
                        ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }

        // ------------------------------------------------------------------ //
        stage('Smoke test') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    sleep 10
                    curl -sf http://localhost:${APP_PORT}/health | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['status'] == 'healthy', f'Health check failed: {data}'
print('Smoke test passed:', data)
"
                """
            }
        }
    }

    // ---------------------------------------------------------------------- //
    post {
        success {
            echo "Pipeline completed successfully — build #${env.BUILD_NUMBER}"
            // Uncomment if you have email-ext or Slack plugin configured:
            // emailext subject: "SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            //          body:    "All stages passed.",
            //          to:      "team@example.com"
        }
        failure {
            echo "Pipeline FAILED — build #${env.BUILD_NUMBER}"
            // emailext subject: "FAILURE: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            //          body:    "Check Jenkins for details: ${env.BUILD_URL}",
            //          to:      "team@example.com"
        }
        always {
            cleanWs()
        }
    }
}
