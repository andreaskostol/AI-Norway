"""Shared helper to place a wrapped notes string under matplotlib figures.

The note is wrapped to the width of the plot grid (the bbox enclosing the
supplied axes), using actual rendered text metrics. Manual newline breaks
in the input are removed first so wrapping is uniform.
"""

import textwrap
import numpy as np


def place_note(fig, ax_or_axes, note_raw, y=0.03, fontsize=18,
               color='#555555', linespacing=1.5):
    """Place a wrapped notes string under the plot grid.

    Parameters
    ----------
    fig : matplotlib Figure
    ax_or_axes : Axes or array/list of Axes
    note_raw : str
        Note text. Manual newlines are stripped before wrapping.
    y : float
        Vertical position in figure coordinates.
    """
    # Normalise to a flat list of axes.
    if hasattr(ax_or_axes, 'flatten'):
        axes_list = list(np.asarray(ax_or_axes).flatten())
    elif isinstance(ax_or_axes, (list, tuple)):
        axes_list = list(ax_or_axes)
    else:
        axes_list = [ax_or_axes]

    # Strip manual line breaks; let textwrap re-wrap evenly.
    cleaned = ' '.join(note_raw.split())

    left = min(ax.get_position().x0 for ax in axes_list)
    right = max(ax.get_position().x1 for ax in axes_list)
    fig_width_px = fig.get_size_inches()[0] * fig.dpi
    plot_width_px = (right - left) * fig_width_px

    renderer = fig.canvas.get_renderer()
    probe = fig.text(0, 0, cleaned, fontsize=fontsize)
    text_width_px = probe.get_window_extent(renderer=renderer).width
    probe.remove()

    chars = len(cleaned)
    px_per_char = text_width_px / chars if chars else 7
    wrap_chars = max(20, int(plot_width_px / px_per_char))
    note = textwrap.fill(cleaned, width=wrap_chars)

    fig.text(left, y, note, ha='left', va='top',
             fontsize=fontsize, color=color, linespacing=linespacing)
