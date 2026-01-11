---
paths:
  - "Jenkinsfile"
  - "**/Jenkinsfile"
---

# Jenkins CI/CD Patterns

## Pipeline Structure

```groovy
pipeline {
    agent any

    environment {
        REGISTRY = 'your-registry.local:5000'
        APP_NAME = 'claude-assistant'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Images') {
            parallel {
                stage('Backend') {
                    steps {
                        script {
                            docker.build("${REGISTRY}/${APP_NAME}-backend:${BUILD_NUMBER}", "./Backend")
                        }
                    }
                }
                stage('Frontend') {
                    steps {
                        script {
                            docker.build("${REGISTRY}/${APP_NAME}-frontend:${BUILD_NUMBER}", "./Frontend")
                        }
                    }
                }
            }
        }

        stage('Push Images') {
            parallel {
                stage('Push Backend') {
                    steps {
                        script {
                            docker.image("${REGISTRY}/${APP_NAME}-backend:${BUILD_NUMBER}").push()
                            docker.image("${REGISTRY}/${APP_NAME}-backend:${BUILD_NUMBER}").push('latest')
                        }
                    }
                }
                stage('Push Frontend') {
                    steps {
                        script {
                            docker.image("${REGISTRY}/${APP_NAME}-frontend:${BUILD_NUMBER}").push()
                            docker.image("${REGISTRY}/${APP_NAME}-frontend:${BUILD_NUMBER}").push('latest')
                        }
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                sshagent(['deploy-key']) {
                    sh '''
                        ssh user@target-host "cd /opt/app && docker-compose pull && docker-compose up -d"
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        failure {
            // Notification on failure
        }
    }
}
```

## Credential Management

Use Jenkins credentials store, never hardcode:

```groovy
pipeline {
    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        GITHUB_TOKEN = credentials('github-token')
    }

    stages {
        stage('Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                    usernamePassword(
                        credentialsId: 'registry-creds',
                        usernameVariable: 'REG_USER',
                        passwordVariable: 'REG_PASS'
                    )
                ]) {
                    sh 'docker login ${REGISTRY} -u ${REG_USER} -p ${REG_PASS}'
                }
            }
        }
    }
}
```

## Required Credentials

| Credential ID | Type | Purpose |
|--------------|------|---------|
| `anthropic-api-key` | Secret text | Claude API access |
| `telegram-bot-token` | Secret text | Telegram bot |
| `github-token` | Secret text | GitHub API access |
| `motion-api-key` | Secret text | Motion API access |
| `db-password` | Secret text | Database password |
| `deploy-key` | SSH key | Deployment server access |

## Parallel Stages

Use parallel blocks for independent operations:

```groovy
stage('Build MCP Images') {
    parallel {
        stage('Telegram MCP') {
            steps {
                script {
                    docker.build("${REGISTRY}/telegram-mcp:${BUILD_NUMBER}", "./MCPS/telegram")
                }
            }
        }
        stage('GitHub MCP') {
            steps {
                script {
                    docker.build("${REGISTRY}/github-mcp:${BUILD_NUMBER}", "./MCPS/github")
                }
            }
        }
        stage('Motion MCP') {
            steps {
                script {
                    docker.build("${REGISTRY}/motion-mcp:${BUILD_NUMBER}", "./MCPS/motion")
                }
            }
        }
    }
}
```

## Deployment Steps

```groovy
stage('Deploy to Production') {
    when {
        branch 'main'
    }
    steps {
        script {
            // Stop existing containers
            sh '''
                ssh user@target-host "
                    cd /opt/app &&
                    docker-compose down --remove-orphans
                "
            '''

            // Pull new images
            sh '''
                ssh user@target-host "
                    cd /opt/app &&
                    docker-compose pull
                "
            '''

            // Start services
            sh '''
                ssh user@target-host "
                    cd /opt/app &&
                    docker-compose up -d
                "
            '''

            // Verify health
            sh '''
                ssh user@target-host "
                    sleep 30 &&
                    curl -f http://localhost:8000/health
                "
            '''
        }
    }
}
```

## Post-Build Actions

```groovy
post {
    always {
        // Clean up workspace
        cleanWs()

        // Clean up Docker images
        sh 'docker image prune -f'
    }

    success {
        echo 'Build and deployment successful!'
    }

    failure {
        echo 'Build or deployment failed!'
        // Add notification here (email, Slack, etc.)
    }
}
```

## Branch-Based Deployment

```groovy
stage('Deploy') {
    when {
        anyOf {
            branch 'main'
            branch 'develop'
        }
    }
    steps {
        script {
            def targetHost = env.BRANCH_NAME == 'main' ? 'prod-host' : 'staging-host'
            sh "ssh user@${targetHost} 'docker-compose up -d'"
        }
    }
}
```

## Key Rules

1. **Credentials in Jenkins** - Never in Jenkinsfile
2. **Parallel stages** - For independent build steps
3. **Branch conditions** - Deploy main to prod only
4. **Health checks** - Verify after deployment
5. **Clean up** - Remove old images and workspaces
6. **Tagging** - Use build number and 'latest' tags
