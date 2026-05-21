"""Whiteboard renderer.

MVP approach:
  - Generate a single SVG scene per segment (title + bullets + doodles)
  - Wrap into a self-contained HTML file with CSS animations
  - Use Playwright to record the scene to video (720p)
  - Mux TTS narration audio
"""
