"""
Document Analyzer

Analyzes text documents for various metrics like word count, line count,
sentence count, paragraph count, and more.

This is a "pseudo-executor" that doesn't run external code but analyzes
document content. It follows the executor pattern for consistency.
"""

import re
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path

from ctcore.security import safe_regex_findall, RegexTimeoutError

from ctexec import BaseExecutor, ExecutorResult
from ctexec.runtime import RuntimeType


@dataclass
class TextMetrics:
    """Metrics extracted from a text document."""

    # Basic counts
    line_count: int = 0
    word_count: int = 0
    char_count: int = 0
    char_count_no_spaces: int = 0

    # Structure counts
    paragraph_count: int = 0
    sentence_count: int = 0

    # Markdown-specific
    heading_count: int = 0
    headings: List[Dict[str, any]] = field(default_factory=list)
    list_item_count: int = 0
    link_count: int = 0
    image_count: int = 0
    code_block_count: int = 0

    # Quality metrics
    unique_word_count: int = 0
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    avg_words_per_paragraph: float = 0.0

    # Content
    words: List[str] = field(default_factory=list)
    unique_words: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary (excluding large lists)."""
        return {
            "line_count": self.line_count,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "char_count_no_spaces": self.char_count_no_spaces,
            "paragraph_count": self.paragraph_count,
            "sentence_count": self.sentence_count,
            "heading_count": self.heading_count,
            "list_item_count": self.list_item_count,
            "link_count": self.link_count,
            "image_count": self.image_count,
            "code_block_count": self.code_block_count,
            "unique_word_count": self.unique_word_count,
            "avg_word_length": round(self.avg_word_length, 2),
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "avg_words_per_paragraph": round(self.avg_words_per_paragraph, 2),
        }


class DocumentAnalyzer(BaseExecutor):
    """
    Analyzes text documents for various metrics.

    This is a special "executor" that doesn't run external code but
    analyzes document content. It follows the executor pattern for
    consistency with other testers.
    """

    language = "document"

    # Sentence-ending punctuation
    SENTENCE_ENDINGS = re.compile(r'[.!?]+')

    # Word pattern (letters, numbers, hyphens, apostrophes)
    WORD_PATTERN = re.compile(r"[\w''-]+", re.UNICODE)

    # Markdown patterns
    MD_HEADING = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    MD_LIST_ITEM = re.compile(r'^\s*[-*+]\s+|^\s*\d+\.\s+', re.MULTILINE)
    MD_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    MD_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    MD_CODE_BLOCK = re.compile(r'```[\s\S]*?```|`[^`]+`', re.MULTILINE)

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        check_runtime: bool = False,  # No external runtime needed
    ):
        """
        Initialize the document analyzer.

        Args:
            working_dir: Working directory for file paths
            timeout: Not used (no execution)
            check_runtime: Not used (no external runtime)
        """
        super().__init__(working_dir, timeout, use_safe_env=False, check_runtime=False)
        self._content: Optional[str] = None
        self._is_markdown: bool = False

    @classmethod
    def check_installed(cls, binary: Optional[str] = None) -> Tuple[bool, str]:
        """Document analyzer is always available (built-in)."""
        return True, "Built-in text analyzer"

    @classmethod
    def from_file(cls, file_path: str) -> "DocumentAnalyzer":
        """
        Create a DocumentAnalyzer from a file path.

        Args:
            file_path: Path to the document file

        Returns:
            DocumentAnalyzer instance with content loaded
        """
        analyzer = cls(working_dir=os.path.dirname(file_path))
        path = Path(file_path)
        analyzer._is_markdown = path.suffix.lower() in ('.md', '.markdown', '.mdown')

        with open(file_path, 'r', encoding='utf-8') as f:
            analyzer._content = f.read()

        return analyzer

    def execute(
        self,
        source_path: str,
        variables_to_extract: Optional[List[str]] = None,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_data: Optional[str] = None,
    ) -> ExecutorResult:
        """
        Analyze a document and return metrics.

        Args:
            source_path: Path to the document file
            variables_to_extract: Metrics to extract (if None, extracts all)
            setup_code: Not used
            teardown_code: Not used
            input_data: Not used

        Returns:
            ExecutorResult with metrics in the namespace
        """
        # Resolve path
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.working_dir, source_path)

        if not os.path.exists(source_path):
            return ExecutorResult(
                success=False,
                error_message=f"File not found: {source_path}",
                error_type="FileNotFoundError",
            )

        try:
            # Load content
            path = Path(source_path)
            self._is_markdown = path.suffix.lower() in ('.md', '.markdown', '.mdown')

            with open(source_path, 'r', encoding='utf-8') as f:
                self._content = f.read()

            # Analyze
            metrics = self.analyze()

            # Convert to namespace
            namespace = metrics.to_dict()

            # Filter to requested variables if specified
            if variables_to_extract:
                namespace = {k: v for k, v in namespace.items() if k in variables_to_extract}

            return ExecutorResult(
                success=True,
                namespace=namespace,
            )

        except Exception as e:
            return ExecutorResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
            )

    def analyze(self) -> TextMetrics:
        """
        Analyze the loaded text and return metrics.

        Returns:
            TextMetrics with all computed metrics
        """
        if self._content is None:
            return TextMetrics()

        metrics = TextMetrics()

        # Basic counts
        lines = self._content.split('\n')
        metrics.line_count = len(lines)
        metrics.char_count = len(self._content)
        metrics.char_count_no_spaces = len(
            self._content.replace(' ', '').replace('\t', '').replace('\n', '')
        )

        # Word extraction
        words = self.WORD_PATTERN.findall(self._content.lower())
        metrics.words = words
        metrics.word_count = len(words)
        metrics.unique_words = set(words)
        metrics.unique_word_count = len(metrics.unique_words)

        # Average word length
        if metrics.word_count > 0:
            total_word_chars = sum(len(w) for w in words)
            metrics.avg_word_length = total_word_chars / metrics.word_count

        # Paragraph count (blocks separated by blank lines)
        paragraphs = re.split(r'\n\s*\n', self._content.strip())
        paragraphs = [p for p in paragraphs if p.strip()]
        metrics.paragraph_count = len(paragraphs)

        # Average words per paragraph
        if metrics.paragraph_count > 0:
            metrics.avg_words_per_paragraph = metrics.word_count / metrics.paragraph_count

        # Sentence count
        text_for_sentences = self._content
        if self._is_markdown:
            text_for_sentences = self.MD_CODE_BLOCK.sub('', text_for_sentences)

        sentences = self.SENTENCE_ENDINGS.split(text_for_sentences)
        sentences = [s for s in sentences if s.strip()]
        metrics.sentence_count = len(sentences)

        # Average sentence length
        if metrics.sentence_count > 0:
            metrics.avg_sentence_length = metrics.word_count / metrics.sentence_count

        # Markdown-specific
        if self._is_markdown:
            self._analyze_markdown(metrics)

        return metrics

    def _analyze_markdown(self, metrics: TextMetrics):
        """Analyze markdown-specific features."""
        # Headings
        for match in self.MD_HEADING.finditer(self._content):
            level = len(match.group(1))
            text = match.group(2).strip()
            line_num = self._content[:match.start()].count('\n') + 1
            metrics.headings.append({
                'level': level,
                'text': text,
                'line': line_num
            })
        metrics.heading_count = len(metrics.headings)

        # List items
        metrics.list_item_count = len(self.MD_LIST_ITEM.findall(self._content))

        # Links (excluding images)
        all_links = self.MD_LINK.findall(self._content)
        image_texts = [m[0] for m in self.MD_IMAGE.findall(self._content)]
        metrics.link_count = len([l for l in all_links if l[0] not in image_texts])

        # Images
        metrics.image_count = len(self.MD_IMAGE.findall(self._content))

        # Code blocks
        metrics.code_block_count = len(re.findall(r'```', self._content)) // 2
        metrics.code_block_count += len(re.findall(r'`[^`]+`', self._content))

    def has_keyword(self, keyword: str, case_sensitive: bool = False) -> bool:
        """Check if a keyword exists in the text."""
        if self._content is None:
            return False
        if case_sensitive:
            return keyword in self._content
        return keyword.lower() in self._content.lower()

    def count_keyword(self, keyword: str, case_sensitive: bool = False) -> int:
        """Count occurrences of a keyword."""
        if self._content is None:
            return 0
        if case_sensitive:
            return self._content.count(keyword)
        return self._content.lower().count(keyword.lower())

    def has_section(self, section_name: str, level: Optional[int] = None) -> bool:
        """Check if a markdown heading/section exists."""
        metrics = self.analyze()
        section_lower = section_name.lower()

        for heading in metrics.headings:
            if section_lower in heading['text'].lower():
                if level is None or heading['level'] == level:
                    return True
        return False

    def matches_pattern(self, pattern: str, flags: int = 0) -> List[str]:
        """
        Find all matches of a regex pattern in the text.

        Uses safe_regex_findall to prevent ReDoS from user-supplied patterns.

        Args:
            pattern: Regular expression pattern
            flags: re module flags (e.g., re.IGNORECASE)

        Returns:
            List of matched strings
        """
        if self._content is None:
            return []
        return safe_regex_findall(pattern, self._content, flags)


def check_document_installed() -> Tuple[bool, str]:
    """Document analyzer is always available."""
    return DocumentAnalyzer.check_installed()


# Alias for backward compatibility
TextAnalyzer = DocumentAnalyzer


def analyze_file(file_path: str) -> TextMetrics:
    """
    Convenience function to analyze a file.

    Args:
        file_path: Path to the file

    Returns:
        TextMetrics with analysis results
    """
    analyzer = DocumentAnalyzer(working_dir=os.path.dirname(file_path))
    result = analyzer.execute(file_path)
    if result.success:
        # Return full metrics
        analyzer._content  # Ensure content is loaded
        return analyzer.analyze()
    raise RuntimeError(result.error_message)
