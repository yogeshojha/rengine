import base64
import colorsys

import plotly.graph_objs as go
from plotly.io import to_image
from django.db.models import Count
from reNgine.definitions import NUCLEI_SEVERITY_MAP

from startScan.models import *



"""
    This file is used to generate the charts for the pdf report.
"""

def generate_subdomain_chart_by_http_status(subdomains):
    """
    Generates a donut chart using plotly for the subdomains based on the http status.
    Includes label, count, and percentage inside the chart segments and in the legend.
    Args:
        subdomains: QuerySet of subdomains.
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

    total = sum(entry['count'] for entry in http_status_count)
    
    labels = [str(entry['http_status']) for entry in http_status_count]
    sizes = [entry['count'] for entry in http_status_count]
    colors = [get_color_by_http_status(entry['http_status']) for entry in http_status_count]

    text = [f"{label}<br>{size}<br>({size/total:.1%})" for label, size in zip(labels, sizes)]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=sizes,
        marker=dict(colors=colors),
        hole=0.4,
        textinfo="text",
        text=text,
        textposition="inside",
        textfont=dict(size=10),
        hoverinfo="label+percent+value"
    )])
    
    fig.update_layout(
        title_text="",
        annotations=[dict(text='HTTP Status', x=0.5, y=0.5, font_size=14, showarrow=False)],
        showlegend=True,
        margin=dict(t=60, b=60, l=60, r=60),
        width=700,
        height=700,
        legend=dict(
            font=dict(size=18),
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        ),
    )

    img_bytes = to_image(fig, format="png")
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_base64



def get_color_by_severity(severity_int):
    """
    Returns a color based on the severity level using a modern color scheme.
    """
    color_map = {
        4: '#FF4D6A',
        3: '#FF9F43',
        2: '#FFCA3A',
        1: '#4ADE80',
        0: '#4ECDC4',
        -1: '#A8A9AD',
    }
    return color_map.get(severity_int, '#A8A9AD')  # Default to gray if severity is unknown

def generate_vulnerability_chart_by_severity(vulnerabilities):
    """
    Generates a donut chart using plotly for the vulnerabilities based on the severity.
    Args:
        vulnerabilities: QuerySet of Vulnerability objects.
    Returns:
        Image as base64 encoded string.
    """
    severity_counts = (
        vulnerabilities
        .values('severity')
        .annotate(count=Count('severity'))
        .order_by('-severity')
    )
    
    total = sum(entry['count'] for entry in severity_counts)
    
    labels = [NUCLEI_REVERSE_SEVERITY_MAP[entry['severity']].capitalize() for entry in severity_counts]
    values = [entry['count'] for entry in severity_counts]
    colors = [get_color_by_severity(entry['severity']) for entry in severity_counts]
    
    text = [f"{label}<br>{value}<br>({value/total:.1%})" for label, value in zip(labels, values)]

    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values,
        marker=dict(colors=colors),
        hole=0.4,
        textinfo="text",
        text=text,
        textposition="inside",
        textfont=dict(size=12),
        hoverinfo="label+percent+value",
    )])
    
    fig.update_layout(
        title_text="",
        annotations=[dict(text='Severity', x=0.5, y=0.5, font_size=14, showarrow=False)],
        showlegend=True,
        margin=dict(t=60, b=60, l=60, r=60),
        width=700,
        height=700,
        legend=dict(
            font=dict(size=18),
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        ),
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