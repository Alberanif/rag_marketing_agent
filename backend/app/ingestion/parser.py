import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF


@dataclass
class ParsedBlock:
    block_type: str  # "heading" | "paragraph" | "table"
    content: str
    page_number: int
    section_title: Optional[str] = None
    level: Optional[int] = None  # 1 for H1, 2 for H2
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    filename: str
    total_pages: int
    blocks: List[ParsedBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFParser:
    """
    Parser avançado de relatórios em PDF usando PyMuPDF (fitz).
    Preserva tabelas em Markdown e infere hierarquia de títulos por tamanho/peso de fonte.
    """

    def __init__(self, heading_threshold_factor: float = 1.25):
        self.heading_threshold_factor = heading_threshold_factor

    def parse_pdf(self, file_content: bytes, filename: str) -> ParsedDocument:
        doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(doc)

        # 1. Primeira passada para calcular mediana global de tamanho de fonte
        font_sizes: List[float] = []
        for page in doc:
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:  # Bloco de texto
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                font_sizes.append(round(span.get("size", 10.0), 1))

        body_font_size = statistics.median(font_sizes) if font_sizes else 11.0

        all_blocks: List[ParsedBlock] = []
        current_section = "Introdução"

        # 2. Segunda passada para extração estruturada página por página
        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1

            # Detecta tabelas na página
            table_bboxes = []
            extracted_tables: List[ParsedBlock] = []
            try:
                tables = page.find_tables()
                if tables and tables.tables:
                    for tab in tables.tables:
                        markdown_table = self._table_to_markdown(tab)
                        if markdown_table:
                            table_bboxes.append(tab.bbox)
                            extracted_tables.append(
                                ParsedBlock(
                                    block_type="table",
                                    content=markdown_table,
                                    page_number=page_num,
                                    section_title=current_section,
                                    metadata={
                                        "has_table": True,
                                        "rows": tab.row_count,
                                        "cols": tab.col_count,
                                        "bbox": list(tab.bbox),
                                    },
                                )
                            )
            except Exception:
                # Fallback caso a detecção tabular falhe em PDFs específicos
                table_bboxes = []

            # Extração de blocos de texto ordenados por coordenadas verticais (y0)
            page_dict = page.get_text("dict")
            text_blocks = [
                b for b in page_dict.get("blocks", []) if b.get("type") == 0
            ]
            text_blocks.sort(key=lambda b: (b.get("bbox", [0, 0])[1], b.get("bbox", [0, 0])[0]))

            for b in text_blocks:
                bbox = b.get("bbox", [0, 0, 0, 0])
                # Ignora blocos que estão completamente dentro de uma tabela já extraída
                if self._is_inside_tables(bbox, table_bboxes):
                    continue

                block_text_lines: List[str] = []
                max_span_size = 0.0
                is_bold = False

                for line in b.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        span_size = span.get("size", 0.0)
                        if span_size > max_span_size:
                            max_span_size = span_size
                        # flags & 2 indica negrito
                        if span.get("flags", 0) & 2 or "bold" in span.get("font", "").lower():
                            is_bold = True
                    clean_line = line_text.strip()
                    if clean_line:
                        block_text_lines.append(clean_line)

                block_text = " ".join(block_text_lines).strip()
                if not block_text:
                    continue

                # Determina se é título
                is_heading = (
                    max_span_size >= body_font_size * self.heading_threshold_factor
                    or (is_bold and len(block_text) < 120 and not block_text.endswith("."))
                )

                if is_heading and len(block_text) < 150:
                    current_section = block_text
                    level = 1 if max_span_size >= body_font_size * 1.5 else 2
                    all_blocks.append(
                        ParsedBlock(
                            block_type="heading",
                            content=block_text,
                            page_number=page_num,
                            section_title=current_section,
                            level=level,
                            metadata={"font_size": max_span_size, "is_bold": is_bold},
                        )
                    )
                else:
                    all_blocks.append(
                        ParsedBlock(
                            block_type="paragraph",
                            content=block_text,
                            page_number=page_num,
                            section_title=current_section,
                            metadata={"font_size": max_span_size},
                        )
                    )

            # Anexa as tabelas extraídas da página
            all_blocks.extend(extracted_tables)

        doc.close()
        return ParsedDocument(
            filename=filename,
            total_pages=total_pages,
            blocks=all_blocks,
            metadata={"median_font_size": body_font_size},
        )

    def _table_to_markdown(self, tab) -> Optional[str]:
        data = tab.extract()
        if not data or len(data) < 2:
            return None

        # Normaliza células vazias e quebras de linha
        headers = [str(c or "").strip().replace("\n", " ") for c in data[0]]
        if not any(headers):
            return None

        md_lines = []
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in data[1:]:
            cells = [str(c or "").strip().replace("\n", " ") for c in row]
            # Ajusta tamanho para bater com headers
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            md_lines.append("| " + " | ".join(cells[: len(headers)]) + " |")

        return "\n".join(md_lines)

    def _is_inside_tables(self, bbox: List[float], table_bboxes: List[List[float]]) -> bool:
        bx0, by0, bx1, by1 = bbox
        for tx0, ty0, tx1, ty1 in table_bboxes:
            # Tolerância de 5 pixels
            if bx0 >= tx0 - 5 and by0 >= ty0 - 5 and bx1 <= tx1 + 5 and by1 <= ty1 + 5:
                return True
        return False
