"""Tests for togo_mcp.ncbi_tools module."""


from togo_mcp.ncbi_tools import _validate_query_field_tags


class TestValidateQueryFieldTags:
    """Tests for _validate_query_field_tags validation logic."""

    # --- Critical database without field tags ---

    def test_critical_db_no_tags_has_issues(self) -> None:
        """A query without field tags on a critical database should flag issues."""
        result = _validate_query_field_tags("BRCA1", "gene")
        assert result["has_issues"] is True
        assert result["is_critical"] is True
        assert result["has_field_tags"] is False

    def test_critical_db_with_proper_tags_no_issues(self) -> None:
        """A properly tagged query on a critical database should pass."""
        result = _validate_query_field_tags("BRCA1[Gene Name] AND Homo sapiens[Organism]", "gene")
        assert result["has_issues"] is False
        assert result["has_field_tags"] is True

    # --- Non-critical database ---

    def test_non_critical_db_no_tags_no_critical_flag(self) -> None:
        """A non-critical database without tags should not flag is_critical."""
        result = _validate_query_field_tags("asthma", "mesh")
        assert result["is_critical"] is False

    def test_non_critical_db_with_tags(self) -> None:
        """A non-critical database with tags should pass cleanly."""
        result = _validate_query_field_tags("asthma[MeSH Terms]", "mesh")
        assert result["has_issues"] is False
        assert result["has_field_tags"] is True

    # --- Organism detection ---

    def test_organism_term_without_tag(self) -> None:
        """Organism terms like 'human' without [Organism] should be flagged."""
        result = _validate_query_field_tags("human BRCA1", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "human" in issues_text.lower()

    def test_organism_term_with_tag(self) -> None:
        """Organism terms with [Organism] tag should not trigger organism warning."""
        result = _validate_query_field_tags("Homo sapiens[Organism] AND BRCA1[Gene Name]", "gene")
        organism_issues = [i for i in result["issues"] if "Organism" in i]
        assert len(organism_issues) == 0

    def test_mouse_organism_detection(self) -> None:
        """The term 'mouse' should be detected as an organism term."""
        result = _validate_query_field_tags("mouse TP53", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "mouse" in issues_text.lower()

    # --- Gene symbol detection ---

    def test_gene_symbol_detection_without_tag(self) -> None:
        """Uppercase potential gene symbols without [Gene Name] should be flagged on gene db."""
        result = _validate_query_field_tags("BRCA1", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "Gene Name" in issues_text

    def test_gene_symbol_not_flagged_on_non_gene_db(self) -> None:
        """Gene symbol detection should not trigger on non-gene databases."""
        result = _validate_query_field_tags("BRCA1", "pubmed")
        gene_issues = [i for i in result["issues"] if "Gene Name" in i]
        assert len(gene_issues) == 0

    # --- Unknown database ---

    def test_unknown_database(self) -> None:
        """An unknown database should not crash and should return minimal results."""
        result = _validate_query_field_tags("test query", "unknown_db")
        assert result["is_critical"] is False
        assert isinstance(result["issues"], list)
