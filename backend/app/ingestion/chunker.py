import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import tiktoken

from backend.app.ingestion.parser import ParsedBlock, ParsedDocument


@dataclass
class DocumentChunkData:
    chunk_index: int
    page_number: int
    section_title: str
    content: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """
    Chunker semântico com janela deslizante de ~600 tokens e overlap de 100 tokens.
    Preserva integridade de tabelas em Markdown e fronteiras de sentenças.
    """

    KNOWN_METRICS = [
        "ROAS", "CAC", "CTR", "CPM", "CPC", "CPL", "CPA",
        "LTV", "ROI", "CONVERSÕES", "CONVERSOES", "INVESTIMENTO",
        "RECEITA", "IMPRESSÕES", "IMPRESSOES", "CLIQUES", "TAXA DE CONVERSÃO"
    ]

    def __init__(
        self,
        target_tokens: int = 600,
        overlap_tokens: int = 100,
        encoding_name: str = "cl100k_base",
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _detect_metrics(self, text: str) -> List[str]:
        upper_text = text.upper()
        found = []
        for metric in self.KNOWN_METRICS:
            # Word boundary regex
            if re.search(r"\b" + re.escape(metric) + r"\b", upper_text):
                found.append(metric)
        return sorted(list(set(found)))

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[DocumentChunkData]:
        chunks: List[DocumentChunkData] = []
        current_tokens: List[str] = []
        current_page = 1
        current_section = "Introdução"
        has_table_in_chunk = False
        chunk_idx = 0

        for block in parsed_doc.blocks:
            if block.section_title:
                current_section = block.section_title
            current_page = block.page_number

            # Se o bloco for uma tabela
            if block.block_type == "table":
                table_text = f"\n### Tabela: {current_section}\n{block.content}\n"
                table_token_count = self.count_tokens(table_text)

                # Se a adição da tabela estourar o limite e já tivermos texto acumulado, fecha o chunk atual
                if current_tokens and (self.count_tokens(" ".join(current_tokens)) + table_token_count > self.target_tokens):
                    chunk_content = " ".join(current_tokens).strip()
                    if chunk_content:
                        chunks.append(
                            DocumentChunkData(
                                chunk_index=chunk_idx,
                                page_number=current_page,
                                section_title=current_section,
                                content=chunk_content,
                                token_count=self.count_tokens(chunk_content),
                                metadata={
                                    "has_table": has_table_in_chunk,
                                    "metrics_mentioned": self._detect_metrics(chunk_content),
                                },
                            )
                        )
                        chunk_idx += 1
                    current_tokens = []
                    has_table_in_chunk = False

                # Adiciona a tabela inteira como chunk dedicado ou inicia com ela
                if table_token_count > (self.target_tokens // 2):
                    chunks.append(
                        DocumentChunkData(
                            chunk_index=chunk_idx,
                            page_number=current_page,
                            section_title=current_section,
                            content=table_text.strip(),
                            token_count=table_token_count,
                            metadata={
                                "has_table": True,
                                "metrics_mentioned": self._detect_metrics(table_text),
                            },
                        )
                    )
                    chunk_idx += 1
                    current_tokens = []
                    has_table_in_chunk = False
                else:
                    current_tokens.append(table_text.strip())
                    has_table_in_chunk = True
                continue

            # Para blocos normais (parágrafos e títulos)
            text_piece = block.content
            if block.block_type == "heading":
                text_piece = f"\n## {text_piece}\n"

            # Divide parágrafo em sentenças para não quebrar no meio de uma frase
            sentences = re.split(r"(?<=[.!?])\s+", text_piece)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                test_combined = " ".join(current_tokens + [sentence])
                if self.count_tokens(test_combined) > self.target_tokens and current_tokens:
                    # Finaliza chunk atual
                    chunk_content = " ".join(current_tokens).strip()
                    chunks.append(
                        DocumentChunkData(
                            chunk_index=chunk_idx,
                            page_number=current_page,
                            section_title=current_section,
                            content=chunk_content,
                            token_count=self.count_tokens(chunk_content),
                            metadata={
                                "has_table": has_table_in_chunk,
                                "metrics_mentioned": self._detect_metrics(chunk_content),
                            },
                        )
                    )
                    chunk_idx += 1

                    # Calcula overlap sem quebrar tabelas
                    overlap_words = " ".join(current_tokens).split()
                    overlap_slice = overlap_words[-min(len(overlap_words), 50):]
                    current_tokens = [" ".join(overlap_slice), sentence]
                    has_table_in_chunk = False
                else:
                    current_tokens.append(sentence)

        # Fecha o último chunk se houver conteúdo restante
        if current_tokens:
            chunk_content = " ".join(current_tokens).strip()
            if chunk_content:
                chunks.append(
                    DocumentChunkData(
                        chunk_index=chunk_idx,
                        page_number=current_page,
                        section_title=current_section,
                        content=chunk_content,
                        token_count=self.count_tokens(chunk_content),
                        metadata={
                            "has_table": has_table_in_chunk,
                            "metrics_mentioned": self._detect_metrics(chunk_content),
                        },
                    )
                )

        return chunks
