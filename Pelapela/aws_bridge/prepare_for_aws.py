#!/usr/bin/env python3
"""
AWS Bridge Script - Prepare Local Data for AWS Upload

This script combines all locally processed *_for_network.json files
and prepares them for upload to the AWS semantic pipeline.

Usage:
    python prepare_for_aws.py [--upload] [--environment dev|prod]
"""

import json
import os
import boto3
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSDataBridge:
    """Bridge between local data processing and AWS semantic pipeline"""
    
    def __init__(self, environment: str = "dev"):
        self.environment = environment
        self.s3_client = None
        self.bucket_name = f"pelapela-semantic-raw-data-{environment}"
        
        # Data source file paths
        self.data_sources = {
            'anki': 'data_sources/anki/anki_concepts_for_network.json',
            'jlpt': 'data_sources/jlpt/jlpt_concepts_for_network.json', 
            'taekim': 'data_sources/taekim/taekim_concepts_for_network.json',
            'duo': 'data_sources/duo/duo_concepts_for_network.json'
        }
        
    def load_local_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all processed local data files"""
        logger.info("🔄 Loading local processed data...")
        
        combined_data = {}
        total_concepts = 0
        
        for source, file_path in self.data_sources.items():
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        combined_data[source] = data
                        count = len(data) if isinstance(data, list) else len(data.get('concepts', []))
                        total_concepts += count
                        logger.info(f"   ✅ {source}: {count:,} concepts")
                except Exception as e:
                    logger.error(f"   ❌ Error loading {source}: {e}")
            else:
                logger.warning(f"   ⚠️  Missing: {file_path}")
        
        logger.info(f"📊 Total concepts loaded: {total_concepts:,}")
        return combined_data
    
    def prepare_for_aws(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Prepare data in format expected by AWS semantic pipeline"""
        logger.info("🔧 Preparing data for AWS...")
        
        # Combine all concepts with source tracking
        unified_concepts = []
        
        for source, concepts in data.items():
            if isinstance(concepts, list):
                concept_list = concepts
            else:
                concept_list = concepts.get('concepts', [])
            
            for concept in concept_list:
                # Ensure concept has required fields for AWS pipeline
                unified_concept = {
                    'source': source,
                    'concept_title': concept.get('word') or concept.get('title') or concept.get('concept_title', ''),
                    'definition': concept.get('definition', ''),
                    'examples': concept.get('examples', []),
                    'type': concept.get('type', 'unknown'),
                    'original_data': concept
                }
                unified_concepts.append(unified_concept)
        
        prepared_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_concepts': len(unified_concepts),
                'sources': list(data.keys()),
                'environment': self.environment
            },
            'concepts': unified_concepts
        }
        
        logger.info(f"✅ Prepared {len(unified_concepts):,} unified concepts")
        return prepared_data
    
    def save_prepared_data(self, data: Dict[str, Any], output_path: str = "aws_upload_ready.json"):
        """Save prepared data locally"""
        logger.info(f"💾 Saving prepared data to {output_path}...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✅ Saved: {output_path} ({size_mb:.1f} MB)")
        return output_path
    
    def upload_to_s3(self, file_path: str, s3_key: str = None):
        """Upload prepared data to S3 for AWS pipeline"""
        if not s3_key:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"batch_upload/{timestamp}/unified_concepts.json"
        
        try:
            logger.info(f"☁️  Uploading to S3: s3://{self.bucket_name}/{s3_key}")
            
            if not self.s3_client:
                self.s3_client = boto3.client('s3')
            
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            logger.info(f"✅ Upload successful!")
            
            # Return S3 URL for reference
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            return s3_url
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return None
    
    def run_full_pipeline(self, upload: bool = False):
        """Run the complete local → AWS preparation pipeline"""
        logger.info("🚀 Starting Local → AWS Data Bridge Pipeline")
        logger.info("=" * 60)
        
        # 1. Load local data
        local_data = self.load_local_data()
        
        if not local_data:
            logger.error("❌ No local data found. Run local processing first.")
            return None
        
        # 2. Prepare for AWS
        prepared_data = self.prepare_for_aws(local_data)
        
        # 3. Save locally
        output_file = self.save_prepared_data(prepared_data)
        
        # 4. Upload if requested
        if upload:
            s3_url = self.upload_to_s3(output_file)
            if s3_url:
                logger.info(f"🎉 Pipeline complete! Data available at: {s3_url}")
                return s3_url
        else:
            logger.info(f"🎉 Pipeline complete! Data ready for upload: {output_file}")
            logger.info("    Run with --upload flag to upload to S3")
        
        return output_file

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare local data for AWS upload")
    parser.add_argument('--upload', action='store_true', help='Upload to S3 after preparation')
    parser.add_argument('--environment', choices=['dev', 'prod'], default='dev', 
                       help='AWS environment (default: dev)')
    
    args = parser.parse_args()
    
    # Initialize bridge
    bridge = AWSDataBridge(environment=args.environment)
    
    # Run pipeline
    result = bridge.run_full_pipeline(upload=args.upload)
    
    if result:
        print(f"\n✅ Success! Result: {result}")
    else:
        print("\n❌ Pipeline failed")
        exit(1)

if __name__ == "__main__":
    main()