from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

doc = SimpleDocTemplate("AI_Transformers.pdf", pagesize=A4,
                        leftMargin=50, rightMargin=50, topMargin=60, bottomMargin=60)
styles = getSampleStyleSheet()
story = []

# Title
title_style = ParagraphStyle(
    'TitleStyle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.darkblue,
    alignment=1
)
story.append(Paragraph("AI: The Transformer Architecture", title_style))
story.append(Paragraph("An Overview of the Engine Behind Modern Generative AI", styles["Heading2"]))
story.append(Spacer(1, 24))

# Section 1
story.append(Paragraph("1. What is a Transformer?", styles["Heading3"]))
story.append(Paragraph(
    "Introduced by Google researchers in the 2017 paper 'Attention Is All You Need,' the Transformer is a deep learning architecture "
    "that relies entirely on a mechanism called Self-Attention. Unlike its predecessors (RNNs and LSTMs), which processed data sequentially, "
    "Transformers process entire sequences of data simultaneously, allowing for massive parallelization and faster training.",
    styles["Normal"]
))
story.append(Spacer(1, 12))

# Section 2
story.append(Paragraph("2. Core Components", styles["Heading3"]))
story.append(Paragraph("<b>Self-Attention Mechanism:</b> This is the heart of the model. It allows the AI to weigh the importance of different words in a sentence relative to one another, regardless of their distance.", styles["Normal"]))
story.append(Paragraph("<b>Positional Encoding:</b> Since Transformers process words in parallel, they have no inherent concept of order. Positional encoding adds 'tags' to the input data to give the model information about the sequence.", styles["Normal"]))
story.append(Paragraph("<b>Encoder-Decoder Structure:</b> The Encoder reads the input text and creates a numerical representation, and the Decoder takes that representation to generate the output sequence.", styles["Normal"]))
story.append(Spacer(1, 12))

# Section 3
story.append(Paragraph("3. Why are they a Breakthrough?", styles["Heading3"]))
story.append(Paragraph("<b>Scalability:</b> Because they process data in parallel, Transformers can be trained on massive datasets using thousands of GPUs.", styles["Normal"]))
story.append(Paragraph("<b>Contextual Understanding:</b> They excel at understanding long-range dependencies, making them far better at maintaining coherence in long documents.", styles["Normal"]))
story.append(Paragraph("<b>Transfer Learning:</b> Transformers allow for 'pre-training' on massive corpora, which can then be 'fine-tuned' for specific tasks with very little additional data.", styles["Normal"]))
story.append(Spacer(1, 12))

# Section 4
story.append(Paragraph("4. Impact on AI Today", styles["Heading3"]))
story.append(Paragraph("The Transformer architecture is the foundation for almost every modern AI advancement, including Large Language Models (GPT-4, Claude, Llama), Computer Vision (Vision Transformers), and Multimodal AI systems like DALL-E or Sora.", styles["Normal"]))

doc.build(story)
