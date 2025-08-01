#!/usr/bin/env python3
"""
Deployment script for the AWS Semantic Concept Pipeline
"""

import os
import sys
import json
import subprocess
import zipfile
import shutil
from pathlib import Path
import boto3
import argparse

class AWSSemanticPipelineDeployer:
    """Deployer for the AWS Semantic Concept Pipeline"""
    
    def __init__(self, region='us-east-1'):
        self.region = region
        self.project_name = 'pelapela-semantic'
        self.lambda_dir = Path(__file__).parent / 'lambda'
        self.infrastructure_dir = Path(__file__).parent / 'infrastructure'
        
        # AWS clients
        self.s3 = boto3.client('s3', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
    def deploy(self, environment='dev'):
        """Deploy the entire pipeline"""
        print(f"🚀 Deploying AWS Semantic Pipeline to {environment} environment...")
        
        try:
            # 1. Deploy infrastructure
            print("📦 Deploying infrastructure...")
            self.deploy_infrastructure(environment)
            
            # 2. Build and deploy Lambda functions
            print("🔧 Building Lambda functions...")
            self.build_lambda_functions()
            
            # 3. Upload Lambda functions
            print("📤 Uploading Lambda functions...")
            self.upload_lambda_functions()
            
            # 4. Test deployment
            print("🧪 Testing deployment...")
            self.test_deployment()
            
            print("✅ Deployment completed successfully!")
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            sys.exit(1)
    
    def deploy_infrastructure(self, environment):
        """Deploy infrastructure using Terraform"""
        os.chdir(self.infrastructure_dir)
        
        # Initialize Terraform
        subprocess.run(['terraform', 'init'], check=True)
        
        # Apply Terraform configuration
        subprocess.run([
            'terraform', 'apply',
            '-var', f'environment={environment}',
            '-auto-approve'
        ], check=True)
        
        # Get outputs
        result = subprocess.run(['terraform', 'output', '-json'], 
                              capture_output=True, text=True, check=True)
        outputs = json.loads(result.stdout)
        
        # Store outputs for Lambda deployment
        self.opensearch_endpoint = outputs['opensearch_endpoint']['value']
        self.s3_bucket = outputs['s3_bucket_name']['value']
        self.api_gateway_url = outputs['api_gateway_url']['value']
        
        print(f"📊 Infrastructure deployed:")
        print(f"   - OpenSearch Endpoint: {self.opensearch_endpoint}")
        print(f"   - S3 Bucket: {self.s3_bucket}")
        print(f"   - API Gateway URL: {self.api_gateway_url}")
    
    def build_lambda_functions(self):
        """Build Lambda function deployment packages"""
        lambda_functions = ['concept_extractor', 'concept_query']
        
        for func_name in lambda_functions:
            print(f"🔨 Building {func_name}...")
            
            # Create build directory
            build_dir = self.lambda_dir / f'{func_name}_build'
            if build_dir.exists():
                shutil.rmtree(build_dir)
            build_dir.mkdir()
            
            # Copy function code
            func_file = self.lambda_dir / f'{func_name}.py'
            shutil.copy2(func_file, build_dir)
            
            # Install dependencies
            requirements_file = self.lambda_dir / 'requirements.txt'
            if requirements_file.exists():
                subprocess.run([
                    'pip', 'install', '-r', str(requirements_file),
                    '-t', str(build_dir)
                ], check=True)
            
            # Create ZIP file
            zip_path = self.lambda_dir / f'{func_name}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in build_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(build_dir)
                        zipf.write(file_path, arcname)
            
            # Clean up build directory
            shutil.rmtree(build_dir)
            
            print(f"✅ {func_name}.zip created")
    
    def upload_lambda_functions(self):
        """Upload Lambda functions to AWS"""
        lambda_functions = ['concept_extractor', 'concept_query']
        
        for func_name in lambda_functions:
            print(f"📤 Uploading {func_name}...")
            
            zip_path = self.lambda_dir / f'{func_name}.zip'
            
            # Update Lambda function code
            with open(zip_path, 'rb') as f:
                self.lambda_client.update_function_code(
                    FunctionName=f'{self.project_name}-{func_name}',
                    ZipFile=f.read()
                )
            
            # Update environment variables
            env_vars = {
                'OPENSEARCH_ENDPOINT': self.opensearch_endpoint,
                'S3_BUCKET': self.s3_bucket,
                'PROJECT_NAME': self.project_name
            }
            
            self.lambda_client.update_function_configuration(
                FunctionName=f'{self.project_name}-{func_name}',
                Environment={'Variables': env_vars}
            )
            
            print(f"✅ {func_name} updated")
    
    def test_deployment(self):
        """Test the deployed pipeline"""
        print("🧪 Testing deployment...")
        
        # Test API Gateway
        try:
            import requests
            response = requests.get(self.api_gateway_url)
            if response.status_code == 200:
                print("✅ API Gateway is responding")
            else:
                print(f"⚠️ API Gateway returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Could not test API Gateway: {e}")
        
        # Test S3 bucket
        try:
            self.s3.head_bucket(Bucket=self.s3_bucket)
            print("✅ S3 bucket is accessible")
        except Exception as e:
            print(f"⚠️ Could not access S3 bucket: {e}")
        
        # Test OpenSearch
        try:
            import requests
            from requests_aws4auth import AWS4Auth
            
            session = boto3.Session()
            credentials = session.get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key, 
                credentials.secret_key, 
                session.region_name, 
                'aoss', 
                session_token=credentials.token
            )
            
            response = requests.get(
                f"{self.opensearch_endpoint}/_cluster/health",
                auth=awsauth
            )
            
            if response.status_code == 200:
                print("✅ OpenSearch is accessible")
            else:
                print(f"⚠️ OpenSearch returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Could not test OpenSearch: {e}")
    
    def upload_sample_data(self, data_path):
        """Upload sample data to S3 for processing"""
        print(f"📤 Uploading sample data from {data_path}...")
        
        data_path = Path(data_path)
        if not data_path.exists():
            print(f"❌ Data path {data_path} does not exist")
            return
        
        # Upload JSON files
        for json_file in data_path.rglob('*.json'):
            if 'concepts' in json_file.name.lower():
                key = f"sample_data/{json_file.name}"
                
                with open(json_file, 'rb') as f:
                    self.s3.upload_fileobj(f, self.s3_bucket, key)
                
                print(f"✅ Uploaded {json_file.name}")
    
    def cleanup(self):
        """Clean up deployment artifacts"""
        print("🧹 Cleaning up...")
        
        # Remove ZIP files
        for zip_file in self.lambda_dir.glob('*.zip'):
            zip_file.unlink()
            print(f"🗑️ Removed {zip_file.name}")
        
        print("✅ Cleanup completed")


def main():
    parser = argparse.ArgumentParser(description='Deploy AWS Semantic Concept Pipeline')
    parser.add_argument('--environment', default='dev', choices=['dev', 'staging', 'prod'],
                       help='Deployment environment')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--upload-data', help='Path to sample data to upload')
    parser.add_argument('--cleanup', action='store_true', help='Clean up after deployment')
    
    args = parser.parse_args()
    
    deployer = AWSSemanticPipelineDeployer(region=args.region)
    
    try:
        # Deploy pipeline
        deployer.deploy(environment=args.environment)
        
        # Upload sample data if specified
        if args.upload_data:
            deployer.upload_sample_data(args.upload_data)
        
        # Cleanup if requested
        if args.cleanup:
            deployer.cleanup()
        
    except KeyboardInterrupt:
        print("\n⚠️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 