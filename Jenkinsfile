pipeline {
    agent any
    
    parameters {
        string(
            name: 'BUNDLE_IDS',
            defaultValue: '',
            description: 'Comma-separated list of Android bundle IDs to scan (e.g., com.whatsapp,com.facebook.katana)'
        )
        string(
            name: 'APP_NAME',
            defaultValue: '',
            description: 'Optional: App name (only works when scanning a single bundle ID)'
        )
        booleanParam(
            name: 'INCLUDE_FAILED',
            defaultValue: false,
            description: 'Include previously failed apps for retry'
        )
        string(
            name: 'LIMIT',
            defaultValue: '',
            description: 'Optional: Maximum number of apps to process'
        )
    }
    
    environment {
        // These should be configured in Jenkins credentials
        BEVIGIL_API_KEY = credentials('bevigil-api-key')
        SUPABASE_URL = credentials('supabase-url')
        SUPABASE_SERVICE_KEY = credentials('supabase-service-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                echo 'Setting up Python environment...'
                sh '''
                    python3 -m venv venv || true
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Validate') {
            steps {
                echo 'Validating configuration...'
                sh '''
                    . venv/bin/activate
                    python3 -c "from src.config import config; missing = config.validate(); print('Config OK' if not missing else f'Missing: {missing}')"
                '''
            }
        }
        
        stage('Run Enrichment') {
            steps {
                script {
                    def cmd = '. venv/bin/activate && python3 scripts/run_enrichment.py'
                    
                    // Handle bundle IDs for direct scanning
                    if (params.BUNDLE_IDS?.trim()) {
                        def bundleIds = params.BUNDLE_IDS.split(',')
                        bundleIds.each { bid ->
                            cmd += " -s ${bid.trim()}"
                        }
                        
                        // Add app name if provided and single bundle ID
                        if (params.APP_NAME?.trim() && bundleIds.size() == 1) {
                            cmd += " -n '${params.APP_NAME}'"
                        }
                    }
                    
                    // Add optional flags
                    if (params.INCLUDE_FAILED) {
                        cmd += ' -f'
                    }
                    
                    if (params.LIMIT?.trim()) {
                        cmd += " -l ${params.LIMIT}"
                    }
                    
                    // Auto-confirm the prompt
                    sh """
                        ${cmd} << EOF
y
EOF
                    """
                }
            }
        }
        
        stage('Check Status') {
            steps {
                echo 'Checking enrichment status...'
                sh '''
                    . venv/bin/activate
                    python3 scripts/check_status.py
                '''
            }
        }
    }
    
    post {
        always {
            echo 'Cleaning up...'
            cleanWs(cleanWhenNotBuilt: false,
                    deleteDirs: true,
                    disableDeferredWipeout: true,
                    notFailBuild: true)
        }
        success {
            echo 'Enrichment completed successfully!'
        }
        failure {
            echo 'Enrichment failed. Check the logs for details.'
        }
    }
}
