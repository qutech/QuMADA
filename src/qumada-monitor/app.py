#!/usr/bin/env python3
"""
Live quantum‑device monitor: geometry + voltages ➜ interactive SVG plot.

Start with:
    python dash_device_monitor.py --ws ws://localhost:8765 --colorscale Cividis
"""
import argparse, json, itertools, os, warnings
from collections import defaultdict

import plotly.graph_objects as go
import plotly.express as px
from plotly.colors import sample_colorscale
from shapely.geometry import Polygon

import dash.exceptions
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update
from dash_extensions import WebSocket                         # pip install dash-extensions

# ---------------- helpers -------------------------------------------------- #
from qumada.utils.geometry import string_to_gate_list, Gate


def layer_palette(layers):
    """Return dict layer -> rgba border colour (qualitative palette, repeats if needed)."""
    palette = itertools.cycle(px.colors.qualitative.Plotly)
    return {layer: next(palette) for layer in layers}


def voltage_colour(v, vabs_max, colorscale):
    """Map voltage to rgba string using the chosen Plotly colourscale."""        # flat value
    ratio = 0.5 + v / vabs_max / 2
    return sample_colorscale(colorscale, [ratio])[0]              # :contentReference[oaicite:9]{index=9}


def _set_alpha(color: str, value) -> str:
    if color.startswith("rgb("):
        result = color.replace("rgb(", "rgba(")
        result = result.replace(")", f",{value})")
    elif color.startswith("rgba("):
        result = color.rsplit(",", 1)[0]
        result = f"{result},{value})"
    else:
        raise NotImplementedError(color)
    return result


def gates_to_figure(gates: list[Gate], voltages: list[dict], colorscale):
    """Build a Plotly figure from gate list + latest voltages dict."""
    if not gates:
        return go.Figure()

    gate_runtime_info = []
    for gate in gates:
        candidates = []
        for data in voltages:
            if gate.label in data["label"]:
                candidates.append(data)
        if not candidates:
            gate_runtime_info.append(None)
        else:
            if len(candidates) > 1:
                data = min(candidates, key=lambda d: d["label"])
            else:
                data, = candidates
            gate_runtime_info.append(data)

    # 1) derive colour mapping
    v_values = [info["value"]
                for info in gate_runtime_info
                if info is not None]
    vabs_max = max(map(abs, v_values + [1.0]))
    layers = sorted({g.layer for g in gates})
    border_col = layer_palette(layers)                             # :contentReference[oaicite:10]{index=10}

    fig = go.Figure()
    for gate, info in zip(gates, gate_runtime_info):
        poly: Polygon = gate.polygon
        x, y = poly.exterior.xy
        x = list(x)
        y = list(y)
        if info:
            v = info["value"]
            unit = info["unit"]
            text = f"{gate.label}:<br>{v:.3f} {unit}"
            fill_col = voltage_colour(v, vabs_max, colorscale)
        else:
            text = f"{gate.label}:<br>NaN"
            fill_col = None
        line_col = border_col[gate.layer]

        if fill_col is None:
            fill_col = "rgba(0,0,0,0)"
        else:
            fill_col = _set_alpha(fill_col, 0.3)

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",                                     # polygon fill trick :contentReference[oaicite:11]{index=11}
                fillcolor=fill_col,
                line=dict(color=line_col, width=1),
                hoverinfo="text",
                text=text,
                showlegend=False,
                mode='lines',
            )
        )
        # add static label at predefined position
        if getattr(gate, "label_position", None):
            lx, ly = gate.label_position
            fig.add_annotation(x=lx, y=ly,
                               text=text,
                               showarrow=False,
                               font=dict(size=10, color="black"))

    fig.update_layout(
        xaxis=dict(scaleanchor="y", visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white",
        uirevision=gates,
    )
    return fig


# ---------------- Dash app -------------------------------------------------- #
def make_app(ws_url: str) -> Dash:
    app = Dash(__name__, title="Quantum‑dot voltage monitor")

    app.layout = html.Div(
        [
            html.H3("Live device layout"),
            WebSocket(id="ws", url=ws_url),
            dcc.Store(id="gate-geometry"),
            dcc.Store(id="voltages"),
            dcc.Store(id="parameters"),
            dcc.Graph(id="layout-graph", style={"height": "700px"}),
            dcc.Dropdown(
                id="colorscale-dropdown",
                value="rdbu",
                options=[{"label": cs, "value": cs} for cs in px.colors.named_colorscales()],
                clearable=False,
                style={"width": "250px"},
            ),
            html.Hr(),
            dash_table.DataTable(
                id="parameter-table",
                columns=[{"name": "Label", "id": "label"},
                         {"name": "Value", "id": "value"},
                         {"name": "Unit", "id": "unit"},
                         {"name": "Timestamp", "id": "timestamp"},
                         {"name": "Name", "id": "name"},
                         ],
                style_cell={"fontFamily": "monospace", "padding": "2px 6px"},
                style_table={"max-height": "400px", "overflowY": "auto"},
            ),
        ],
        style={"font-family": "Source Sans Pro, sans-serif", "margin": "0 20px"},
    )

    # ---------- 1) unpack every WebSocket message -------------------------- #
    @app.callback(
        Output("gate-geometry", "data"),
        Output("parameters", "data"),
        Input("ws", "message"),
        prevent_initial_call=True,
    )
    def _unpack_ws(msg):
        if msg is None:
            return no_update, no_update

        data = json.loads(msg["data"])

        parameters = gate_geometry = no_update
        if "parameters" in data:
            parameters = data["parameters"]
        if "gate_geometry" in data:
            gate_geometry = data["gate_geometry"]
        return gate_geometry, parameters

    @app.callback(
        Output("voltages", "data"),
        Input("parameters", "data"),
        prevent_initial_call=True,
    )
    def _select_voltages(parameters):
        voltages = []
        for parameter in parameters:
            assert "unit" in parameter, f"{parameter!r}"
            if "V" in parameter["unit"]:
                value = {attr: parameter[attr] for attr in ["name", "value", "label", "unit"]}
                voltages.append(value)
        return voltages

    @app.callback(
        Output("parameter-table", "data"),
        Input("parameters", "data"),
    )
    def _parameter_table(parameters):
        if not parameters:
            return []

        cols = ["label", "value", "unit", "timestamp", "name"]
        return [
            {col: parameter[col] for col in cols}
            for parameter in parameters
        ]

    @app.callback(
        Output("layout-graph", "figure"),
        Input("gate-geometry", "data"),
        Input("voltages", "data"),
        Input("colorscale-dropdown", "value"),
        prevent_initial_call=True,
    )
    def _draw_layout(geom_str, volts, colorscale_selected):
        if geom_str is None or volts is None:
            raise dash.exceptions.PreventUpdate

        gates = string_to_gate_list(geom_str)
        fig = gates_to_figure(gates, volts, colorscale_selected)
        return fig

    return app

