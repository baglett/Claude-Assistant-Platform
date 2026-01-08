// =============================================================================
// Claude Assistant Platform - Jenkinsfile
// =============================================================================
// CI/CD Pipeline for deploying Backend, Frontend, Telegram MCP,
// Google Calendar MCP, and Gmail MCP servers
// =============================================================================

pipeline {
    agent any

    environment {
        // Docker Registry Configuration
        DOCKER_REGISTRY = '192.168.50.35:5000'
        DOCKER_HOST = 'unix:///var/run/docker.sock'

        // =====================================================================
        // Credentials (injected from Jenkins credential store)
        // =====================================================================
        // Configure in: Jenkins -> Manage Jenkins -> Credentials -> System
        //               -> Global credentials (unrestricted) -> Add Credentials
        // Use Kind: "Secret text" for each credential
        // =====================================================================
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        TELEGRAM_ALLOWED_USER_IDS = credentials('telegram-allowed-user-ids')
        POSTGRES_USER = credentials('postgres-db-user')
        POSTGRES_PASSWORD = credentials('postgres-db-password')
        GOOGLE_CALENDAR_CLIENT_ID = credentials('google-calendar-client-id')
        GOOGLE_CALENDAR_CLIENT_SECRET = credentials('google-calendar-client-secret')
        GMAIL_CLIENT_ID = credentials('gmail-client-id')
        GMAIL_CLIENT_SECRET = credentials('gmail-client-secret')

        // Image Names
        BACKEND_IMAGE_NAME = 'claude-assistant-backend'
        FRONTEND_IMAGE_NAME = 'claude-assistant-frontend'
        TELEGRAM_MCP_IMAGE_NAME = 'claude-assistant-telegram-mcp'
        GOOGLE_CALENDAR_MCP_IMAGE_NAME = 'claude-assistant-google-calendar-mcp'
        GMAIL_MCP_IMAGE_NAME = 'claude-assistant-gmail-mcp'

        // Container Names
        BACKEND_CONTAINER = 'claude-assistant-backend'
        FRONTEND_CONTAINER = 'claude-assistant-frontend'
        TELEGRAM_MCP_CONTAINER = 'claude-assistant-telegram-mcp'
        GOOGLE_CALENDAR_MCP_CONTAINER = 'claude-assistant-google-calendar-mcp'
        GMAIL_MCP_CONTAINER = 'claude-assistant-gmail-mcp'

        // Network Name
        DOCKER_NETWORK = 'claude-assistant-network'

        // Port Configuration (external:internal)
        BACKEND_PORT = '8000'
        FRONTEND_PORT = '3000'
        TELEGRAM_MCP_PORT = '8081'
        GOOGLE_CALENDAR_MCP_PORT = '8084'
        GMAIL_MCP_PORT = '8085'

        // Database Configuration (uses existing PostgreSQL on Orange Pi)
        POSTGRES_HOST = '192.168.50.35'
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
                    env.GOOGLE_CALENDAR_MCP_IMAGE = "${DOCKER_REGISTRY}/${GOOGLE_CALENDAR_MCP_IMAGE_NAME}:${env.IMAGE_VERSION}"
                    env.GMAIL_MCP_IMAGE = "${DOCKER_REGISTRY}/${GMAIL_MCP_IMAGE_NAME}:${env.IMAGE_VERSION}"

                    echo "Deploying version: ${env.IMAGE_VERSION}"
                    echo "Backend Image: ${env.BACKEND_IMAGE}"
                    echo "Frontend Image: ${env.FRONTEND_IMAGE}"
                    echo "Telegram MCP Image: ${env.TELEGRAM_MCP_IMAGE}"
                    echo "Google Calendar MCP Image: ${env.GOOGLE_CALENDAR_MCP_IMAGE}"
                    echo "Gmail MCP Image: ${env.GMAIL_MCP_IMAGE}"
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
                stage('Build Google Calendar MCP') {
                    steps {
                        script {
                            sh """
                            export DOCKER_HOST=${DOCKER_HOST}
                            docker build --platform linux/arm64/v8 \
                                -t ${env.GOOGLE_CALENDAR_MCP_IMAGE} \
                                -f ./MCPS/google-calendar/Dockerfile \
                                ./MCPS/google-calendar
                            """
                        }
                    }
                }
                stage('Build Gmail MCP') {
                    steps {
                        script {
                            sh """
                            export DOCKER_HOST=${DOCKER_HOST}
                            docker build --platform linux/arm64/v8 \
                                -t ${env.GMAIL_MCP_IMAGE} \
                                -f ./MCPS/gmail/Dockerfile \
                                ./MCPS/gmail
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
                stage('Push Google Calendar MCP') {
                    steps {
                        script {
                            sh "docker push ${env.GOOGLE_CALENDAR_MCP_IMAGE}"
                        }
                    }
                }
                stage('Push Gmail MCP') {
                    steps {
                        script {
                            sh "docker push ${env.GMAIL_MCP_IMAGE}"
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

                    docker ps -f name=${GOOGLE_CALENDAR_MCP_CONTAINER} -q | xargs --no-run-if-empty docker container stop
                    docker container ls -a -f name=${GOOGLE_CALENDAR_MCP_CONTAINER} -q | xargs -r docker container rm

                    docker ps -f name=${GMAIL_MCP_CONTAINER} -q | xargs --no-run-if-empty docker container stop
                    docker container ls -a -f name=${GMAIL_MCP_CONTAINER} -q | xargs -r docker container rm
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
        // Stage: Start Google Calendar MCP Container
        // ---------------------------------------------------------------------
        stage('Start Google Calendar MCP') {
            steps {
                script {
                    sh """
                    docker run -d \
                        --name ${GOOGLE_CALENDAR_MCP_CONTAINER} \
                        --network ${DOCKER_NETWORK} \
                        --restart unless-stopped \
                        -p ${GOOGLE_CALENDAR_MCP_PORT}:8084 \
                        -v google-calendar-data:/app/data \
                        -e GOOGLE_CALENDAR_CLIENT_ID=\${GOOGLE_CALENDAR_CLIENT_ID} \
                        -e GOOGLE_CALENDAR_CLIENT_SECRET=\${GOOGLE_CALENDAR_CLIENT_SECRET} \
                        -e GOOGLE_CALENDAR_TOKEN_PATH=/app/data/token.json \
                        -e GOOGLE_CALENDAR_DEFAULT_TIMEZONE=America/New_York \
                        -e GOOGLE_CALENDAR_MCP_HOST=0.0.0.0 \
                        -e GOOGLE_CALENDAR_MCP_PORT=8084 \
                        ${env.GOOGLE_CALENDAR_MCP_IMAGE}
                    """

                    // Wait for health check
                    sh """
                    echo "Waiting for Google Calendar MCP to be healthy..."
                    sleep 10
                    curl -f http://localhost:${GOOGLE_CALENDAR_MCP_PORT}/health || echo "Health check pending..."
                    """
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage: Start Gmail MCP Container
        // ---------------------------------------------------------------------
        stage('Start Gmail MCP') {
            steps {
                script {
                    sh """
                    docker run -d \
                        --name ${GMAIL_MCP_CONTAINER} \
                        --network ${DOCKER_NETWORK} \
                        --restart unless-stopped \
                        -p ${GMAIL_MCP_PORT}:8085 \
                        -v gmail-data:/app/data \
                        -e GMAIL_CLIENT_ID=\${GMAIL_CLIENT_ID} \
                        -e GMAIL_CLIENT_SECRET=\${GMAIL_CLIENT_SECRET} \
                        -e GMAIL_TOKEN_PATH=/app/data/token.json \
                        -e GMAIL_MCP_HOST=0.0.0.0 \
                        -e GMAIL_MCP_PORT=8085 \
                        ${env.GMAIL_MCP_IMAGE}
                    """

                    // Wait for health check
                    sh """
                    echo "Waiting for Gmail MCP to be healthy..."
                    sleep 10
                    curl -f http://localhost:${GMAIL_MCP_PORT}/health || echo "Health check pending..."
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
                        -e ALLOWED_HOSTS=localhost,127.0.0.1,192.168.50.35 \
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
                        -e GOOGLE_CALENDAR_MCP_HOST=${GOOGLE_CALENDAR_MCP_CONTAINER} \
                        -e GOOGLE_CALENDAR_MCP_PORT=8084 \
                        -e GMAIL_MCP_HOST=${GMAIL_MCP_CONTAINER} \
                        -e GMAIL_MCP_PORT=8085 \
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
                        -e NEXT_PUBLIC_API_URL=http://192.168.50.35:${BACKEND_PORT} \
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
                    echo "Backend:             http://192.168.50.35:${BACKEND_PORT}"
                    echo "Frontend:            http://192.168.50.35:${FRONTEND_PORT}"
                    echo "Telegram MCP:        http://192.168.50.35:${TELEGRAM_MCP_PORT}"
                    echo "Google Calendar MCP: http://192.168.50.35:${GOOGLE_CALENDAR_MCP_PORT}"
                    echo "Gmail MCP:           http://192.168.50.35:${GMAIL_MCP_PORT}"
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
