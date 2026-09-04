"""PDF case-report export using fpdf2 — pure Python, no system-level
Cairo/Pango dependency. Builds an actual laid-out document straight from
the FraudCase (the same inputs ReportGenerator._build_markdown uses),
not a rendering of the markdown report text.

The layout deliberately reuses FraudLens's own visual identity rather
than a generic report template: the graphite/cobalt palette and risk-tone
colors are the exact values from frontend/app/globals.css (light-theme
values — this is a printed/static document, no dark mode), and Courier
is used for identifiers/scores/amounts, Helvetica for everything else,
mirroring the frontend's own "monospace reserved for identifiers and
numeric evidence" typographic rule (see frontend/DESIGN-AUDIT.md).

Amounts are written as "Rs." rather than the ₹ glyph, and any other
character outside fpdf2's core-font encoding is replaced defensively:
see _safe()'s docstring below.
"""

from __future__ import annotations

from typing import Optional

from fpdf import FPDF
from fpdf.enums import MethodReturnValue, XPos, YPos

from fraudlens.core.compliance.regulatory_matrix import get_regulatory_context
from fraudlens.core.privacy import mask_identifier, mask_ip
from fraudlens.models.schemas import AnalystDecision, FraudCase

# ── Palette — exact values from frontend/app/globals.css's light theme.
# Keep these two files in sync if the frontend palette ever changes. ───────

_GRAPHITE = (28, 32, 48)
_GRAPHITE_FOREGROUND = (183, 189, 208)
_COBALT = (53, 56, 205)
_FOREGROUND = (23, 27, 44)
_MUTED = (98, 106, 128)
_BORDER = (223, 226, 236)
_CANVAS = (243, 244, 248)
_WHITE = (255, 255, 255)

# decision -> (fg, bg), matching frontend/lib/risk.ts's DECISION_TONE
# exactly. Risk colors stay reserved strictly for risk states, per this
# project's own design rule — nothing else in this document uses them.
_RISK_TONES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "clear": ((31, 138, 76), (231, 246, 236)),
    "review": ((181, 117, 10), (251, 240, 221)),
    "block": ((194, 59, 34), (252, 235, 231)),
    "block_and_report": ((156, 28, 28), (251, 226, 226)),
}

_DECISION_LABEL = {
    "clear": "CLEAR",
    "review": "REVIEW",
    "block": "BLOCK",
    "block_and_report": "BLOCK & ESCALATE",
}
_DEFAULT_TONE = ((98, 106, 128), (243, 244, 248))  # unknown decision -> muted/canvas

_PAGE_WIDTH_MM = 210.0
_MARGIN_MM = 15.0
_CONTENT_WIDTH_MM = _PAGE_WIDTH_MM - 2 * _MARGIN_MM
_MASTHEAD_H_MM = 14.0


def _safe(text: str) -> str:
    """fpdf2's core Helvetica/Courier fonts only support what their
    configured encoding maps to. cp1252 (set below) covers the bullet/
    dash/quote characters this app's masked IDs and copy actually use.
    The ₹ symbol isn't in cp1252 either — agent-generated reason strings
    (e.g. rule_agent's "Amount ₹342,829.13...") contain it verbatim, so
    it's rewritten to "Rs." to match how amounts are written everywhere
    else in this PDF, rather than falling through to the generic
    replacement below and rendering as a bare "?". Anything still
    outside cp1252 after that is replaced rather than raising, since this
    renders arbitrary reason/evidence-summary text no one has pre-vetted
    for font support."""
    text = text.replace("₹", "Rs. ")
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _tone_for(decision: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    return _RISK_TONES.get(decision, _DEFAULT_TONE)


def _label_for(decision: str) -> str:
    return _DECISION_LABEL.get(decision, decision.replace("_", " ").upper())


class _CaseReportPDF(FPDF):
    """FPDF subclass carrying FraudLens's own masthead/footer and the
    layout primitives the report is built from below."""

    def __init__(self, *args, case_id: str = "", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.core_fonts_encoding = "cp1252"
        self._case_id = case_id
        self.alias_nb_pages()

    # ── Running header/footer ───────────────────────────────────────

    def header(self) -> None:
        self.set_fill_color(*_GRAPHITE)
        self.rect(0, 0, _PAGE_WIDTH_MM, _MASTHEAD_H_MM, style="F")

        self.set_xy(_MARGIN_MM, 3)
        self.set_font("Courier", "B", 13)
        self.set_text_color(*_WHITE)
        self.cell(100, 6, "FraudLens")

        self.set_xy(_MARGIN_MM, 9)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*_GRAPHITE_FOREGROUND)
        self.cell(100, 4, "FRAUD INTELLIGENCE & REGULATORY CASEOPS")

        case_text = _safe(self._case_id)
        self.set_font("Courier", "", 8)
        self.set_text_color(*_GRAPHITE_FOREGROUND)
        w = self.get_string_width(case_text)
        self.set_xy(_PAGE_WIDTH_MM - _MARGIN_MM - w, 5.5)
        self.cell(w, 5, case_text, align="R")

        self.set_y(_MASTHEAD_H_MM + 6)
        self.set_text_color(*_FOREGROUND)

    def footer(self) -> None:
        self.set_y(-16)
        self.set_draw_color(*_BORDER)
        self.set_line_width(0.2)
        self.line(_MARGIN_MM, self.get_y(), _PAGE_WIDTH_MM - _MARGIN_MM, self.get_y())

        self.set_xy(_MARGIN_MM, self.get_y() + 2)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED)
        self.cell(
            130,
            5,
            "FraudLens - Confidential Investigation Report. A qualified analyst "
            "must review the evidence before any action is taken.",
        )

        page_text = f"Page {self.page_no()} of {{nb}}"
        self.set_font("Courier", "", 7)
        w = self.get_string_width(f"Page {self.page_no()} of 00")
        self.set_xy(_PAGE_WIDTH_MM - _MARGIN_MM - w, self.get_y())
        self.cell(w, 5, page_text, align="R")

    # ── Layout primitives ────────────────────────────────────────────

    def ensure_space(self, needed_h: float) -> None:
        """Manually-drawn fill/rect blocks below don't trigger fpdf2's
        auto-page-break the way text-writing calls do — this covers the
        gap for every block that draws a rect before writing into it."""
        if self.get_y() + needed_h > self.page_break_trigger:
            self.add_page()

    def decision_banner(
        self,
        engine_label: str,
        analyst_label: str,
        tone_fg: tuple[int, int, int],
        tone_bg: tuple[int, int, int],
        txn_id: str,
        final_score: float,
        confidence: float,
    ) -> None:
        h = 20.0
        self.ensure_space(h)
        y0 = self.get_y()

        self.set_fill_color(*tone_bg)
        self.rect(_MARGIN_MM, y0, _CONTENT_WIDTH_MM, h, style="F")
        self.set_fill_color(*tone_fg)
        self.rect(_MARGIN_MM, y0, 1.5, h, style="F")

        self.set_xy(_MARGIN_MM + 5, y0 + 3)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*tone_fg)
        self.cell(120, 7, _safe(engine_label))

        self.set_xy(_MARGIN_MM + 5, y0 + 12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_FOREGROUND)
        self.cell(120, 5, _safe(f"Transaction {txn_id}  -  Analyst decision: {analyst_label}"))

        stat_text = _safe(f"Risk {final_score:.0%}   Confidence {confidence:.0%}")
        self.set_font("Courier", "B", 10)
        self.set_text_color(*tone_fg)
        w = self.get_string_width(stat_text)
        self.set_xy(_PAGE_WIDTH_MM - _MARGIN_MM - w - 5, y0 + 8)
        self.cell(w, 6, stat_text, align="R")

        self.set_y(y0 + h + 6)
        self.set_text_color(*_FOREGROUND)

    def section_title(self, title: str) -> None:
        self.ln(1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*_GRAPHITE)
        self.cell(0, 6, _safe(title.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_COBALT)
        self.set_line_width(0.6)
        self.line(_MARGIN_MM, self.get_y(), _MARGIN_MM + 22, self.get_y())
        self.ln(3)
        self.set_text_color(*_FOREGROUND)

    def kv_grid(self, pairs: list[tuple[str, str, bool]]) -> None:
        """A compact two-column form grid — (label, value, monospace)
        triples — with a faint row rule, instead of one full-width
        "Label: value" line per field."""
        col_w = _CONTENT_WIDTH_MM / 2
        label_h, value_h = 3.6, 4.2
        row_h = label_h + value_h + 2.2  # value bottom + clear gap before the rule
        y = self.get_y()
        for i, (label, value, mono) in enumerate(pairs):
            col = i % 2
            if col == 0:
                self.ensure_space(row_h)
                y = self.get_y()
            x = _MARGIN_MM + col * col_w

            self.set_xy(x, y)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*_MUTED)
            self.cell(col_w - 3, label_h, _safe(label.upper()))

            self.set_xy(x, y + label_h)
            self.set_font("Courier" if mono else "Helvetica", "", 9)
            self.set_text_color(*_FOREGROUND)
            self.cell(col_w - 3, value_h, _safe(value))

            if col == 1 or i == len(pairs) - 1:
                rule_y = y + label_h + value_h + 0.8
                self.set_draw_color(*_BORDER)
                self.set_line_width(0.15)
                self.line(_MARGIN_MM, rule_y, _PAGE_WIDTH_MM - _MARGIN_MM, rule_y)
                self.set_y(y + row_h)
        self.ln(2)

    def stat_card(
        self, x: float, y: float, w: float, h: float, label: str, value: str, color: tuple[int, int, int]
    ) -> None:
        self.set_draw_color(*_BORDER)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, style="D")
        self.set_xy(x, y + 3)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_MUTED)
        self.cell(w, 4, _safe(label.upper()), align="C")
        self.set_xy(x, y + 8)
        self.set_font("Courier", "B", 16)
        self.set_text_color(*color)
        self.cell(w, 9, _safe(value), align="C")

    def callout_box(self, text: str, accent: tuple[int, int, int]) -> None:
        """A tinted, left-accented box for a block of prose — recommended
        action, evidence summaries, DNA descriptions — visually distinct
        from the form-grid fields around it."""
        self.set_font("Helvetica", "", 9)
        box_text_w = _CONTENT_WIDTH_MM - 10
        lines = self.multi_cell(box_text_w, 5, _safe(text), dry_run=True, output=MethodReturnValue.LINES)
        h = max(len(lines), 1) * 5 + 6
        self.ensure_space(h)
        y0 = self.get_y()

        self.set_fill_color(*_CANVAS)
        self.rect(_MARGIN_MM, y0, _CONTENT_WIDTH_MM, h, style="F")
        self.set_fill_color(*accent)
        self.rect(_MARGIN_MM, y0, 1.2, h, style="F")

        self.set_xy(_MARGIN_MM + 5, y0 + 3)
        self.set_text_color(*_FOREGROUND)
        self.multi_cell(box_text_w, 5, _safe(text))
        self.set_y(y0 + h + 4)

    def regulatory_reference(self, framework: str, citation: str, hedge: str) -> None:
        """A citation-style block — framework name, then the specific
        citation in smaller italic type, then the hedged reference text.
        Deliberately not boxed like callout_box: this is sourced,
        citation-grade text, not evidence to visually emphasize."""
        self.set_font("Helvetica", "", 8.5)
        lines = self.multi_cell(_CONTENT_WIDTH_MM, 4.2, _safe(hedge), dry_run=True, output=MethodReturnValue.LINES)
        self.ensure_space(4.5 + 3.8 + max(len(lines), 1) * 4.2 + 3)

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_FOREGROUND)
        self.cell(0, 4.5, _safe(framework), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED)
        self.cell(0, 3.8, _safe(citation), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*_FOREGROUND)
        self.multi_cell(_CONTENT_WIDTH_MM, 4.2, _safe(hedge))
        self.ln(2)

    def agent_table(self, agent_scores: list) -> None:
        col_agent, col_score, col_conf = 38.0, 18.0, 24.0
        col_finding = _CONTENT_WIDTH_MM - col_agent - col_score - col_conf
        header_h = 7.0

        self.ensure_space(header_h + 8)
        self.set_fill_color(*_GRAPHITE)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(_MARGIN_MM, self.get_y())
        for w, label, align in (
            (col_agent, "AGENT", "L"),
            (col_score, "SCORE", "C"),
            (col_conf, "CONFIDENCE", "C"),
            (col_finding, "KEY FINDING", "L"),
        ):
            self.cell(w, header_h, label, fill=True, align=align)
        self.ln(header_h)

        for i, a in enumerate(agent_scores):
            finding = a.reasons[0] if a.reasons else "-"
            self.set_font("Helvetica", "", 8)
            lines = self.multi_cell(
                col_finding - 4, 4.2, _safe(finding), dry_run=True, output=MethodReturnValue.LINES
            )
            row_h = max(len(lines), 1) * 4.2 + 3

            self.ensure_space(row_h)
            y = self.get_y()
            self.set_fill_color(*(_CANVAS if i % 2 == 1 else _WHITE))
            self.rect(_MARGIN_MM, y, _CONTENT_WIDTH_MM, row_h, style="F")

            self.set_text_color(*_FOREGROUND)
            self.set_xy(_MARGIN_MM, y + 1.5)
            self.set_font("Helvetica", "B", 8)
            self.cell(col_agent, row_h - 1.5, _safe(a.agent_name.replace("_", " ")))

            self.set_font("Courier", "", 8)
            self.set_xy(_MARGIN_MM + col_agent, y + 1.5)
            self.cell(col_score, row_h - 1.5, f"{a.score:.2f}", align="C")
            self.set_xy(_MARGIN_MM + col_agent + col_score, y + 1.5)
            self.cell(col_conf, row_h - 1.5, f"{a.confidence:.0%}", align="C")

            self.set_font("Helvetica", "", 8)
            self.set_xy(_MARGIN_MM + col_agent + col_score + col_conf + 2, y + 1.5)
            self.multi_cell(col_finding - 4, 4.2, _safe(finding))

            self.set_draw_color(*_BORDER)
            self.set_line_width(0.1)
            self.line(_MARGIN_MM, y + row_h, _PAGE_WIDTH_MM - _MARGIN_MM, y + row_h)
            self.set_y(y + row_h)
        self.ln(3)


def build_case_report_pdf(case: FraudCase, analyst_decision: Optional[AnalystDecision] = None) -> bytes:
    """Lay out the full investigation report as a PDF and return its bytes."""
    engine_tone_fg, engine_tone_bg = _tone_for(case.decision.value)
    engine_label = _label_for(case.decision.value)
    analyst_label = _label_for(analyst_decision.decision) if analyst_decision else "PENDING"
    txn = case.transaction

    pdf = _CaseReportPDF(format="A4", case_id=case.case_id)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
    pdf.set_title(f"FraudLens Investigation Report - {case.txn_id}")
    pdf.add_page()

    pdf.decision_banner(
        engine_label, analyst_label, engine_tone_fg, engine_tone_bg,
        case.txn_id, case.final_score, case.confidence,
    )

    pdf.section_title("Transaction Summary")
    pdf.kv_grid([
        ("Account", mask_identifier(txn.account_id), True),
        ("Amount", f"Rs. {txn.amount:,.2f}", True),
        ("Merchant", f"{mask_identifier(txn.merchant_id)} ({txn.merchant_category})", False),
        ("Channel", txn.channel, False),
        ("Timestamp", txn.timestamp, True),
        ("Device", mask_identifier(txn.device_id), True),
        ("IP Address", mask_ip(txn.ip_address), True),
        ("Report Status", "Draft", False),
    ])

    pdf.section_title("Risk Assessment")
    y = pdf.get_y()
    card_w = (_CONTENT_WIDTH_MM - 6) / 2
    pdf.ensure_space(20)
    y = pdf.get_y()
    pdf.stat_card(_MARGIN_MM, y, card_w, 20, "Risk Score", f"{case.final_score:.0%}", engine_tone_fg)
    pdf.stat_card(_MARGIN_MM + card_w + 6, y, card_w, 20, "Model Agreement", f"{case.confidence:.0%}", _COBALT)
    pdf.set_y(y + 20 + 6)

    pdf.section_title("Agent Evidence")
    if case.agent_scores:
        pdf.agent_table(case.agent_scores)
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5.5, "No agent evidence available for this case.")
        pdf.ln(2)

    if case.graph_evidence:
        ge = case.graph_evidence
        pdf.section_title("Graph Evidence")
        pdf.kv_grid([
            ("Ring Size", str(ge.ring_size), True),
            ("Suspicious Cluster", "Yes" if ge.suspicious_cluster else "No", False),
            ("Shared Devices", str(len(ge.shared_devices)), True),
            ("Shared IPs", str(len(ge.shared_ips)), True),
        ])
        if ge.evidence_summary:
            pdf.callout_box(ge.evidence_summary, _COBALT)

    if case.fraud_dna_match:
        dna = case.fraud_dna_match
        pdf.section_title("Fraud DNA Match")
        pdf.kv_grid([
            ("Similarity", f"{dna.similarity_score:.1%}", True),
            ("Matched Pattern", f"{dna.matched_ring_id} ({dna.fraud_type})", False),
        ])
        pdf.callout_box(f"Modus operandi: {dna.modus_operandi}\n\nRecommendation: {dna.recommendation}", _COBALT)

    if case.system_action:
        pdf.section_title("Autonomous Action")
        pdf.callout_box(
            "This case was automatically held pending review - final score, model agreement "
            "confidence, and (where applicable) the Fraud DNA match all cleared the "
            "autonomous-action thresholds together. This is a hold, not a block: no real "
            "transaction was stopped, and an analyst decision on this case reverses it "
            "immediately. See the audit trail (event_type=autonomous_action) for the exact "
            "scores that triggered it.",
            _COBALT,
        )

    fraud_type = case.fraud_dna_match.fraud_type if case.fraud_dna_match else case.transaction.fraud_pattern_type
    regulatory_context = get_regulatory_context(case.decision, fraud_type)
    if regulatory_context:
        pdf.section_title("Regulatory Context (Reference Only)")
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(
            _CONTENT_WIDTH_MM, 4,
            "Background context for the reviewing analyst, not a record of any actual "
            "regulatory filing or notification - FraudLens does not submit anything to the "
            "RBI, FIU-IND, or CERT-In.",
        )
        pdf.ln(2)
        pdf.set_text_color(*_FOREGROUND)
        for ref in regulatory_context:
            pdf.regulatory_reference(ref.framework, ref.citation, ref.hedge)

    pdf.section_title("Recommended Action")
    pdf.callout_box(case.recommended_action, engine_tone_fg)

    if analyst_decision:
        pdf.section_title("Analyst Decision")
        pdf.kv_grid([
            ("Decision", analyst_label, False),
            ("Analyst", analyst_decision.analyst or "Unspecified", False),
        ])
        pdf.callout_box(analyst_decision.notes or "None provided.", _COBALT)

    output = pdf.output()
    return bytes(output)
