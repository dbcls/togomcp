#!/usr/bin/env python3
"""
TogoMCP Question Generator Helper

Assists in creating high-quality evaluation questions through:
- Interactive question builder
- Category-specific templates
- Auto-generated variations
- Database-specific suggestions

Usage:
    python question_generator.py                    # Interactive mode
    python question_generator.py --batch 5          # Generate 5 questions
    python question_generator.py --entity BRCA1     # Generate for specific entity
    python question_generator.py --template         # Show all templates
"""

import json
import sys
import argparse
from typing import List, Dict, Optional
from pathlib import Path


class QuestionGenerator:
    """Generate TogoMCP evaluation questions."""
    
    CATEGORIES = [
        "Precision",
        "Completeness", 
        "Integration",
        "Currency",
        "Specificity",
        "Structured Query"
    ]
    
    # Question templates by category
    TEMPLATES = {
        "Precision": [
            {
                "template": "What is the {id_type} for {organism} {gene}?",
                "params": {"id_type": ["UniProt ID", "NCBI Gene ID", "Ensembl ID"], 
                          "organism": ["human", "mouse", "rat"], 
                          "gene": ["<GENE_NAME>"]},
                "example": "What is the UniProt ID for human BRCA1?",
                "databases": ["UniProt", "NCBI Gene", "Ensembl"]
            },
            {
                "template": "What is the PubChem Compound ID for {compound}?",
                "params": {"compound": ["<COMPOUND_NAME>"]},
                "example": "What is the PubChem Compound ID for aspirin?",
                "databases": ["PubChem"]
            },
            {
                "template": "What is the EC number for {organism} {enzyme}?",
                "params": {"organism": ["human", "mouse", "E. coli"], 
                          "enzyme": ["<ENZYME_NAME>"]},
                "example": "What is the EC number for human hexokinase?",
                "databases": ["UniProt", "ChEBI"]
            },
            {
                "template": "What is the SMILES string for {compound} (PubChem CID {cid})?",
                "params": {"compound": ["<COMPOUND_NAME>"], "cid": ["<CID>"]},
                "example": "What is the SMILES string for caffeine (PubChem CID 2519)?",
                "databases": ["PubChem"]
            },
            {
                "template": "What is the MeSH descriptor ID for {disease}?",
                "params": {"disease": ["<DISEASE_NAME>"]},
                "example": "What is the MeSH descriptor ID for Alzheimer's disease?",
                "databases": ["MeSH"]
            }
        ],
        "Completeness": [
            {
                "template": "How many {organism} genes are annotated with the GO term '{go_term}' ({go_id})?",
                "params": {"organism": ["human", "mouse", "rat"], 
                          "go_term": ["<GO_TERM_NAME>"], 
                          "go_id": ["<GO_ID>"]},
                "example": "How many human genes are annotated with GO term 'DNA repair' (GO:0006281)?",
                "databases": ["GO"]
            },
            {
                "template": "List all {type} in {database} that involve {substrate}.",
                "params": {"type": ["biochemical reactions", "pathways"], 
                          "database": ["Rhea", "Reactome"],
                          "substrate": ["<SUBSTRATE_NAME>"]},
                "example": "List all biochemical reactions in Rhea that involve ATP as substrate.",
                "databases": ["Rhea", "Reactome"]
            },
            {
                "template": "How many protein structures are available for {protein} in PDB?",
                "params": {"protein": ["<PROTEIN_NAME>"]},
                "example": "How many protein structures are available for p53 in PDB?",
                "databases": ["PDB"]
            },
            {
                "template": "List all known variants of {gene} in ClinVar.",
                "params": {"gene": ["<GENE_NAME>"]},
                "example": "List all known variants of BRCA1 in ClinVar.",
                "databases": ["ClinVar"]
            }
        ],
        "Integration": [
            {
                "template": "Convert the {source_db} ID {source_id} to its corresponding {target_db} ID.",
                "params": {"source_db": ["UniProt", "NCBI Gene", "Ensembl"],
                          "source_id": ["<ID>"],
                          "target_db": ["NCBI Gene", "UniProt", "ChEMBL"]},
                "example": "Convert UniProt ID P04637 to its corresponding NCBI Gene ID.",
                "databases": ["TogoID", "UniProt", "NCBI Gene"]
            },
            {
                "template": "Find the {target_db} targets associated with PubChem compound {cid} ({compound}).",
                "params": {"target_db": ["ChEMBL", "UniProt"],
                          "cid": ["<CID>"],
                          "compound": ["<COMPOUND_NAME>"]},
                "example": "Find ChEMBL targets for PubChem compound 5288826 (resveratrol).",
                "databases": ["PubChem", "ChEMBL"]
            },
            {
                "template": "What proteins interact with {protein} according to {database}?",
                "params": {"protein": ["<PROTEIN_NAME>"],
                          "database": ["UniProt", "Reactome"]},
                "example": "What proteins interact with p53 according to UniProt?",
                "databases": ["UniProt", "Reactome"]
            },
            {
                "template": "Find PDB structures for {organism} {protein}.",
                "params": {"organism": ["human", "mouse"], 
                          "protein": ["<PROTEIN_NAME>"]},
                "example": "Find PDB structures for human p53.",
                "databases": ["PDB", "UniProt"]
            }
        ],
        "Currency": [
            {
                "template": "What pathways in Reactome involve {topic} proteins?",
                "params": {"topic": ["SARS-CoV-2", "Zika virus", "recent viral"]},
                "example": "What pathways in Reactome involve SARS-CoV-2 proteins?",
                "databases": ["Reactome"]
            },
            {
                "template": "What are the most recent publications about {topic} in PubMed?",
                "params": {"topic": ["<RESEARCH_TOPIC>"]},
                "example": "What are the most recent publications about mRNA vaccines?",
                "databases": ["PubMed"]
            },
            {
                "template": "Find recently added {organism} genes in {database}.",
                "params": {"organism": ["human", "mouse"],
                          "database": ["NCBI Gene", "UniProt"]},
                "example": "Find recently added human genes in NCBI Gene.",
                "databases": ["NCBI Gene", "UniProt"]
            }
        ],
        "Specificity": [
            {
                "template": "What is the MeSH descriptor ID for {rare_disease}?",
                "params": {"rare_disease": ["<RARE_DISEASE_NAME>"]},
                "example": "What is the MeSH descriptor ID for Erdheim-Chester disease?",
                "databases": ["MeSH"]
            },
            {
                "template": "Find information about {obscure_organism} in {database}.",
                "params": {"obscure_organism": ["<ORGANISM_NAME>"],
                          "database": ["Taxonomy", "UniProt"]},
                "example": "Find information about Pyrococcus furiosus in Taxonomy.",
                "databases": ["Taxonomy", "UniProt"]
            },
            {
                "template": "What is known about {niche_compound} in ChEBI?",
                "params": {"niche_compound": ["<COMPOUND_NAME>"]},
                "example": "What is known about batrachotoxin in ChEBI?",
                "databases": ["ChEBI"]
            }
        ],
        "Structured Query": [
            {
                "template": "Find all {organism} {protein_type} proteins in {db1} that are also targets in {db2}.",
                "params": {"organism": ["human", "mouse"],
                          "protein_type": ["kinase", "GPCR", "ion channel"],
                          "db1": ["UniProt"],
                          "db2": ["ChEMBL"]},
                "example": "Find all human kinase proteins in UniProt that are also targets in ChEMBL.",
                "databases": ["UniProt", "ChEMBL"]
            },
            {
                "template": "Find {type} in {database} with {property} {operator} {value}.",
                "params": {"type": ["compounds", "proteins"],
                          "database": ["ChEMBL", "PubChem"],
                          "property": ["IC50", "molecular weight"],
                          "operator": ["<", ">"],
                          "value": ["<VALUE>"]},
                "example": "Find kinase inhibitors in ChEMBL with IC50 < 10nM.",
                "databases": ["ChEMBL"]
            }
        ]
    }
    
    # Common entities for suggestions
    COMMON_ENTITIES = {
        "genes": ["BRCA1", "TP53", "EGFR", "KRAS", "MYC", "TNF", "IL6"],
        "proteins": ["p53", "insulin", "hemoglobin", "albumin", "cytochrome c"],
        "compounds": ["aspirin", "caffeine", "glucose", "ATP", "resveratrol", "metformin"],
        "diseases": ["Alzheimer's disease", "diabetes", "cancer", "COVID-19"],
        "organisms": ["Homo sapiens", "Mus musculus", "Escherichia coli"],
    }
    
    def __init__(self):
        """Initialize generator."""
        self.generated_questions = []
    
    def interactive_mode(self):
        """Interactive question generation."""
        print("=" * 70)
        print("TogoMCP Question Generator - Interactive Mode")
        print("=" * 70)
        print()
        
        while True:
            # Choose category
            print("Select category:")
            for i, cat in enumerate(self.CATEGORIES, 1):
                print(f"  {i}. {cat}")
            print("  0. Done (save and exit)")
            print()
            
            try:
                choice = int(input("Your choice [1-6, 0 to exit]: "))
                if choice == 0:
                    break
                if choice < 1 or choice > len(self.CATEGORIES):
                    print("Invalid choice. Try again.\n")
                    continue
                
                category = self.CATEGORIES[choice - 1]
                self._generate_for_category(category)
                
            except (ValueError, KeyboardInterrupt):
                print("\nExiting...\n")
                break
        
        self._save_questions()
    
    def _generate_for_category(self, category: str):
        """Generate question for specific category."""
        print(f"\n--- {category} Questions ---\n")
        
        templates = self.TEMPLATES[category]
        
        # Show templates
        print("Available templates:")
        for i, t in enumerate(templates, 1):
            print(f"  {i}. {t['example']}")
        print()
        
        try:
            choice = int(input(f"Choose template [1-{len(templates)}]: "))
            if choice < 1 or choice > len(templates):
                print("Invalid choice.\n")
                return
            
            template_info = templates[choice - 1]
            question = self._customize_template(template_info, category)
            
            if question:
                self.generated_questions.append(question)
                print(f"\n✓ Added question {len(self.generated_questions)}")
                print(f"  Q: {question['question']}\n")
        
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.\n")
    
    def _customize_template(self, template_info: Dict, category: str) -> Optional[Dict]:
        """Customize a template with user input."""
        print(f"\nTemplate: {template_info['example']}")
        print(f"Databases: {', '.join(template_info['databases'])}\n")
        
        # Get custom text
        question_text = input("Enter your question (or press Enter to use example): ").strip()
        
        if not question_text:
            question_text = template_info['example']
        
        expected_answer = input("Expected answer (optional): ").strip()
        notes = input("Notes (optional): ").strip()
        
        return {
            "id": len(self.generated_questions) + 1,
            "category": category,
            "question": question_text,
            "expected_answer": expected_answer if expected_answer else "TBD",
            "notes": notes if notes else f"Generated from template"
        }
    
    def batch_generate(self, entity: str, num_questions: int = 5):
        """Generate multiple questions for an entity."""
        print(f"Generating {num_questions} questions for: {entity}\n")
        
        variations = [
            ("Precision", f"What is the UniProt ID for human {entity}?"),
            ("Precision", f"What is the NCBI Gene ID for {entity}?"),
            ("Completeness", f"How many variants of {entity} are known?"),
            ("Integration", f"Find PDB structures for {entity}."),
            ("Integration", f"What pathways involve {entity}?"),
            ("Completeness", f"List all protein-protein interactions for {entity}."),
            ("Currency", f"What are recent publications about {entity}?"),
            ("Specificity", f"What post-translational modifications are known for {entity}?"),
        ]
        
        for i, (category, question_text) in enumerate(variations[:num_questions], 1):
            self.generated_questions.append({
                "id": i,
                "category": category,
                "question": question_text,
                "expected_answer": "TBD",
                "notes": f"Auto-generated for {entity}"
            })
            print(f"  {i}. [{category}] {question_text}")
        
        print(f"\n✓ Generated {len(self.generated_questions)} questions")
    
    def show_templates(self):
        """Display all available templates."""
        print("=" * 70)
        print("AVAILABLE QUESTION TEMPLATES")
        print("=" * 70)
        
        for category, templates in self.TEMPLATES.items():
            print(f"\n{category}:")
            print("-" * 70)
            for i, t in enumerate(templates, 1):
                print(f"  {i}. {t['example']}")
                print(f"     Databases: {', '.join(t['databases'])}")
        
        print("\n" + "=" * 70)
    
    def _save_questions(self):
        """Save generated questions to file."""
        if not self.generated_questions:
            print("No questions to save.")
            return
        
        filename = input(f"\nSave to file [generated_questions.json]: ").strip()
        if not filename:
            filename = "generated_questions.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = Path(filename)
        
        # Check if file exists
        if filepath.exists():
            overwrite = input(f"File {filename} exists. Overwrite? [y/N]: ").strip().lower()
            if overwrite != 'y':
                print("Cancelled.")
                return
        
        # Save
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.generated_questions, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(self.generated_questions)} questions to {filename}")
        print(f"\nNext steps:")
        print(f"  1. Review and edit {filename}")
        print(f"  2. Validate: python validate_questions.py {filename}")
        print(f"  3. Run evaluation: python automated_test_runner.py {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate TogoMCP evaluation questions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive question builder (default)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        metavar="N",
        help="Generate N questions automatically"
    )
    parser.add_argument(
        "--entity",
        help="Entity to generate questions for (gene, protein, compound)"
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Show all available templates"
    )
    
    args = parser.parse_args()
    
    generator = QuestionGenerator()
    
    # Show templates
    if args.template:
        generator.show_templates()
        return
    
    # Batch mode
    if args.batch or args.entity:
        entity = args.entity or "BRCA1"
        num = args.batch or 5
        generator.batch_generate(entity, num)
        generator._save_questions()
        return
    
    # Interactive mode (default)
    generator.interactive_mode()


if __name__ == "__main__":
    main()
