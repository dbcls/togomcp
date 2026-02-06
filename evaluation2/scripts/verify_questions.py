#!/usr/bin/env python3
"""
Verification script for BioASQ benchmark questions
"""
import json
import os
from collections import Counter
from pathlib import Path

def verify_questions():
    base_path = Path("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions")
    
    # Find all question files
    question_files = sorted(base_path.glob("question_*.json"))
    
    total_questions = 0
    all_types = []
    all_ids = []
    databases_used = set()
    issues = []
    valid_types = {"yes_no", "factoid", "list", "summary"}
    
    print("=" * 70)
    print("BIOASQ BENCHMARK QUESTIONS VERIFICATION")
    print("=" * 70)
    
    # Load coverage tracker if exists
    coverage_tracker_path = base_path / "coverage_tracker.json"
    coverage_tracker = None
    if coverage_tracker_path.exists():
        try:
            with open(coverage_tracker_path, 'r') as f:
                coverage_tracker = json.load(f)
            print(f"\n✓ Coverage tracker found")
        except json.JSONDecodeError as e:
            print(f"\n❌ ERROR: coverage_tracker.json has invalid JSON: {e}")
    else:
        print(f"\n⚠️  WARNING: coverage_tracker.json not found")
    
    # Verify each question file
    for filepath in question_files:
        filename = filepath.name
        
        try:
            with open(filepath, 'r') as f:
                question = json.load(f)
        except FileNotFoundError:
            issues.append(f"{filename}: File not found!")
            continue
        except json.JSONDecodeError as e:
            issues.append(f"{filename}: Invalid JSON - {e}")
            continue
        
        print(f"\n{filename}:")
        
        # Verify required top-level fields
        required_fields = ['id', 'type', 'body', 'source_article', 'documents', 
                          'snippets', 'exact_answer', 'ideal_answer']
        missing_fields = [field for field in required_fields if field not in question]
        
        if missing_fields:
            print(f"  ❌ Missing required fields: {missing_fields}")
            issues.append(f"{filename}: Missing fields {missing_fields}")
        else:
            print(f"  ✓ All required fields present")
        
        # Verify question type
        q_type = question.get('type')
        if q_type not in valid_types:
            print(f"  ❌ Invalid type '{q_type}'. Must be one of: {valid_types}")
            issues.append(f"{filename}: Invalid type '{q_type}'")
        else:
            print(f"  ✓ Type: {q_type}")
            all_types.append(q_type)
        
        # Verify ID
        q_id = question.get('id')
        if q_id:
            all_ids.append(q_id)
            print(f"  ✓ ID: {q_id}")
        else:
            print(f"  ❌ Missing or empty ID")
            issues.append(f"{filename}: Missing or empty ID")
        
        # Verify body
        body = question.get('body')
        if body and isinstance(body, str) and len(body.strip()) > 0:
            print(f"  ✓ Body: {len(body)} characters")
        else:
            print(f"  ❌ Body is empty or invalid")
            issues.append(f"{filename}: Empty or invalid body")
        
        # Verify source_article structure
        source_article = question.get('source_article')
        if isinstance(source_article, dict):
            sa_required = ['pmid', 'title', 'url']
            sa_missing = [field for field in sa_required if field not in source_article]
            if sa_missing:
                print(f"  ❌ source_article missing: {sa_missing}")
                issues.append(f"{filename}: source_article missing {sa_missing}")
            else:
                print(f"  ✓ Source article: PMID {source_article.get('pmid')}")
        else:
            print(f"  ❌ source_article is not a dictionary")
            issues.append(f"{filename}: source_article invalid structure")
        
        # Verify documents array
        documents = question.get('documents')
        if isinstance(documents, list):
            print(f"  ✓ Documents: {len(documents)} articles")
            for i, doc in enumerate(documents):
                if not isinstance(doc, dict):
                    print(f"    ❌ Document {i+1} is not a dictionary")
                    issues.append(f"{filename}: Document {i+1} invalid structure")
                else:
                    doc_required = ['pmid', 'title', 'url']
                    doc_missing = [field for field in doc_required if field not in doc]
                    if doc_missing:
                        print(f"    ❌ Document {i+1} missing: {doc_missing}")
                        issues.append(f"{filename}: Document {i+1} missing {doc_missing}")
        else:
            print(f"  ❌ documents is not an array")
            issues.append(f"{filename}: documents not an array")
        
        # Verify snippets array
        snippets = question.get('snippets')
        if isinstance(snippets, list):
            print(f"  ✓ Snippets: {len(snippets)} text excerpts")
            for i, snippet in enumerate(snippets):
                if not isinstance(snippet, dict):
                    print(f"    ❌ Snippet {i+1} is not a dictionary")
                    issues.append(f"{filename}: Snippet {i+1} invalid structure")
                else:
                    snip_required = ['text', 'document', 'offsetInBeginSection', 'offsetInEndSection']
                    snip_missing = [field for field in snip_required if field not in snippet]
                    if snip_missing:
                        print(f"    ❌ Snippet {i+1} missing: {snip_missing}")
                        issues.append(f"{filename}: Snippet {i+1} missing {snip_missing}")
                    # Check if text contains complete sentences
                    text = snippet.get('text', '')
                    if text and not text.strip().endswith(('.', '!', '?', '"', "'")):
                        print(f"    ⚠️  Snippet {i+1} may not be complete sentence(s)")
        else:
            print(f"  ❌ snippets is not an array")
            issues.append(f"{filename}: snippets not an array")
        
        # Verify exact_answer based on type
        exact_answer = question.get('exact_answer')
        if q_type == 'yes_no':
            if exact_answer not in ['yes', 'no']:
                print(f"  ❌ exact_answer for yes_no must be 'yes' or 'no', got: {exact_answer}")
                issues.append(f"{filename}: Invalid yes_no exact_answer")
            else:
                print(f"  ✓ Exact answer: {exact_answer}")
        elif q_type == 'factoid':
            if isinstance(exact_answer, (str, list)):
                print(f"  ✓ Exact answer: {exact_answer}")
            else:
                print(f"  ❌ exact_answer for factoid must be string or list")
                issues.append(f"{filename}: Invalid factoid exact_answer type")
        elif q_type == 'list':
            if isinstance(exact_answer, list):
                print(f"  ✓ Exact answer: {len(exact_answer)} items")
            else:
                print(f"  ❌ exact_answer for list must be an array")
                issues.append(f"{filename}: Invalid list exact_answer type")
        elif q_type == 'summary':
            if exact_answer is None or exact_answer == "":
                print(f"  ✓ Exact answer: null (summary type)")
            else:
                print(f"  ⚠️  exact_answer for summary should be null or empty")
        
        # Verify ideal_answer
        ideal_answer = question.get('ideal_answer')
        if ideal_answer and isinstance(ideal_answer, str) and len(ideal_answer.strip()) > 0:
            print(f"  ✓ Ideal answer: {len(ideal_answer)} characters")
            # Check for meta-references that should be avoided
            meta_phrases = [
                'according to pubmed', 'research shows', 'studies indicate',
                'the literature suggests', 'based on research', 'according to sources',
                'research indicates', 'studies have shown'
            ]
            ideal_lower = ideal_answer.lower()
            found_meta = [phrase for phrase in meta_phrases if phrase in ideal_lower]
            if found_meta:
                print(f"  ⚠️  Ideal answer contains meta-references: {found_meta}")
        else:
            print(f"  ❌ ideal_answer is empty or invalid")
            issues.append(f"{filename}: Empty or invalid ideal_answer")
        
        total_questions += 1
    
    # Summary section
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"\n✓ Total Questions: {total_questions}")
    
    # Check progress toward 50 minimum
    if total_questions >= 50:
        print(f"  ✓ PASS: Minimum 50 questions met")
    else:
        print(f"  ⚠️  PROGRESS: {total_questions}/50 minimum questions")
    
    # Type distribution
    print(f"\nQuestion Type Distribution:")
    type_counts = Counter(all_types)
    for q_type in valid_types:
        count = type_counts.get(q_type, 0)
        status = "✓" if count >= 10 else "⚠️ "
        target = "(10 minimum)" if count < 10 else ""
        print(f"  {status} {q_type}: {count} {target}")
    
    # ID verification
    print(f"\nID Verification:")
    print(f"  Total unique IDs: {len(set(all_ids))}")
    
    if len(all_ids) == len(set(all_ids)):
        print(f"  ✓ PASS: No duplicate IDs")
    else:
        print(f"  ❌ FAIL: {len(all_ids) - len(set(all_ids))} duplicate IDs found")
        dupes = [id for id in all_ids if all_ids.count(id) > 1]
        print(f"  Duplicates: {set(dupes)}")
        issues.append(f"Duplicate IDs found: {set(dupes)}")
    
    # Coverage tracker verification
    if coverage_tracker:
        print(f"\nCoverage Tracker Verification:")
        tracker_total = coverage_tracker.get('total_questions', 0)
        if tracker_total == total_questions:
            print(f"  ✓ Tracker total matches actual: {tracker_total}")
        else:
            print(f"  ❌ Tracker total ({tracker_total}) != actual ({total_questions})")
            issues.append(f"Coverage tracker mismatch: tracker={tracker_total}, actual={total_questions}")
        
        # Check type counts
        by_type = coverage_tracker.get('by_type', {})
        for q_type, count in type_counts.items():
            tracker_count = by_type.get(q_type, 0)
            if tracker_count != count:
                print(f"  ❌ {q_type}: tracker={tracker_count}, actual={count}")
                issues.append(f"Type count mismatch for {q_type}")
        
        # Database coverage
        by_database = coverage_tracker.get('by_database', {})
        uncovered = coverage_tracker.get('uncovered_databases', [])
        
        print(f"\nDatabase Coverage:")
        print(f"  Databases used: {len(by_database)}")
        print(f"  Uncovered databases: {len(uncovered)}")
        
        if by_database:
            print(f"\n  Used databases:")
            for db, questions in sorted(by_database.items()):
                print(f"    • {db}: {len(questions)} question(s)")
        
        if uncovered:
            print(f"\n  ⚠️  Uncovered databases ({len(uncovered)}):")
            for db in sorted(uncovered):
                print(f"    • {db}")
    
    # Issues summary
    if issues:
        print(f"\n{'=' * 70}")
        print(f"ISSUES FOUND ({len(issues)}):")
        print(f"{'=' * 70}")
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print(f"\n✓ No issues found!")
    
    print(f"\n{'=' * 70}")
    print("VERIFICATION COMPLETE")
    print(f"{'=' * 70}\n")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = verify_questions()
    exit(0 if success else 1)
