"""Accessible PDF export of an Access Passport (preferences only)."""
from __future__ import annotations

import io


def passport_pdf(profile) -> bytes:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    x = inch
    y = height - inch

    def line(text, size=11, dy=16, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, y, text)
        y -= dy

    line("AccessWeave — Access Passport", 18, 26, bold=True)
    line(f"Profile: {profile.name}", 13, 20, bold=True)
    line("This describes how software should behave for me. It is not a medical record.",
         9, 22)

    p = profile.payload or {}
    out = p.get("output", {})
    cog = p.get("cognitive", {})
    safe = p.get("safety", {})

    line("How I control the interface", 12, 18, bold=True)
    line(f"• Input: {', '.join(p.get('input_modes', ['keyboard']))}")
    line(f"• Minimum target size: {p.get('minimum_target_px', 44)} px")

    line("How information should be presented", 12, 18, bold=True)
    line(f"• Text scale: {out.get('text_scale', 1.0)}x")
    line(f"• Contrast: {out.get('contrast', 'system')}")
    line(f"• Speech: {'on' if out.get('speech_enabled') else 'off'}")
    line(f"• Captions: {'on' if out.get('captions') else 'off'}")
    line(f"• Reduced motion: {'on' if out.get('reduced_motion') else 'off'}")

    line("How tasks should be organized", 12, 18, bold=True)
    line(f"• Plain language: {'yes' if cog.get('plain_language') else 'no'}")
    line(f"• One step at a time: {'yes' if cog.get('one_step_at_a_time') else 'no'}")
    line(f"• Show progress: {'yes' if cog.get('show_progress', True) else 'no'}")
    line(f"• Recovery instructions: {'yes' if cog.get('recovery_instructions', True) else 'no'}")

    line("What must always require confirmation", 12, 18, bold=True)
    line(f"• Sending / sharing: {safe.get('external_action', 'strong')}")
    line(f"• Payments: {safe.get('financial_action', 'strong')}")
    line(f"• Medical actions: {safe.get('medical_action', 'block')} (never automatic)")

    c.showPage()
    c.save()
    return buf.getvalue()
