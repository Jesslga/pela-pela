#!/usr/bin/env python3
"""
Enhanced Topic Clustering Visualization

This script creates comprehensive visualizations of the topic clustering results,
including detailed analysis of topic distributions, learning paths, and concept relationships.
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
import networkx as nx
from typing import List, Dict, Any
import os

# Set style
plt.style.use('default')
sns.set_palette("husl")

def load_clustering_data():
    """Load all clustering data."""
    with open('topic_clusters/topics.json', 'r', encoding='utf-8') as f:
        topics = json.load(f)
    
    with open('topic_clusters/concepts_with_topics.json', 'r', encoding='utf-8') as f:
        concepts = json.load(f)
    
    with open('topic_clusters/topic_relationships.json', 'r', encoding='utf-8') as f:
        relationships = json.load(f)
    
    return topics, concepts, relationships

def create_jlpt_topic_heatmap(topics: Dict[str, Any], concepts: List[Dict[str, Any]]):
    """Create a heatmap showing JLPT level distribution across topics."""
    
    # Create topic-JLPT matrix
    topic_jlpt_matrix = defaultdict(lambda: defaultdict(int))
    
    for concept in concepts:
        if concept.get('topic_id') and concept.get('jlpt_level'):
            topic_jlpt_matrix[concept['topic_id']][concept['jlpt_level']] += 1
    
    # Convert to DataFrame
    df = pd.DataFrame(topic_jlpt_matrix).T.fillna(0)
    
    # Sort topics by average difficulty
    topic_difficulties = {}
    for topic_id, topic_data in topics.items():
        if topic_id in df.index:
            topic_difficulties[topic_id] = topic_data['difficulty_range']['average']
    
    df = df.reindex(sorted(topic_difficulties.keys(), key=lambda x: topic_difficulties[x]))
    
    # Create heatmap
    plt.figure(figsize=(12, 16))
    sns.heatmap(df, annot=True, fmt='d', cmap='YlOrRd', cbar_kws={'label': 'Number of Concepts'})
    plt.title('JLPT Level Distribution Across Topics\n(Darker = More Concepts)', fontsize=16, pad=20)
    plt.xlabel('JLPT Level', fontsize=12)
    plt.ylabel('Topics (Sorted by Difficulty)', fontsize=12)
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('topic_clusters/visualizations/jlpt_topic_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_learning_path_visualization(topics: Dict[str, Any], relationships: Dict[str, List[str]]):
    """Create a learning path visualization showing topic progression."""
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Add nodes with difficulty information
    for topic_id, topic_data in topics.items():
        G.add_node(topic_id, 
                   difficulty=topic_data['difficulty_range']['average'],
                   name=topic_data['name'],
                   concept_count=topic_data['concept_count'])
    
    # Add edges based on relationships
    for topic_id, related_topics in relationships.items():
        for related_topic in related_topics:
            if related_topic in topics:
                # Only add edge if it goes from lower to higher difficulty
                if (topics[topic_id]['difficulty_range']['average'] < 
                    topics[related_topic]['difficulty_range']['average']):
                    G.add_edge(topic_id, related_topic)
    
    # Create layout based on difficulty
    pos = {}
    for topic_id in G.nodes():
        difficulty = G.nodes[topic_id]['difficulty']
        # Position by difficulty (x-axis) and some random y variation
        pos[topic_id] = (difficulty, np.random.uniform(-1, 1))
    
    # Create visualization
    plt.figure(figsize=(20, 12))
    
    # Draw nodes
    node_colors = [G.nodes[node]['difficulty'] for node in G.nodes()]
    node_sizes = [G.nodes[node]['concept_count'] * 10 for node in G.nodes()]
    
    nx.draw_networkx_nodes(G, pos, 
                          node_color=node_colors, 
                          node_size=node_sizes,
                          cmap=plt.cm.viridis,
                          alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, 
                          edge_color='gray', 
                          alpha=0.3, 
                          arrows=True,
                          arrowsize=10)
    
    # Add labels for some nodes (to avoid clutter)
    labels = {}
    for node in G.nodes():
        if G.nodes[node]['concept_count'] > 20:  # Only label larger topics
            labels[node] = G.nodes[node]['name'][:15] + '...'
    
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.colorbar(plt.cm.ScalarMappable(cmap=plt.cm.viridis), 
                label='Average Difficulty')
    plt.title('Learning Path Visualization\n(Node size = concept count, Color = difficulty)', 
              fontsize=16, pad=20)
    plt.xlabel('Difficulty Level', fontsize=12)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('topic_clusters/visualizations/learning_paths.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_topic_size_analysis(topics: Dict[str, Any]):
    """Create detailed analysis of topic sizes and distributions."""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Extract data
    concept_counts = [topic['concept_count'] for topic in topics.values()]
    difficulties = [topic['difficulty_range']['average'] for topic in topics.values()]
    jlpt_levels = []
    for topic in topics.values():
        jlpt_levels.extend(topic['jlpt_levels'])
    
    # 1. Topic size distribution
    ax1.hist(concept_counts, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.set_xlabel('Number of Concepts per Topic')
    ax1.set_ylabel('Number of Topics')
    ax1.set_title('Topic Size Distribution')
    ax1.axvline(np.mean(concept_counts), color='red', linestyle='--', 
                label=f'Mean: {np.mean(concept_counts):.1f}')
    ax1.legend()
    
    # 2. Difficulty vs Topic Size
    ax2.scatter(difficulties, concept_counts, alpha=0.6, s=50)
    ax2.set_xlabel('Average Difficulty')
    ax2.set_ylabel('Number of Concepts')
    ax2.set_title('Difficulty vs Topic Size')
    
    # 3. JLPT Level Distribution
    jlpt_counts = Counter(jlpt_levels)
    ax3.bar(jlpt_counts.keys(), jlpt_counts.values(), color='lightcoral')
    ax3.set_xlabel('JLPT Level')
    ax3.set_ylabel('Number of Topics')
    ax3.set_title('JLPT Level Distribution Across Topics')
    
    # 4. Difficulty distribution
    ax4.hist(difficulties, bins=15, alpha=0.7, color='lightgreen', edgecolor='black')
    ax4.set_xlabel('Average Difficulty')
    ax4.set_ylabel('Number of Topics')
    ax4.set_title('Difficulty Distribution')
    ax4.axvline(np.mean(difficulties), color='red', linestyle='--', 
                label=f'Mean: {np.mean(difficulties):.1f}')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('topic_clusters/visualizations/topic_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_concept_quality_analysis(concepts: List[Dict[str, Any]]):
    """Analyze the quality of concepts across different dimensions."""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Extract data
    jlpt_levels = [c.get('jlpt_level', 'Unknown') for c in concepts]
    has_meaning = [bool(c.get('meaning')) for c in concepts]
    has_usage = [bool(c.get('usage')) for c in concepts]
    has_examples = [bool(c.get('examples')) for c in concepts]
    embedding_lengths = [len(c.get('embedding_input', '')) for c in concepts]
    
    # 1. Data quality by JLPT level
    jlpt_quality = defaultdict(lambda: {'meaning': 0, 'usage': 0, 'examples': 0, 'total': 0})
    for i, level in enumerate(jlpt_levels):
        jlpt_quality[level]['total'] += 1
        if has_meaning[i]:
            jlpt_quality[level]['meaning'] += 1
        if has_usage[i]:
            jlpt_quality[level]['usage'] += 1
        if has_examples[i]:
            jlpt_quality[level]['examples'] += 1
    
    # Convert to percentages
    quality_data = []
    for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
        if level in jlpt_quality:
            total = jlpt_quality[level]['total']
            quality_data.append({
                'JLPT': level,
                'Meaning': jlpt_quality[level]['meaning'] / total * 100,
                'Usage': jlpt_quality[level]['usage'] / total * 100,
                'Examples': jlpt_quality[level]['examples'] / total * 100
            })
    
    df_quality = pd.DataFrame(quality_data)
    df_quality.set_index('JLPT').plot(kind='bar', ax=ax1)
    ax1.set_title('Data Quality by JLPT Level')
    ax1.set_ylabel('Percentage of Concepts')
    ax1.legend()
    
    # 2. Embedding input length distribution
    ax2.hist(embedding_lengths, bins=30, alpha=0.7, color='orange', edgecolor='black')
    ax2.set_xlabel('Embedding Input Length')
    ax2.set_ylabel('Number of Concepts')
    ax2.set_title('Embedding Input Length Distribution')
    ax2.axvline(np.mean(embedding_lengths), color='red', linestyle='--', 
                label=f'Mean: {np.mean(embedding_lengths):.1f}')
    ax2.legend()
    
    # 3. Overall data quality summary
    total_concepts = len(concepts)
    quality_summary = {
        'Has Meaning': sum(has_meaning) / total_concepts * 100,
        'Has Usage': sum(has_usage) / total_concepts * 100,
        'Has Examples': sum(has_examples) / total_concepts * 100
    }
    
    ax3.bar(quality_summary.keys(), quality_summary.values(), color=['lightblue', 'lightgreen', 'lightcoral'])
    ax3.set_ylabel('Percentage of Concepts')
    ax3.set_title('Overall Data Quality')
    ax3.set_ylim(0, 100)
    
    # 4. Concept distribution by source
    sources = [c.get('source', 'Unknown') for c in concepts]
    source_counts = Counter(sources)
    ax4.pie(source_counts.values(), labels=source_counts.keys(), autopct='%1.1f%%')
    ax4.set_title('Concept Distribution by Source')
    
    plt.tight_layout()
    plt.savefig('topic_clusters/visualizations/concept_quality_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_topic_explorer_report(topics: Dict[str, Any], concepts: List[Dict[str, Any]]):
    """Create a comprehensive report for exploring topics."""
    
    report = []
    report.append("# Topic Explorer Report\n")
    report.append(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Summary statistics
    total_topics = len(topics)
    total_concepts = len(concepts)
    concepts_with_topics = len([c for c in concepts if c.get('topic_id')])
    
    report.append("## Summary Statistics\n")
    report.append(f"- **Total Topics**: {total_topics}")
    report.append(f"- **Total Concepts**: {total_concepts}")
    report.append(f"- **Concepts with Topics**: {concepts_with_topics} ({concepts_with_topics/total_concepts*100:.1f}%)")
    report.append(f"- **Concepts without Topics**: {total_concepts - concepts_with_topics}\n")
    
    # JLPT level distribution
    jlpt_counts = Counter([c.get('jlpt_level', 'Unknown') for c in concepts])
    report.append("## JLPT Level Distribution\n")
    for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
        count = jlpt_counts.get(level, 0)
        report.append(f"- **{level}**: {count} concepts")
    report.append("")
    
    # Topic details by difficulty
    report.append("## Topics by Difficulty Level\n")
    
    # Sort topics by difficulty
    sorted_topics = sorted(topics.items(), 
                          key=lambda x: x[1]['difficulty_range']['average'])
    
    for topic_id, topic_data in sorted_topics:
        report.append(f"### {topic_data['name']} (ID: {topic_id})\n")
        report.append(f"- **Difficulty**: {topic_data['difficulty_range']['average']:.2f} (Range: {topic_data['difficulty_range']['min']:.2f} - {topic_data['difficulty_range']['max']:.2f})")
        report.append(f"- **Concepts**: {topic_data['concept_count']}")
        report.append(f"- **JLPT Levels**: {', '.join(topic_data['jlpt_levels']) if topic_data['jlpt_levels'] else 'None'}")
        report.append(f"- **Keywords**: {', '.join(topic_data['common_keywords'][:5])}")
        report.append(f"- **Description**: {topic_data['description'][:200]}...")
        
        # Show sample concepts
        topic_concepts = [c for c in concepts if c.get('topic_id') == topic_id]
        if topic_concepts:
            report.append("- **Sample Concepts**:")
            for concept in topic_concepts[:5]:
                report.append(f"  - {concept.get('title', 'Unknown')} ({concept.get('jlpt_level', 'Unknown')})")
        report.append("")
    
    # Save report
    with open('topic_clusters/visualizations/topic_explorer_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

def main():
    """Main function to create enhanced visualizations."""
    print("=== Creating Enhanced Visualizations ===")
    
    # Load data
    topics, concepts, relationships = load_clustering_data()
    
    print(f"Loaded {len(topics)} topics and {len(concepts)} concepts")
    
    # Create visualizations
    print("Creating JLPT topic heatmap...")
    create_jlpt_topic_heatmap(topics, concepts)
    
    print("Creating learning path visualization...")
    create_learning_path_visualization(topics, relationships)
    
    print("Creating topic size analysis...")
    create_topic_size_analysis(topics)
    
    print("Creating concept quality analysis...")
    create_concept_quality_analysis(concepts)
    
    print("Creating topic explorer report...")
    create_topic_explorer_report(topics, concepts)
    
    print("\n✅ Enhanced visualizations completed!")
    print("📁 Files saved to topic_clusters/visualizations/")
    print("\nGenerated files:")
    print("- jlpt_topic_heatmap.png: JLPT level distribution across topics")
    print("- learning_paths.png: Visual learning progression paths")
    print("- topic_analysis.png: Detailed topic size and difficulty analysis")
    print("- concept_quality_analysis.png: Data quality analysis")
    print("- topic_explorer_report.md: Comprehensive topic exploration guide")

if __name__ == "__main__":
    main() 