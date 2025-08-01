#!/usr/bin/env python3
"""
Demo script for the AWS Semantic Concept Pipeline
"""

import json
import sys
from pathlib import Path
from client.semantic_client import create_client, create_analyzer

def demo_basic_search(client, api_url):
    """Demo basic concept search"""
    print("🔍 Demo: Basic Concept Search")
    print("=" * 50)
    
    # Search for topic particles
    print("Searching for 'topic particles'...")
    result = client.search_concepts("topic particles", limit=5)
    
    print(f"Found {result.count} concepts:")
    for i, concept in enumerate(result.results, 1):
        print(f"{i}. {concept.normalized_title} ({concept.jlpt_level})")
        print(f"   Category: {concept.category}")
        print(f"   Explanation: {concept.explanation[:100]}...")
        print(f"   Confidence: {concept.confidence:.2f}")
        print()
    
    # Search for grammar concepts
    print("Searching for 'grammar' concepts...")
    result = client.search_concepts("grammar", category="grammar", limit=3)
    
    print(f"Found {result.count} grammar concepts:")
    for i, concept in enumerate(result.results, 1):
        print(f"{i}. {concept.normalized_title} ({concept.jlpt_level})")
        print(f"   Related: {', '.join(concept.related_concepts[:3])}")
        print()


def demo_jlpt_filtering(client):
    """Demo JLPT level filtering"""
    print("📚 Demo: JLPT Level Filtering")
    print("=" * 50)
    
    # Get N5 concepts
    print("Getting N5 level concepts...")
    n5_concepts = client.get_concepts_by_jlpt_level("N5", limit=5)
    
    print(f"Found {len(n5_concepts)} N5 concepts:")
    for i, concept in enumerate(n5_concepts, 1):
        print(f"{i}. {concept.normalized_title}")
        print(f"   Category: {concept.category}")
        print(f"   Source: {concept.source}")
        print()
    
    # Get N4 concepts
    print("Getting N4 level concepts...")
    n4_concepts = client.get_concepts_by_jlpt_level("N4", limit=3)
    
    print(f"Found {len(n4_concepts)} N4 concepts:")
    for i, concept in enumerate(n4_concepts, 1):
        print(f"{i}. {concept.normalized_title}")
        print(f"   Category: {concept.category}")
        print()


def demo_learning_paths(client):
    """Demo learning path generation"""
    print("🛤️ Demo: Learning Path Generation")
    print("=" * 50)
    
    # Generate learning path for topic particles
    print("Generating learning path for 'topic particles'...")
    try:
        path = client.get_learning_path("topic particles", target_level="N4")
        
        print(f"Learning path with {path.concept_count} concepts:")
        for i, concept in enumerate(path.concepts, 1):
            print(f"{i}. {concept.normalized_title} ({concept.jlpt_level})")
            print(f"   Category: {concept.category}")
            if concept.examples:
                print(f"   Example: {concept.examples[0]}")
            print()
    except Exception as e:
        print(f"Error generating learning path: {e}")
        print("This might be because no concepts are indexed yet.")


def demo_statistics(client):
    """Demo statistics and analytics"""
    print("📊 Demo: Concept Statistics")
    print("=" * 50)
    
    try:
        stats = client.get_statistics()
        
        print(f"Total concepts: {stats.total_concepts}")
        print(f"Average confidence: {stats.average_confidence:.2f}")
        print()
        
        print("Concepts by category:")
        for category, count in stats.categories.items():
            print(f"  {category}: {count}")
        print()
        
        print("Concepts by JLPT level:")
        for level, count in stats.jlpt_levels.items():
            print(f"  {level}: {count}")
        print()
        
        print("Concepts by source:")
        for source, count in stats.sources.items():
            print(f"  {source}: {count}")
        print()
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
        print("This might be because no concepts are indexed yet.")


def demo_advanced_analysis(analyzer):
    """Demo advanced analysis features"""
    print("🧠 Demo: Advanced Analysis")
    print("=" * 50)
    
    # Demo study plan generation
    print("Generating study plan for N3 level...")
    try:
        study_plan = analyzer.generate_study_plan(
            target_level="N3",
            focus_areas=["grammar", "vocabulary"]
        )
        
        print(f"Study plan for {study_plan['target_level']}:")
        print(f"Total concepts: {study_plan['total_concepts']}")
        print(f"Estimated study time: {study_plan['estimated_study_time']['weeks']} weeks")
        print()
        
        print("Concepts by category:")
        for category, count in study_plan['concepts_by_category'].items():
            print(f"  {category}: {count}")
        print()
        
    except Exception as e:
        print(f"Error generating study plan: {e}")
        print("This might be because no concepts are indexed yet.")


def demo_concept_clusters(analyzer):
    """Demo concept clustering"""
    print("🔗 Demo: Concept Clustering")
    print("=" * 50)
    
    try:
        # Find clusters in grammar category
        print("Finding concept clusters in grammar category...")
        clusters = analyzer.find_concept_clusters(category="grammar")
        
        print(f"Found {len(clusters)} concept clusters:")
        for i, cluster in enumerate(clusters[:3], 1):  # Show first 3
            print(f"{i}. {cluster['main_concept'].normalized_title}")
            print(f"   Cluster size: {cluster['cluster_size']}")
            print(f"   Related concepts: {', '.join(cluster['related_concepts'][:3])}")
            print()
            
    except Exception as e:
        print(f"Error finding concept clusters: {e}")
        print("This might be because no concepts are indexed yet.")


def demo_api_info(client):
    """Demo API information"""
    print("ℹ️ Demo: API Information")
    print("=" * 50)
    
    try:
        info = client.get_api_info()
        
        print("API Information:")
        print(f"Message: {info.get('message', 'N/A')}")
        print()
        
        print("Available endpoints:")
        for endpoint, description in info.get('endpoints', {}).items():
            print(f"  {endpoint}: {description}")
        print()
        
    except Exception as e:
        print(f"Error getting API info: {e}")


def demo_upload_sample_data():
    """Demo uploading sample data"""
    print("📤 Demo: Sample Data Upload")
    print("=" * 50)
    
    # Create sample data
    sample_data = [
        {
            "id": "sample_1",
            "title": "は (topic marker)",
            "type": "grammar",
            "level": "N5",
            "meaning": "Topic particle used to mark the subject of a sentence",
            "examples": ["私は学生です", "これは本です"],
            "source": "demo"
        },
        {
            "id": "sample_2", 
            "title": "が (subject marker)",
            "type": "grammar",
            "level": "N5",
            "meaning": "Subject particle used to mark the subject of a verb",
            "examples": ["私が行きます", "雨が降っています"],
            "source": "demo"
        },
        {
            "id": "sample_3",
            "title": "を (object marker)",
            "type": "grammar", 
            "level": "N5",
            "meaning": "Object particle used to mark the direct object of a verb",
            "examples": ["本を読みます", "ご飯を食べます"],
            "source": "demo"
        }
    ]
    
    # Save sample data
    sample_file = Path("sample_data.json")
    with open(sample_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"Created sample data file: {sample_file}")
    print("You can upload this to S3 to trigger concept extraction:")
    print(f"aws s3 cp {sample_file} s3://your-bucket-name/sample_data/")
    print()


def main():
    """Main demo function"""
    print("🚀 AWS Semantic Concept Pipeline Demo")
    print("=" * 60)
    print()
    
    # Get API URL from command line or use default
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        api_url = input("Enter your API Gateway URL (or press Enter for demo mode): ").strip()
        if not api_url:
            print("\n📝 Demo Mode: No API URL provided, showing demo structure only")
            demo_upload_sample_data()
            return
    
    try:
        # Create client and analyzer
        client = create_client(api_url)
        analyzer = create_analyzer(api_url)
        
        print(f"✅ Connected to API: {api_url}")
        print()
        
        # Run demos
        demo_api_info(client)
        demo_basic_search(client, api_url)
        demo_jlpt_filtering(client)
        demo_learning_paths(client)
        demo_statistics(client)
        demo_advanced_analysis(analyzer)
        demo_concept_clusters(analyzer)
        
        print("🎉 Demo completed successfully!")
        print()
        print("💡 Next steps:")
        print("1. Upload your Japanese learning data to S3")
        print("2. The pipeline will automatically extract and index concepts")
        print("3. Use the client library to build your applications")
        print("4. Explore the API endpoints for more features")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("1. Make sure your API Gateway is deployed and accessible")
        print("2. Check that you have the correct API URL")
        print("3. Ensure your AWS credentials are configured")
        print("4. Verify that the pipeline has been deployed successfully")
        
        # Show demo structure anyway
        print()
        demo_upload_sample_data()


if __name__ == '__main__':
    main() 