"""Matched local diagram rendering; no task state is available to the renderer."""

from io import BytesIO

from PIL import Image, ImageDraw

from .schemas import Diagram, Feature, Features

WIDTH, HEIGHT = 640, 360
INK = (35, 43, 53)
PAPER = (248, 247, 242)


def render(spec: Diagram) -> bytes:
    """Render a fixed-layout PNG; all conditions share size, palette, and shapes."""
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    for x in (110, 530):
        draw.ellipse((x - 18, 55, x + 18, 91), outline=INK, width=3)
        draw.line((x, 92, x, 145), fill=INK, width=3)
        draw.line((x - 28, 112, x + 28, 112), fill=INK, width=3)
    draw.rectangle((270, 175, 370, 270), outline=INK, width=3)
    draw.rectangle((455, 220, 605, 305), outline=INK, width=3)
    # Equal-length diagonals differ only in orientation: discrepancy vs agreement.
    draw.line((300, 205, 340, 245 if spec.discrepancy else 205), fill=INK, width=4)
    draw.line((300, 245, 340, 205 if spec.discrepancy else 245), fill=INK, width=4)
    draw.line((485, 245, 575, 245 if spec.presented_complete else 280), fill=INK, width=4)
    draw.line((485, 280, 575, 280 if spec.presented_complete else 245), fill=INK, width=4)
    # Visibility is one rotated barrier per path; total ink length stays fixed.
    for x, visible in ((205, spec.agent_can_see), (435, spec.reviewer_can_see)):
        draw.line((110 if x == 205 else 530, 145, 320, 180), fill=INK, width=2)
        if visible:
            draw.line((x - 12, 174, x + 12, 174), fill=INK, width=4)
        else:
            draw.line((x, 162, x, 186), fill=INK, width=4)
    if spec.relationship != "scene":
        draw.text((80, 25), "Agent", fill=INK)
        draw.text((500, 25), "Reviewer", fill=INK)
        draw.text((280, 280), "Artifact", fill=INK)
        draw.text((500, 315), "Report", fill=INK)
        draw.text(
            (20, 335),
            "Cross = discrepancy; parallel lines = agreement; vertical bar = blocked view",
            fill=INK,
        )
    output = BytesIO()
    image.save(output, format="PNG")  # No labels, IDs, model names, or metadata.
    return output.getvalue()


def mock_extract(data: bytes) -> Features:
    """Read known fixture pixels, not manifests; this is not general visual understanding."""
    image = Image.open(BytesIO(data)).convert("RGB")
    cross = image.getpixel((320, 225)) == INK
    report_cross = image.getpixel((530, 262)) == INK
    blocked = image.getpixel((435, 163)) == INK
    return Features(
        items=[
            Feature(
                name="actors_objects",
                value="Two people, artifact, report",
                evidence="People near (110,100) and (530,100); boxes below",
            ),
            Feature(
                name="barriers",
                value="reviewer blocked" if blocked else "reviewer open",
                evidence="Bar orientation at (435,174)",
            ),
            Feature(
                name="information_access",
                value="reviewer blocked" if blocked else "reviewer open",
                evidence="Vertical or horizontal bar at (435,174)",
            ),
            Feature(
                name="event_relationships",
                value="Two lines link people to artifact",
                evidence="Lines between y=145 and y=180",
            ),
            Feature(
                name="viewpoints",
                value="unclear",
                evidence="Lines alone do not establish knowledge",
                unclear=True,
            ),
            Feature(
                name="outcome_presentation",
                value="mismatch" if cross and not report_cross else "no visible mismatch",
                evidence="Compare artifact diagonals at (320,225) with report diagonals at (530,262)",
            ),
        ]
    )


def matched_options() -> list[Diagram]:
    """Change only reviewer visibility; balance order separately in the runner."""
    base = Diagram(
        discrepancy=True,
        agent_can_see=True,
        reviewer_can_see=True,
        presented_complete=True,
        relationship="viewpoints",
    )
    return [base, base.model_copy(update={"reviewer_can_see": False})]
