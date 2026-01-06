// =============================================================================
// Claude Assistant Platform - Jenkinsfile
// =============================================================================
// CI/CD Pipeline for deploying Backend, Frontend, and Telegram MCP Server
// =============================================================================

pipeline {
    agent any

    environment {
        // Docker Registry Configuration
        DOCKER_REGISTRY = '192.168.50.35:5000'
        DOCKER_HOST = 'unix:///var/run/docker.sock'

        // Image Names
        BACKEND_IMAGE_NAME = 'claude-assistant-backend'
        FRONTEND_IMAGE_NAME = 'claude-assistant-frontend'
        TELEGRAM_MCP_IMAGE_NAME = 'claude-assistant-telegram-mcp'

        // Container Names
        BACKEND_CONTAINER = 'claude-assistant-backend'
        FRONTEND_CONTAINER = 'claude-assistant-frontend'
        TELEGRAM_MCP_CONTAINER = 'claude-assistant-telegram-mcp'

        // Network Name
        DOCKER_NETWORK = 'claude-assistant-network'

        // Port Configuration (external:internal)
        BACKEND_PORT = '8000'
        FRONTEND_PORT = '3000'
        TELEGRAM_MCP_PORT = '8081'

        // Database Configuration (uses existing PostgreSQL on Orange Pi)
        POSTGRES_HOST = '192.168.86.80'
        POSTGRES_PORT = '5432'
    }

    stages {
        // ---------------------------------------------------------------------
        // Stage: Prepare
        // ---------------------------------------------------------------------
        stage('Prepare') {
            steps {
                script {
                    // Read version from file or use git commit hash
                    if (fileExists('version.txt')) {
                        env.IMAGE_VERSION = readFile('version.txt').trim()
                    } else {
                        env.IMAGE_VERSION = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    }

                    // Set full image paths
                    env.BACKEND_IMAGE = "${DOCKER_REGISTRY}/${BACKEND_IMAGE_NAME}:${env.IMAGE_VERSION}"
                    env.FRONTEND_IMAGE = "${DOCKER_REGISTRY}/${FRONTEND_IMAGE_NAME}:${env.IMAGE_VERSION}"
                    env.TELEGRAM_MCP_IMAGE = "${DOCKER_REGISTRY}/${TELEGRAM_MCP_IMAGE_NAME}:${env.IMAGE_VERSION}"

                    echo "Deploying version: ${env.IMAGE_VERSION}"
                    echo "Backend Image: ${env.BACKEND_IMAGE}"
                    echo "Frontend Image: ${env.FRONTEND_IMAGE}"
                    echo "Telegram MCP Image: ${env.TELEGRAM_MCP_IMAGE}"
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Verify Docker CLI
        // ---------------------------------------------------------------------
        stage('Verify Docker CLI') {
            steps {
                script {
                    sh 'docker --version'
                    sh 'docker info'
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Create Docker Network
        // ---------------------------------------------------------------------
        stage('Create Docker Network') {
            steps {
                script {
                    // Create network if it doesn't exist
                    sh """
                    docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1 || \
                    docker network create ${DOCKER_NETWORK}
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Build Docker Images
        // ---------------------------------------------------------------------
        stage('Build Docker Images') {
            parallel {
                stage('Build Backend') {
                    steps {
                        script {
                            sh """
                            export DOCKER_HOST=${DOCKER_HOST}
                            docker build --platform linux/arm64/v8 \
                                -t ${env.BACKEND_IMAGE} \
                                -f ./Backend/Dockerfile \
                                ./Backend
                            """
                        }
                    }
                }
                stage('Build Frontend') {
                    steps {
                        script {
                            sh """
                            export DOCKER_HOST=${DOCKER_HOST}
                            docker build --platform linux/arm64/v8 \
                                -t ${env.FRONTEND_IMAGE} \
                                -f ./Frontend/Dockerfile \
                                ./Frontend
                            """
                        }
                    }
                }
                stage('Build Telegram MCP') {
                    steps {
                        script {
                            sh """
                            export DOCKER_HOST=${DOCKER_HOST}
                            docker build --platform linux/arm64/v8 \
                                -t ${env.TELEGRAM_MCP_IMAGE} \
                                -f ./MCPS/Telegram/Dockerfile \
                                ./MCPS/Telegram
                            """
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Push Docker Images
        // ---------------------------------------------------------------------
        stage('Push Docker Images') {
            parallel {
                stage('Push Backend') {
                    steps {
                        script {
                            sh "docker push ${env.BACKEND_IMAGE}"
                        }
                    }
                }
                stage('Push Frontend') {
                    steps {
                        script {
                            sh "docker push ${env.FRONTEND_IMAGE}"
                        }
                    }
                }
                stage('Push Telegram MCP') {
                    steps {
                        script {
                            sh "docker push ${env.TELEGRAM_MCP_IMAGE}"
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Stop and Remove Existing Containers
        // ---------------------------------------------------------------------
        stage('Stop and Remove Containers') {
            steps {
                script {
                    // Stop and remove containers if they exist
                    sh """
                    docker ps -f name=${BACKEND_CONTAINER} -q | xargs --no-run-if-empty docker container stop
                    docker container ls -a -f name=${BACKEND_CONTAINER} -q | xargs -r docker container rm

                    docker ps -f name=${FRONTEND_CONTAINER} -q | xargs --no-run-if-empty docker container stop
                    docker container ls -a -f name=${FRONTEND_CONTAINER} -q | xargs -r docker container rm

                    docker ps -f name=${TELEGRAM_MCP_CONTAINER} -q | xargs --no-run-if-empty docker container stop
                    docker container ls -a -f name=${TELEGRAM_MCP_CONTAINER} -q | xargs -r docker container rm
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Start Telegram MCP Container (must start first)
        // ---------------------------------------------------------------------
        stage('Start Telegram MCP') {
            steps {
                script {
                    sh """
                    docker run -d \
                        --name ${TELEGRAM_MCP_CONTAINER} \
                        --network ${DOCKER_NETWORK} \
                        --restart unless-stopped \
                        -p ${TELEGRAM_MCP_PORT}:8080 \
                        -e TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN} \
                        ${env.TELEGRAM_MCP_IMAGE}
                    """

                    // Wait for health check
                    sh """
                    echo "Waiting for Telegram MCP to be healthy..."
                    sleep 10
                    curl -f http://localhost:${TELEGRAM_MCP_PORT}/health || echo "Health check pending..."
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Start Backend Container
        // ---------------------------------------------------------------------
        stage('Start Backend') {
            steps {
                script {
                    sh """
                    docker run -d \
                        --name ${BACKEND_CONTAINER} \
                        --network ${DOCKER_NETWORK} \
                        --restart unless-stopped \
                        -p ${BACKEND_PORT}:8000 \
                        -e APP_NAME=claude-assistant-platform \
                        -e APP_ENV=production \
                        -e DEBUG=false \
                        -e LOG_LEVEL=INFO \
                        -e API_HOST=0.0.0.0 \
                        -e API_PORT=8000 \
                        -e ALLOWED_HOSTS=localhost,127.0.0.1,192.168.86.80 \
                        -e ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY} \
                        -e CLAUDE_MODEL=\${CLAUDE_MODEL:-claude-sonnet-4-20250514} \
                        -e POSTGRES_DB=\${POSTGRES_DB:-claude_assistant_platform} \
                        -e POSTGRES_USER=\${POSTGRES_USER:-postgres} \
                        -e POSTGRES_PASSWORD=\${POSTGRES_PASSWORD} \
                        -e POSTGRES_HOST=${POSTGRES_HOST} \
                        -e POSTGRES_PORT=${POSTGRES_PORT} \
                        -e TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN} \
                        -e TELEGRAM_ALLOWED_USER_IDS=\${TELEGRAM_ALLOWED_USER_IDS} \
                        -e TELEGRAM_POLLING_TIMEOUT=30 \
                        -e TELEGRAM_ENABLED=true \
                        -e TELEGRAM_MCP_HOST=${TELEGRAM_MCP_CONTAINER} \
                        -e TELEGRAM_MCP_PORT=8080 \
                        -e TODO_EXECUTOR_ENABLED=true \
                        -e TODO_EXECUTOR_INTERVAL=30 \
                        -e TODO_EXECUTOR_BATCH_SIZE=5 \
                        ${env.BACKEND_IMAGE}
                    """

                    // Wait for health check
                    sh """
                    echo "Waiting for Backend to be healthy..."
                    sleep 15
                    curl -f http://localhost:${BACKEND_PORT}/health || echo "Health check pending..."
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Start Frontend Container
        // ---------------------------------------------------------------------
        stage('Start Frontend') {
            steps {
                script {
                    sh """
                    docker run -d \
                        --name ${FRONTEND_CONTAINER} \
                        --network ${DOCKER_NETWORK} \
                        --restart unless-stopped \
                        -p ${FRONTEND_PORT}:3000 \
                        -e NEXT_PUBLIC_API_URL=http://192.168.86.80:${BACKEND_PORT} \
                        -e NODE_ENV=production \
                        ${env.FRONTEND_IMAGE}
                    """

                    // Wait for health check
                    sh """
                    echo "Waiting for Frontend to be healthy..."
                    sleep 10
                    curl -f http://localhost:${FRONTEND_PORT}/ || echo "Health check pending..."
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Verify Deployment
        // ---------------------------------------------------------------------
        stage('Verify Deployment') {
            steps {
                script {
                    sh """
                    echo "============================================"
                    echo "Deployment Complete!"
                    echo "============================================"
                    echo "Backend:      http://192.168.86.80:${BACKEND_PORT}"
                    echo "Frontend:     http://192.168.86.80:${FRONTEND_PORT}"
                    echo "Telegram MCP: http://192.168.86.80:${TELEGRAM_MCP_PORT}"
                    echo "============================================"
                    echo ""
                    echo "Running Containers:"
                    docker ps --filter "name=claude-assistant"
                    echo ""
                    echo "Network:"
                    docker network inspect ${DOCKER_NETWORK} --format '{{range .Containers}}{{.Name}} {{end}}'
                    """
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Post Actions
    // -------------------------------------------------------------------------
    post {
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
            // Optionally clean up on failure
            script {
                sh """
                echo "Cleaning up failed deployment..."
                docker ps -f name=claude-assistant -q | xargs --no-run-if-empty docker container stop || true
                """
            }
        }
        always {
            // Clean up old images to save space
            sh """
            echo "Cleaning up unused Docker images..."
            docker image prune -f || true
            """
        }
    }
}
