pipeline {
    agent any
    
    parameters {
        password(
            name: 'BEVIGIL_API_KEY',
            defaultValue: '',
            description: 'BeVigil API Key'
        )
        password(
            name: 'SUPABASE_URL',
            defaultValue: '',
            description: 'Supabase URL'
        )
        password(
            name: 'SUPABASE_SERVICE_KEY',
            defaultValue: '',
            description: 'Supabase Service Key'
        )
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
        string(
            name: 'LIMIT',
            defaultValue: '',
            description: 'Optional: Maximum number of apps to process'
        )
    }
    
    environment {
        VENV_DIR = 'venv'
        BEVIGIL_API_KEY = "${params.BEVIGIL_API_KEY}"
        SUPABASE_URL = "${params.SUPABASE_URL}"
        SUPABASE_SERVICE_KEY = "${params.SUPABASE_SERVICE_KEY}"
        // Fix Unicode encoding issues on Windows
        PYTHONIOENCODING = 'utf-8'
        PYTHONUTF8 = '1'
    }
    
    stages {
        stage('Setup') {
            steps {
                echo 'Setting up Python environment...'
                script {
                    if (isUnix()) {
                        sh '''
                            if [ ! -d "${VENV_DIR}" ]; then
                                echo "Creating new virtual environment..."
                                python3 -m venv ${VENV_DIR}
                            else
                                echo "Using existing virtual environment..."
                            fi
                            . ${VENV_DIR}/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                        '''
                    } else {
                        bat '''
                            chcp 65001 > nul
                            if not exist "%VENV_DIR%" (
                                echo Creating new virtual environment...
                                python -m venv %VENV_DIR%
                            ) else (
                                echo Using existing virtual environment...
                            )
                            call %VENV_DIR%\\Scripts\\activate.bat
                            pip install --upgrade pip
                            pip install -r requirements.txt
                        '''
                    }
                }
            }
        }
        
        stage('Validate') {
            steps {
                echo 'Validating configuration...'
                script {
                    if (isUnix()) {
                        sh '''
                            . ${VENV_DIR}/bin/activate
                            python3 -c "from src.config import config; missing = config.validate(); print('Config OK' if not missing else f'Missing: {missing}')"
                        '''
                    } else {
                        bat '''
                            chcp 65001 > nul
                            call %VENV_DIR%\\Scripts\\activate.bat
                            python -c "from src.config import config; missing = config.validate(); print('Config OK' if not missing else f'Missing: {missing}')"
                        '''
                    }
                }
            }
        }
        
        stage('Run Enrichment') {
            steps {
                script {
                    def bundleArgs = ''
                    def appNameArg = ''
                    def limitArg = ''
                    
                    // Handle bundle IDs for direct scanning
                    if (params.BUNDLE_IDS?.trim()) {
                        def bundleIds = params.BUNDLE_IDS.split(',')
                        bundleIds.each { bid ->
                            bundleArgs += " -s ${bid.trim()}"
                        }
                        
                        // Add app name if provided and single bundle ID
                        if (params.APP_NAME?.trim() && bundleIds.size() == 1) {
                            appNameArg = " -n '${params.APP_NAME}'"
                        }
                    }
                    
                    if (params.LIMIT?.trim()) {
                        limitArg = " -l ${params.LIMIT}"
                    }
                    
                    if (isUnix()) {
                        sh """
                            . ${VENV_DIR}/bin/activate
                            python3 scripts/run_enrichment.py${bundleArgs}${appNameArg}${limitArg} << EOF
y
EOF
                        """
                    } else {
                        bat """
                            chcp 65001 > nul
                            call %VENV_DIR%\\Scripts\\activate.bat
                            echo y | python scripts/run_enrichment.py${bundleArgs}${appNameArg}${limitArg}
                        """
                    }
                }
            }
        }
        
        stage('Check Status') {
            steps {
                echo 'Checking enrichment status...'
                script {
                    if (isUnix()) {
                        sh '''
                            . ${VENV_DIR}/bin/activate
                            python3 scripts/check_status.py
                        '''
                    } else {
                        bat '''
                            chcp 65001 > nul
                            call %VENV_DIR%\\Scripts\\activate.bat
                            python scripts/check_status.py
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            node('') {
                echo 'Cleaning up...'
                cleanWs(cleanWhenNotBuilt: false,
                        deleteDirs: true,
                        disableDeferredWipeout: true,
                        notFailBuild: true)
            }
        }
        success {
            echo 'Enrichment completed successfully!'
        }
        failure {
            echo 'Enrichment failed. Check the logs for details.'
        }
    }
}
