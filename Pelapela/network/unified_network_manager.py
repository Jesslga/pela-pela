#!/usr/bin/env python3
"""
Unified Concept Network Manager
Handles loading, processing, and cleanup of all concept network data
"""
import json
import os
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path

class ConceptNetworkManager:
    def __init__(self, data_dir: str = "concept_network"):
        """Initialize the network manager with data directory"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Define file paths
        self.files = {
            # Core processed files (keep these)
            'unified': self.data_dir / 'quick_test_unified.json',
            'enriched': self.data_dir / 'quick_test_enriched.json',
            'normalized': self.data_dir / 'quick_test_normalized.json',
            
            # Analysis files (keep these)
            'enrichment_analysis': self.data_dir / 'enrichment_analysis.json',
            'quality_analysis': self.data_dir / 'quality_analysis_report.json',
            'unification_summary': self.data_dir / 'unification_summary.json',
            'network_summary': self.data_dir / 'network_summary.json',
            
            # Legacy files (can be cleaned up)
            'legacy_grammar': self.data_dir / 'grammar.json',
            'legacy_vocabulary': self.data_dir / 'vocabulary.json',
            'legacy_kanji': self.data_dir / 'kanji.json',
            'legacy_expression': self.data_dir / 'expression.json',
            'legacy_complete': self.data_dir / 'complete_network.json',
            'legacy_complete_updated': self.data_dir / 'complete_network_updated.json',
            'legacy_complete_comprehensive': self.data_dir / 'complete_network_comprehensive.json',
            'legacy_complete_with_n4': self.data_dir / 'complete_network_with_n4.json',
            'legacy_complete_enhanced': self.data_dir / 'complete_network_enhanced.json',
            'legacy_complete_deduped': self.data_dir / 'complete_network_deduped.json',
            'legacy_enriched': self.data_dir / 'enriched_network.json',
            'legacy_enriched_sample': self.data_dir / 'enriched_network_sample.json',
            'legacy_normalized': self.data_dir / '01_normalized_concepts.json',
        }
    
    def load_unified_concepts(self) -> List[Dict[str, Any]]:
        """Load the unified concept data (main data source)"""
        if not self.files['unified'].exists():
            raise FileNotFoundError(f"Unified concepts file not found: {self.files['unified']}")
        
        print(f"Loading unified concepts from {self.files['unified']}...")
        with open(self.files['unified'], 'r', encoding='utf-8') as f:
            concepts = json.load(f)
        
        print(f"Loaded {len(concepts)} unified concepts")
        return concepts
    
    def load_enriched_concepts(self) -> List[Dict[str, Any]]:
        """Load the enriched concept data (with MeCab analysis)"""
        if not self.files['enriched'].exists():
            raise FileNotFoundError(f"Enriched concepts file not found: {self.files['enriched']}")
        
        print(f"Loading enriched concepts from {self.files['enriched']}...")
        with open(self.files['enriched'], 'r', encoding='utf-8') as f:
            concepts = json.load(f)
        
        print(f"Loaded {len(concepts)} enriched concepts")
        return concepts
    
    def load_normalized_concepts(self) -> List[Dict[str, Any]]:
        """Load the normalized concept data"""
        if not self.files['normalized'].exists():
            raise FileNotFoundError(f"Normalized concepts file not found: {self.files['normalized']}")
        
        print(f"Loading normalized concepts from {self.files['normalized']}...")
        with open(self.files['normalized'], 'r', encoding='utf-8') as f:
            concepts = json.load(f)
        
        print(f"Loaded {len(concepts)} normalized concepts")
        return concepts
    
    def load_analysis_data(self) -> Dict[str, Any]:
        """Load all analysis data"""
        analysis_data = {}
        
        # Load enrichment analysis
        if self.files['enrichment_analysis'].exists():
            with open(self.files['enrichment_analysis'], 'r', encoding='utf-8') as f:
                analysis_data['enrichment'] = json.load(f)
        
        # Load quality analysis
        if self.files['quality_analysis'].exists():
            with open(self.files['quality_analysis'], 'r', encoding='utf-8') as f:
                analysis_data['quality'] = json.load(f)
        
        # Load unification summary
        if self.files['unification_summary'].exists():
            with open(self.files['unification_summary'], 'r', encoding='utf-8') as f:
                analysis_data['unification'] = json.load(f)
        
        # Load network summary
        if self.files['network_summary'].exists():
            with open(self.files['network_summary'], 'r', encoding='utf-8') as f:
                analysis_data['network'] = json.load(f)
        
        return analysis_data
    
    def save_concepts(self, concepts: List[Dict[str, Any]], filename: str) -> None:
        """Save concepts to a file"""
        filepath = self.data_dir / filename
        print(f"Saving {len(concepts)} concepts to {filepath}...")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, indent=2, ensure_ascii=False)
        
        print(f"Saved to {filepath}")
    
    def get_concept_stats(self, concepts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about concepts"""
        stats = {
            'total': len(concepts),
            'by_type': {},
            'by_source': {},
            'with_japanese': 0,
            'with_patterns': 0,
            'with_vocabulary': 0,
            'with_kanji': 0,
        }
        
        for concept in concepts:
            # Count by type
            concept_type = concept.get('type', 'unknown')
            stats['by_type'][concept_type] = stats['by_type'].get(concept_type, 0) + 1
            
            # Count by source
            sources = concept.get('sources', [])
            for source in sources:
                stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            
            # Count enriched features
            if concept.get('japanese'):
                stats['with_japanese'] += 1
            if concept.get('grammar_patterns'):
                stats['with_patterns'] += 1
            if concept.get('vocabulary_items'):
                stats['with_vocabulary'] += 1
            if concept.get('kanji'):
                stats['with_kanji'] += 1
        
        return stats
    
    def print_concept_stats(self, concepts: List[Dict[str, Any]], title: str = "Concept Statistics") -> None:
        """Print formatted concept statistics"""
        stats = self.get_concept_stats(concepts)
        
        print(f"\n=== {title} ===")
        print(f"Total concepts: {stats['total']}")
        
        print(f"\nBy type:")
        for concept_type, count in sorted(stats['by_type'].items()):
            percentage = (count / stats['total']) * 100
            print(f"  {concept_type}: {count} ({percentage:.1f}%)")
        
        print(f"\nBy source:")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count}")
        
        if stats['with_japanese'] > 0:
            print(f"\nEnrichment coverage:")
            print(f"  With Japanese: {stats['with_japanese']} ({stats['with_japanese']/stats['total']*100:.1f}%)")
            print(f"  With Patterns: {stats['with_patterns']} ({stats['with_patterns']/stats['total']*100:.1f}%)")
            print(f"  With Vocabulary: {stats['with_vocabulary']} ({stats['with_vocabulary']/stats['total']*100:.1f}%)")
            print(f"  With Kanji: {stats['with_kanji']} ({stats['with_kanji']/stats['total']*100:.1f}%)")
    
    def cleanup_legacy_files(self, dry_run: bool = True) -> List[str]:
        """Clean up legacy files that are no longer needed"""
        legacy_files = [
            'legacy_grammar', 'legacy_vocabulary', 'legacy_kanji', 'legacy_expression',
            'legacy_complete', 'legacy_complete_updated', 'legacy_complete_comprehensive',
            'legacy_complete_with_n4', 'legacy_complete_enhanced', 'legacy_complete_deduped',
            'legacy_enriched', 'legacy_enriched_sample', 'legacy_normalized'
        ]
        
        files_to_delete = []
        total_size = 0
        
        for file_key in legacy_files:
            filepath = self.files[file_key]
            if filepath.exists():
                size = filepath.stat().st_size
                files_to_delete.append(str(filepath))
                total_size += size
                print(f"Would delete: {filepath} ({size / (1024*1024):.1f} MB)")
        
        if not dry_run and files_to_delete:
            print(f"\nDeleting {len(files_to_delete)} legacy files ({total_size / (1024*1024):.1f} MB total)...")
            for filepath in files_to_delete:
                os.remove(filepath)
                print(f"Deleted: {filepath}")
        elif dry_run:
            print(f"\nDRY RUN: Would delete {len(files_to_delete)} files ({total_size / (1024*1024):.1f} MB total)")
        
        return files_to_delete
    
    def get_file_sizes(self) -> Dict[str, float]:
        """Get sizes of all data files in MB"""
        sizes = {}
        for name, filepath in self.files.items():
            if filepath.exists():
                size_mb = filepath.stat().st_size / (1024 * 1024)
                sizes[name] = size_mb
            else:
                sizes[name] = 0.0
        return sizes
    
    def print_file_sizes(self) -> None:
        """Print sizes of all data files"""
        sizes = self.get_file_sizes()
        
        print("\n=== FILE SIZES ===")
        for name, size_mb in sorted(sizes.items(), key=lambda x: x[1], reverse=True):
            if size_mb > 0:
                print(f"{name}: {size_mb:.1f} MB")
            else:
                print(f"{name}: Not found")

def main():
    """Main function to demonstrate usage"""
    manager = ConceptNetworkManager()
    
    # Print file sizes
    manager.print_file_sizes()
    
    # Load and analyze unified concepts
    try:
        concepts = manager.load_unified_concepts()
        manager.print_concept_stats(concepts, "Unified Concepts")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Load and analyze enriched concepts
    try:
        enriched_concepts = manager.load_enriched_concepts()
        manager.print_concept_stats(enriched_concepts, "Enriched Concepts")
    except FileNotFoundError as e:
        print(f"Warning: {e}")
    
    # Show cleanup options
    print("\n=== CLEANUP OPTIONS ===")
    print("Run cleanup_legacy_files(dry_run=False) to delete unnecessary files")
    print("Run cleanup_legacy_files(dry_run=True) to see what would be deleted")

if __name__ == "__main__":
    main() 