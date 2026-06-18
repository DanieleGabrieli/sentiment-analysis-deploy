pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '5'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "Build #${env.BUILD_NUMBER} — commit: ${env.GIT_COMMIT}"
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip --quiet
                    pip install -r app/requirements.txt pytest httpx --quiet
                '''
            }
        }

        stage('Unit & Integration tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v
                '''
            }
        }

        stage('Build Docker image') {
            steps {
                sh "docker build -t sentiment-analysis-api:${env.BUILD_NUMBER} -t sentiment-analysis-api:latest ."
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker stop sentiment-api || true
                    docker rm sentiment-api || true
                    docker run -d \
                        --name sentiment-api \
                        -p 8000:8000 \
                        --restart unless-stopped \
                        sentiment-analysis-api:latest
                '''
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    sleep 10
                    curl -sf http://localhost:8000/health
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline completata con successo — build #${env.BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline FALLITA — build #${env.BUILD_NUMBER}"
        }
    }
}
