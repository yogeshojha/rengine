import base64
import colorsys

import plotly.graph_objs as go
from plotly.io import to_image
from django.db.models import Count

from startScan.models import *



"""
    This file is used to generate the charts for the pdf report.
"""

def generate_subdomain_chart_by_http_status(subdomains):
    """
        Generates a donut chart using plotly for the subdomains based on the http status.
        Args:
            sobdomains: List of subdomains.
        Returns:
            Image as base64 encoded string.
    """
    http_statuses = (
        subdomains
        .exclude(http_status=0)
        .values('http_status')
        .annotate(count=Count('http_status'))
        .order_by('-count')
    )
    http_status_count = [{'http_status': entry['http_status'], 'count': entry['count']} for entry in http_statuses]

    labels = [f"{entry['http_status']} ({entry['count']})" for entry in http_status_count]
    sizes = [entry['count'] for entry in http_status_count]
    colors = [get_color_by_http_status(entry['http_status']) for entry in http_status_count]

    fig = go.Figure(data=[go.Pie(
            labels=labels, 
            values=sizes, 
            marker=dict(colors=colors),
            hole=0.4,
            textinfo="value",
            textfont=dict(size=18),
            hoverinfo="none"
        )])
    
    fig.update_layout(
        title_text="",
        annotations=[dict(text='HTTP Status', x=0.5, y=0.5, font_size=14, showarrow=False)],
        showlegend=True,
        margin=dict(t=50, b=50, l=50, r=50),
        width=450,
        height=450,
    )

    img_bytes = to_image(fig, format="png")
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_base64


def generate_color(base_color, offset):
    r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
    factor = 1 + (offset * 0.03)
    r, g, b = [min(255, int(c * factor)) for c in (r, g, b)]
    return f"#{r:02x}{g:02x}{b:02x}"


def get_color_by_http_status(http_status):
    """
        Returns the color based on the http status.
        Args:
            http_status: HTTP status code.
        Returns:
            Color code.
    """

    status = int(http_status)
    
    colors = {
        200: "#36a2eb",
        300: "#4bc0c0",
        400: "#ff6384",
        401: "#ff9f40",
        403: "#f27474",
        404: "#ffa1b5",
        429: "#bf7bff",
        500: "#9966ff",
        502: "#8a4fff",
        503: "#c39bd3",
    }


    if status in colors:
        return colors[status]
    elif 200 <= status < 300:
        return generate_color(colors[200], status - 200)
    elif 300 <= status < 400:
        return generate_color(colors[300], status - 300)
    elif 400 <= status < 500:
        return generate_color(colors[400], status - 400)
    elif 500 <= status < 600:
        return generate_color(colors[500], status - 500)
    else:
        return "#c9cbcf"