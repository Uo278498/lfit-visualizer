"""Construcción de un mapa interactivo de reglas sin dependencias externas."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.lfit_engine import LearnedRule


MAP_COMPONENT_HEIGHT = 760
_COMPONENT_DIRECTORY = Path(__file__).resolve().parent.parent / "components" / "theory_map"


def _json_safe(value: Any) -> Any:
    """Convierte metadatos arbitrarios a un formato que pueda viajar al componente HTML."""
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def filter_rules_by_complexity(rules: Sequence[LearnedRule], layer: str) -> list[LearnedRule]:
    """Devuelve reglas de un nivel de complejidad para el mapa de teoría."""
    if layer == "Todas":
        return list(rules)
    if layer == "4 o más condiciones":
        return [rule for rule in rules if rule.conditions_count >= 4]
    expected_conditions = int(layer.split()[0])
    return [rule for rule in rules if rule.conditions_count == expected_conditions]


def _graph_payload(
    rules: Sequence[LearnedRule],
    target_column: str,
    target_value: str,
    observations: int | None,
    active_rule_id: str | None,
) -> dict[str, Any]:
    condition_to_rules: dict[tuple[str, str], list[str]] = {}
    serialized_rules: list[dict[str, Any]] = []
    for rule in rules:
        for condition in rule.antecedents.items():
            condition_to_rules.setdefault(condition, []).append(rule.identifier)
        serialized_rules.append(
            {
                "id": rule.identifier,
                "label": rule.identifier,
                "text": rule.text,
                "conditions": rule.conditions_count,
                "coverage": rule.coverage,
                "coveragePercentage": rule.coverage / observations if observations else None,
                "compatibleCases": rule.compatible_cases,
                "consistency": rule.data_consistency,
                "targetPrevalence": rule.target_prevalence,
                "lift": rule.lift,
                "metadata": _json_safe(getattr(rule, "metadata", {})),
            }
        )

    conditions = [
        {
            "id": f"condition::{variable}::{value}",
            "label": f"{variable} = {value}",
            "variable": variable,
            "value": value,
            "ruleIds": identifiers,
        }
        for (variable, value), identifiers in sorted(condition_to_rules.items())
    ]
    return {
        "conditions": conditions,
        "rules": serialized_rules,
        "target": {"label": f"{target_column} = {target_value}", "column": target_column, "value": target_value},
        "activeRuleId": active_rule_id,
    }


def build_theory_map_html(
    rules: Sequence[LearnedRule],
    target_column: str,
    target_value: str,
    observations: int | None = None,
    active_rule_id: str | None = None,
) -> str:
    """Genera un SVG con zoom, paneo, tooltip y panel de detalle al hacer clic.

    El nodo central de cada regla conserva el significado de los antecedentes
    conjuntos: una regla con tres condiciones no se convierte erróneamente en tres
    relaciones independientes hacia la salida.
    """
    payload = _graph_payload(rules, target_column, target_value, observations, active_rule_id)
    serialized = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Arial, sans-serif; color: #1e293b; background: #f8fafc; }}
  #layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 300px; height: {MAP_COMPONENT_HEIGHT}px; border: 1px solid #dbe4ee; border-radius: 10px; overflow: hidden; background: white; }}
  #canvas {{ position: relative; min-width: 0; background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%); }}
  #graph {{ width: 100%; height: 100%; display: block; cursor: grab; touch-action: none; }}
  #graph.dragging {{ cursor: grabbing; }}
  #details {{ border-left: 1px solid #dbe4ee; padding: 16px; overflow-y: auto; background: #fbfdff; font-size: 13px; line-height: 1.45; }}
  #details h3 {{ margin: 0 0 8px; font-size: 16px; color: #0f3f6e; }}
  #details h4 {{ margin: 14px 0 5px; font-size: 13px; color: #334155; }}
  #details p {{ margin: 5px 0; }}
  #details ul {{ margin: 5px 0; padding-left: 18px; }}
  #hint {{ color: #64748b; }}
  #tooltip {{ position: absolute; max-width: 280px; display: none; z-index: 2; pointer-events: none; padding: 8px 10px; border-radius: 6px; background: #0f172a; color: white; font-size: 12px; line-height: 1.35; box-shadow: 0 4px 12px rgba(15, 23, 42, .25); }}
  .edge {{ stroke: #94a3b8; stroke-width: 1.5; opacity: .75; }}
  .edge.output {{ stroke: #2563eb; stroke-width: 2.2; }}
  .node rect {{ stroke-width: 1.5; rx: 8; ry: 8; }}
  .node text {{ font-size: 14px; fill: #0f172a; pointer-events: none; }}
  .condition rect {{ fill: #fef3c7; stroke: #d97706; }}
  .rule rect {{ fill: #dbeafe; stroke: #2563eb; }}
  .target rect {{ fill: #dcfce7; stroke: #16a34a; }}
  .node:hover rect, .node.selected rect {{ stroke-width: 3; filter: brightness(.97); }}
  .legend {{ position: absolute; bottom: 12px; left: 12px; color: #475569; font-size: 12px; background: rgba(255,255,255,.92); border: 1px solid #dbe4ee; border-radius: 6px; padding: 7px 9px; }}
  @media (max-width: 760px) {{ #layout {{ grid-template-columns: 1fr; height: auto; }} #canvas {{ height: 550px; }} #details {{ border-left: 0; border-top: 1px solid #dbe4ee; min-height: 230px; }} }}
</style>
</head>
<body>
<div id="layout">
  <div id="canvas">
    <svg id="graph" aria-label="Mapa interactivo de reglas"></svg>
    <div id="tooltip"></div>
    <div class="legend">Rueda: zoom · Arrastra el fondo: mover · Clic en un nodo: detalle</div>
  </div>
  <aside id="details"><h3>Mapa de teoría</h3><p id="hint">Selecciona una condición, una regla o la salida para ver sus metadatos.</p></aside>
</div>
<script>
(() => {{
  const data = {serialized};
  const svg = document.getElementById('graph');
  const canvas = document.getElementById('canvas');
  const tooltip = document.getElementById('tooltip');
  const details = document.getElementById('details');
  const svgNs = 'http://www.w3.org/2000/svg';
  const width = 1180;
  const nodeGap = 72;
  const count = Math.max(data.conditions.length, data.rules.length, 1);
  const height = Math.max(620, 150 + count * nodeGap);
  const conditionX = 180, ruleX = 575, targetX = 970;
  const positions = {{}};
  const ruleById = Object.fromEntries(data.rules.map(rule => [rule.id, rule]));
  const conditionById = Object.fromEntries(data.conditions.map(item => [item.id, item]));
  let view = {{ x: 0, y: 0, w: width, h: height }};
  let dragging = null;
  let selectedElement = null;
  const ruleGroups = {{}};

  function element(name, attributes = {{}}) {{
    const item = document.createElementNS(svgNs, name);
    Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value));
    return item;
  }}
  function truncate(text, limit = 29) {{ return text.length > limit ? text.slice(0, limit - 1) + '…' : text; }}
  function percent(value) {{ return (Number(value || 0) * 100).toFixed(1) + '%'; }}
  function coverage(rule) {{ return rule.coveragePercentage === null || rule.coveragePercentage === undefined ? `${{rule.coverage}} filas` : `${{rule.coverage}} filas (${{percent(rule.coveragePercentage)}})`; }}
  function lift(value) {{ return value === null || value === undefined ? '—' : Number(value).toFixed(2); }}
  function setView() {{ svg.setAttribute('viewBox', `${{view.x}} ${{view.y}} ${{view.w}} ${{view.h}}`); }}
  function appendText(parent, value, x, y, anchor = 'middle') {{
    const label = element('text', {{ x, y, 'text-anchor': anchor, 'dominant-baseline': 'middle' }});
    label.textContent = truncate(value);
    parent.appendChild(label);
  }}
  function addLine(start, end, output = false, thickness = 1.5) {{
    const line = element('line', {{ x1: start.x, y1: start.y, x2: end.x, y2: end.y, class: output ? 'edge output' : 'edge' }});
    line.style.strokeWidth = thickness;
    svg.appendChild(line);
  }}
  function clearSelection() {{ if (selectedElement) selectedElement.classList.remove('selected'); }}
  function showTooltip(event, lines) {{
    tooltip.textContent = lines.join(' · ');
    tooltip.style.display = 'block';
    const box = canvas.getBoundingClientRect();
    tooltip.style.left = Math.min(event.clientX - box.left + 12, box.width - 290) + 'px';
    tooltip.style.top = Math.max(event.clientY - box.top - 38, 8) + 'px';
  }}
  function hideTooltip() {{ tooltip.style.display = 'none'; }}
  function title(text) {{ const item = document.createElement('h3'); item.textContent = text; details.replaceChildren(item); }}
  function text(value) {{ const item = document.createElement('p'); item.textContent = value; details.appendChild(item); }}
  function section(name, entries) {{
    const heading = document.createElement('h4'); heading.textContent = name; details.appendChild(heading);
    const list = document.createElement('ul');
    entries.forEach(entry => {{ const row = document.createElement('li'); row.textContent = entry; list.appendChild(row); }});
    details.appendChild(list);
  }}
  function selectNode(group, render, ruleId = null) {{
    clearSelection(); selectedElement = group; group.classList.add('selected'); render();
    if (ruleId && window.parent !== window) {{
      window.parent.postMessage({{ type: 'lfit:ruleSelected', value: ruleId }}, '*');
    }}
  }}
  function showRule(rule) {{
    title(rule.id);
    text(rule.text);
    section('Métricas', [
      `Cobertura: ${{coverage(rule)}}`,
      `Casos compatibles: ${{rule.compatibleCases}}`,
      `Consistencia: ${{percent(rule.consistency)}}`,
      `Frecuencia de salida: ${{percent(rule.targetPrevalence)}}`,
      `Lift: ${{lift(rule.lift)}}`,
      `Condiciones: ${{rule.conditions}}`,
    ]);
    const metadata = Object.entries(rule.metadata || {{}}).map(([key, value]) => `${{key}}: ${{Array.isArray(value) ? value.join(', ') : value}}`);
    if (metadata.length) section('Metadatos', metadata);
  }}
  function showCondition(condition) {{
    title(condition.label);
    text(`Esta condición aparece en ${{condition.ruleIds.length}} regla(s) visibles.`);
    section('Reglas relacionadas', condition.ruleIds.map(id => {{
      const rule = ruleById[id];
      return `${{id}} · cobertura ${{coverage(rule)}} · consistencia ${{percent(rule.consistency)}}`;
    }}));
  }}
  function showTarget() {{
    title(data.target.label);
    text(`Salida seleccionada en ${{data.rules.length}} regla(s) visibles.`);
    section('Resumen', [
      `Cobertura máxima: ${{Math.max(...data.rules.map(rule => rule.coverage))}} filas`,
      `Reglas de 1 condición: ${{data.rules.filter(rule => rule.conditions === 1).length}}`,
      `Reglas de 2 o más condiciones: ${{data.rules.filter(rule => rule.conditions >= 2).length}}`,
    ]);
  }}
  function nodeGroup(kind, label, x, y, widthNode, onClick, tooltipLines, ruleId = null) {{
    const group = element('g', {{ class: `node ${{kind}}`, tabindex: '0', role: 'button' }});
    const rect = element('rect', {{ x: x - widthNode / 2, y: y - 22, width: widthNode, height: 44 }});
    group.appendChild(rect); appendText(group, label, x, y);
    group.addEventListener('mouseenter', event => showTooltip(event, tooltipLines()));
    group.addEventListener('mousemove', event => showTooltip(event, tooltipLines()));
    group.addEventListener('mouseleave', hideTooltip);
    group.addEventListener('click', event => {{ event.stopPropagation(); selectNode(group, onClick, ruleId); }});
    group.addEventListener('keydown', event => {{ if (event.key === 'Enter' || event.key === ' ') {{ event.preventDefault(); selectNode(group, onClick); }} }});
    svg.appendChild(group); return group;
  }}

  const targetPosition = {{ x: targetX, y: height / 2 }};
  const maxCoverage = Math.max(...data.rules.map(rule => rule.coverage), 1);
  data.conditions.forEach((condition, index) => {{ positions[condition.id] = {{ x: conditionX, y: 80 + index * nodeGap }}; }});
  data.rules.forEach((rule, index) => {{ positions[rule.id] = {{ x: ruleX, y: 80 + index * nodeGap }}; }});
  data.conditions.forEach(condition => condition.ruleIds.forEach(ruleId => addLine(positions[condition.id], positions[ruleId])));
  data.rules.forEach(rule => addLine(positions[rule.id], targetPosition, true, 1.5 + 4 * rule.coverage / maxCoverage));
  data.conditions.forEach(condition => {{
    const position = positions[condition.id];
    nodeGroup('condition', condition.label, position.x, position.y, 260, () => showCondition(condition), () => [condition.label, `${{condition.ruleIds.length}} regla(s) visible(s)`]);
  }});
  data.rules.forEach(rule => {{
    const position = positions[rule.id];
    const ratio = rule.coverage / maxCoverage;
    const widthNode = 120 + 76 * ratio;
    ruleGroups[rule.id] = nodeGroup('rule', rule.label, position.x, position.y, widthNode, () => showRule(rule), () => [rule.id, `Cobertura: ${{coverage(rule)}}`, `Consistencia: ${{percent(rule.consistency)}}`, `Lift: ${{lift(rule.lift)}}`], rule.id);
  }});
  nodeGroup('target', data.target.label, targetPosition.x, targetPosition.y, 270, showTarget, () => [data.target.label, `${{data.rules.length}} regla(s) visible(s)`]);
  if (data.activeRuleId && ruleGroups[data.activeRuleId]) {{
    selectNode(ruleGroups[data.activeRuleId], () => showRule(ruleById[data.activeRuleId]));
  }}
  svg.addEventListener('click', () => {{ clearSelection(); selectedElement = null; details.innerHTML = '<h3>Mapa de teoría</h3><p id="hint">Selecciona una condición, una regla o la salida para ver sus metadatos.</p>'; }});
  svg.addEventListener('wheel', event => {{
    event.preventDefault();
    const rect = svg.getBoundingClientRect();
    const px = view.x + (event.clientX - rect.left) / rect.width * view.w;
    const py = view.y + (event.clientY - rect.top) / rect.height * view.h;
    const factor = event.deltaY < 0 ? 0.84 : 1.19;
    const newW = Math.max(430, Math.min(2600, view.w * factor));
    const newH = newW * height / width;
    view.x = px - (px - view.x) * newW / view.w;
    view.y = py - (py - view.y) * newH / view.h;
    view.w = newW; view.h = newH; setView();
  }}, {{ passive: false }});
  svg.addEventListener('pointerdown', event => {{ if (event.target === svg) {{ dragging = {{ x: event.clientX, y: event.clientY, viewX: view.x, viewY: view.y }}; svg.classList.add('dragging'); svg.setPointerCapture(event.pointerId); }} }});
  svg.addEventListener('pointermove', event => {{ if (dragging) {{ const rect = svg.getBoundingClientRect(); view.x = dragging.viewX - (event.clientX - dragging.x) / rect.width * view.w; view.y = dragging.viewY - (event.clientY - dragging.y) / rect.height * view.h; setView(); }} }});
  svg.addEventListener('pointerup', () => {{ dragging = null; svg.classList.remove('dragging'); }});
  svg.addEventListener('dblclick', () => {{ view = {{ x: 0, y: 0, w: width, h: height }}; setView(); }});
  setView();
}})();
</script>
</body>
</html>
"""


def render_theory_map(
    rules: Sequence[LearnedRule],
    target_column: str,
    target_value: str,
    observations: int,
    active_rule_id: str | None,
    key: str,
) -> str | None:
    """Renderiza el mapa y devuelve el identificador de regla pulsado, si existe."""
    import streamlit.components.v1 as components

    component = components.declare_component(
        "lfit_theory_map", path=str(_COMPONENT_DIRECTORY)
    )
    selected = component(
        html=build_theory_map_html(
            rules,
            target_column,
            target_value,
            observations=observations,
            active_rule_id=active_rule_id,
        ),
        height=MAP_COMPONENT_HEIGHT,
        default=None,
        key=key,
    )
    valid_identifiers = {rule.identifier for rule in rules}
    return selected if selected in valid_identifiers else None
