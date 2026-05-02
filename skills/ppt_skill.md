DESCRIPTION: THis skills helps you to create beautiful and stunning presentations.(ppt files)

# Creating PowerPoint Files

## Tool of Choice: `pptxgenjs` (Node.js)

Always use `pptxgenjs`. Install once, then generate.

```bash
npm install pptxgenjs
```

## Minimal Working Example

```javascript
const pptxgen = require("pptxgenjs");
const prs = new pptxgen();
prs.layout = "LAYOUT_16x9"; // 10" × 5.625" — always use this unless told otherwise

const slide = prs.addSlide();
slide.addText("Hello World", { x: 1, y: 1, w: 8, h: 1, fontSize: 36, bold: true, color: "363636" });

prs.writeFile({ fileName: "output.pptx" });
```

## Core Elements

### Text
```javascript
slide.addText("Title", {
  x: 0.5, y: 0.3, w: 9, h: 0.8,
  fontSize: 32, bold: true, color: "1a1a2e", align: "center"
});
```

### Bullet List
```javascript
slide.addText([
  { text: "Point one",   options: { bullet: true, breakLine: true } },
  { text: "Point two",   options: { bullet: true, breakLine: true } },
  { text: "Point three", options: { bullet: true } },
], { x: 0.5, y: 1.5, w: 9, h: 3, fontSize: 20, color: "333333" });
```

### Shapes & Backgrounds
```javascript
// Filled rectangle (e.g. header bar)
slide.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 10, h: 1.2, fill: { color: "1a1a2e" } });

// Slide background color
slide.background = { color: "f5f5f5" };
```

### Images
```javascript
slide.addImage({ path: "logo.png", x: 8.5, y: 0.1, w: 1.2, h: 0.8 });
```

### Tables
```javascript
const rows = [
  [{ text: "Name", options: { bold: true } }, { text: "Value", options: { bold: true } }],
  ["Revenue", "$1.2M"],
  ["Growth",  "24%"],
];
slide.addTable(rows, { x: 1, y: 1.5, w: 8, colW: [4, 4], fontSize: 16 });
```

## Decision Table

| Slide type          | Key elements to add                              |
|---------------------|--------------------------------------------------|
| Title slide         | Large bold title + subtitle text + bg color      |
| Content slide       | Header bar shape + bullet text block             |
| Data / metrics      | `addTable` or individual stat text boxes         |
| Image-heavy slide   | `addImage` + minimal caption text               |
| Section divider     | Full-bleed background color + centered text      |

## Anti-Patterns

| Don't                                         | Do instead                                      |
|-----------------------------------------------|-------------------------------------------------|
| Use Unicode subscripts (₂, ⁰) in text         | Avoid — they render as boxes in most viewers    |
| Set `w`/`h` without checking slide bounds     | Slide is 10" × 5.625"; stay within those bounds |
| Use `letterSpacing` for character spacing     | Use `charSpacing` — `letterSpacing` is ignored  |
| Skip `breakLine: true` in bullet arrays       | Always set it on every item except the last     |

## Output

```javascript
// Always save to the outputs directory
prs.writeFile({ fileName: "/mnt/user-data/outputs/presentation.pptx" });
```
