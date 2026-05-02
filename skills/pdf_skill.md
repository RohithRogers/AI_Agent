DESCRIPTION: This skill helps you to create stunning and beautiful pdfs.

# Creating PDF Files

## Tool of Choice: `reportlab` (Python)

Always use `reportlab`. Two modes — pick one based on complexity.

```bash
pip install reportlab --break-system-packages   # always include the flag
```

| Mode          | Use when                                      | API                  |
|---------------|-----------------------------------------------|----------------------|
| **Canvas**    | Precise positioning, custom layouts, drawings | `canvas.Canvas`      |
| **Platypus**  | Multi-page docs, flowing text, auto-layout    | `SimpleDocTemplate`  |

---

## Mode 1 — Canvas (precise control)

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

c = canvas.Canvas("/mnt/user-data/outputs/output.pdf", pagesize=A4)
W, H = A4  # 595 × 842 pts; origin is bottom-left

c.setFont("Helvetica-Bold", 24)
c.setFillColorRGB(0.1, 0.1, 0.2)
c.drawString(50, H - 80, "Report Title")

c.setStrokeColorRGB(0.2, 0.4, 0.8)
c.setLineWidth(2)
c.line(50, H - 90, W - 50, H - 90)

c.showPage()
c.save()
```

---

## Mode 2 — Platypus (flowing multi-page documents)

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

doc = SimpleDocTemplate("/mnt/user-data/outputs/output.pdf", pagesize=A4,
                        leftMargin=50, rightMargin=50, topMargin=60, bottomMargin=60)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("Section Title", styles["Heading1"]))
story.append(Spacer(1, 12))
story.append(Paragraph("Body text wraps automatically.", styles["Normal"]))
story.append(PageBreak())

data = [["Name", "Value"], ["Revenue", "$1.2M"], ["Growth", "24%"]]
t = Table(data, colWidths=[250, 200])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
]))
story.append(t)
doc.build(story)
```

---

## Common Additions

```python
from reportlab.platypus import Image
story.append(Image("chart.png", width=400, height=250))          # Platypus image
c.drawImage("logo.png", x=50, y=H-150, width=120, height=60)    # Canvas image

# Subscript / Superscript — NEVER use Unicode (₂ ⁰ render as black boxes)
story.append(Paragraph("H<sub>2</sub>O and x<super>2</super>", styles["Normal"]))
```

---

## Anti-Patterns

| Don't                                        | Do instead                                       |
|----------------------------------------------|--------------------------------------------------|
| Use Unicode sub/superscripts (₂ ⁰ ¹)         | Use `<sub>` / `<super>` tags in Paragraph        |
| Mix Canvas and Platypus in the same doc      | Pick one mode per document                       |
| Forget `c.showPage()` between Canvas pages   | Call it before starting a new page               |
| Hard-code pixel coords without knowing size  | A4 = 595 × 842 pts; Letter = 612 × 792 pts      |
