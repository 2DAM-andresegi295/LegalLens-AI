from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT_DIR / "dataset" / "source"
OUTPUT_DIR = ROOT_DIR / "dataset"

MAPPING = {
    "contrato_alquiler_legal.txt": "contrato_alquiler_legal.pdf",
    "contrato_alquiler_trampa.txt": "contrato_alquiler_trampa.pdf",
    "contrato_nda_legal.txt": "contrato_nda_legal.pdf",
    "contrato_nda_trampa.txt": "contrato_nda_trampa.pdf",
}


def build_pdf(source_path: Path, output_path: Path) -> None:
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    text_object = pdf.beginText(50, height - 50)
    text_object.setLeading(16)

    for line in source_path.read_text(encoding="utf-8").splitlines():
        if text_object.getY() < 60:
            pdf.drawText(text_object)
            pdf.showPage()
            text_object = pdf.beginText(50, height - 50)
            text_object.setLeading(16)
        text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.save()


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source_name, output_name in MAPPING.items():
        build_pdf(SOURCE_DIR / source_name, OUTPUT_DIR / output_name)
    print("Generación del dataset completada correctamente.")

