import streamlit as st
import streamlit.components.v1 as components
import json
import os
from snowflake.snowpark.context import get_active_session

session = get_active_session()


def load_layout_engine():
    """Load LayoutEngine.js from the same directory as this file."""
    path = os.path.join(os.path.dirname(__file__), "LayoutEngine.js")
    with open(path, "r") as f:
        return f.read()


st.set_page_config(page_title="Workflow Editor", layout="wide")

st.title("Workflow Editor")
st.caption("Manage task graph definitions stored in metadata.CF_Configuration")

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

@st.cache_data(ttl=5)
def list_workflows():
    rows = session.sql("""
        SELECT CF_NAM_Configuration_Name AS name,
               CF_TYP_CFT_ConfigurationType AS type
        FROM metadata.lCF_Configuration
        ORDER BY CF_NAM_Configuration_Name
    """).collect()
    return [{"name": r["NAME"], "type": r["TYPE"]} for r in rows]


def load_workflow(name):
    result = session.call("metadata._ConfigurationGet", name)
    return result if result else None


def save_workflow(name, content):
    return session.call("metadata._ConfigurationUpsert", name, content, "Workflow")


def delete_workflow(name):
    return session.call("metadata._ConfigurationDelete", name)


def validate_json(text):
    if not text.strip():
        return None, "Content is empty"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, str(e)


def extract_graph(parsed):
    """Extract nodes and edges from parsed workflow JSON."""
    tasks = parsed.get("TASKS", [])
    nodes = []
    edges = []
    for i, task in enumerate(tasks):
        nodes.append({
            "id": task.get("name", f"task_{i}"),
            "label": task.get("name", f"task_{i}"),
            "is_root": task.get("is_root", False),
            "description": task.get("description", ""),
        })
        for after in task.get("after", []):
            edges.append({
                "source": after.get("name", ""),
                "target": task.get("name", f"task_{i}"),
            })
    return {"nodes": nodes, "edges": edges}


def render_graph_html(graph_data):
    """Generate HTML with the LayoutEngine and SVG rendering."""
    graph_json = json.dumps(graph_data)

    html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; overflow: hidden; background: #0e1117; font-family: sans-serif; }
  svg { width: 100%; height: 100%; }
  .node-circle { cursor: grab; }
  .node-circle:active { cursor: grabbing; }
  .node-label { fill: #fafafa; font-size: 11px; pointer-events: none; text-anchor: middle; }
  .edge-line { stroke: #4a9eff; stroke-width: 1.5; fill: none; }
  .root-node { stroke: #ffd700; stroke-width: 2.5; }
</style>
</head>
<body>
<svg id="graph" viewBox="0 0 800 400" width="100%" height="400" style="display:block; background:#0e1117;"></svg>
<script>
// --- extend helper ---
function extend(subClass, superClass) {
  var oldProto = subClass.prototype;
  var F = function() {};
  F.prototype = superClass.prototype;
  subClass.prototype = new F();
  subClass.prototype.constructor = subClass;
  subClass.superclass = superClass.prototype;
  // Copy all existing prototype properties that were defined before extend()
  // Always overwrite, even if superClass has the same property name,
  // because the subclass version should take precedence.
  var keys = Object.getOwnPropertyNames(oldProto);
  for (var i = 0; i < keys.length; i++) {
    if (keys[i] !== 'constructor') {
      subClass.prototype[keys[i]] = oldProto[keys[i]];
    }
  }
}

// --- LayoutEngine ---
__LAYOUT_JS__

// --- Graph data ---
var graphData = __GRAPH_JSON__;

// --- Build nodes and edges ---
var nodes = [];
var nodeMap = {};
var edges = [];

LayoutEngine.init();

var SVG = document.getElementById('graph');
var svgNS = 'http://www.w3.org/2000/svg';

graphData.nodes.forEach(function(n, i) {
  var angle = (i / Math.max(graphData.nodes.length, 1)) * 2 * Math.PI;
  var nodeType = n.is_root ? NodeType.ROOT_TASK : NodeType.TASK;
  var node = new Node(n.id, 400 + Math.cos(angle) * 120, 200 + Math.sin(angle) * 100, nodeType);
  node.label = n.label;
  node.isRoot = n.is_root;
  node.description = n.description;
  nodes.push(node);
  nodeMap[n.id] = node;
});

var edgeId = 1000;
graphData.edges.forEach(function(e) {
  var src = nodeMap[e.source];
  var tgt = nodeMap[e.target];
  if (src && tgt) {
    var edge = new Edge(edgeId++, src, tgt);
    edges.push(edge);
    nodes.push(edge);
  }
});

// --- Coordinate conversion ---
function screenToSVG(x, y) {
  var pt = SVG.createSVGPoint();
  pt.x = x; pt.y = y;
  var ctm = SVG.getScreenCTM();
  if (ctm) return pt.matrixTransform(ctm.inverse());
  return {x: x, y: y};
}

// --- Rendering ---
function clearSvg() {
  while (SVG.firstChild) SVG.removeChild(SVG.firstChild);
}

function createElem(tag, attrs) {
  var el = document.createElementNS(svgNS, tag);
  for (var k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

function render() {
  clearSvg();
  edges.forEach(function(edge) {
    var src = edge.node;
    var tgt = edge.otherNode;
    var path = createElem('path', {
      'class': 'edge-line',
      'd': 'M' + src.xPosition + ',' + src.yPosition +
           ' Q' + edge.xPosition + ',' + edge.yPosition +
           ' ' + tgt.xPosition + ',' + tgt.yPosition
    });
    SVG.appendChild(path);
    var dx = tgt.xPosition - edge.xPosition;
    var dy = tgt.yPosition - edge.yPosition;
    var len = Math.sqrt(dx*dx + dy*dy) || 1;
    var ux = dx / len, uy = dy / len;
    var nodeR = tgt.isRoot ? 22 : 18;
    var tipX = tgt.xPosition - ux * (nodeR + 2);
    var tipY = tgt.yPosition - uy * (nodeR + 2);
    var aSize = 8;
    var bX = tipX - ux * aSize, bY = tipY - uy * aSize;
    var pX = -uy * aSize * 0.5, pY = ux * aSize * 0.5;
    SVG.appendChild(createElem('polygon', {
      'points': tipX + ',' + tipY + ' ' + (bX+pX) + ',' + (bY+pY) + ' ' + (bX-pX) + ',' + (bY-pY),
      'fill': '#4a9eff'
    }));
  });
  graphData.nodes.forEach(function(n) {
    var node = nodeMap[n.id];
    if (!node) return;
    var r = node.isRoot ? 22 : 18;
    var circle = createElem('circle', {
      'class': 'node-circle' + (node.isRoot ? ' root-node' : ''),
      'cx': node.xPosition, 'cy': node.yPosition, 'r': r,
      'fill': node.isRoot ? '#1a5c1a' : '#1a3a5c',
      'stroke': node.isRoot ? '#ffd700' : '#4a9eff',
      'stroke-width': node.isRoot ? 2.5 : 1.5,
      'data-id': n.id
    });
    SVG.appendChild(circle);
    var label = createElem('text', {
      'class': 'node-label',
      'x': node.xPosition, 'y': node.yPosition + r + 14
    });
    label.textContent = n.label;
    SVG.appendChild(label);
  });
}

// --- Drag handling ---
var dragNode = null;
var dragStartX = 0, dragStartY = 0;
var isDragging = false;
var DRAG_THRESHOLD = 5;

SVG.addEventListener('mousedown', function(e) {
  if (e.target.classList && e.target.classList.contains('node-circle')) {
    var id = e.target.getAttribute('data-id');
    dragNode = nodeMap[id];
    if (dragNode) {
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      isDragging = false;
      e.preventDefault();
    }
  }
});

SVG.addEventListener('mousemove', function(e) {
  if (dragNode) {
    if (!isDragging) {
      var dx = Math.abs(e.clientX - dragStartX);
      var dy = Math.abs(e.clientY - dragStartY);
      if (Math.max(dx, dy) < DRAG_THRESHOLD) return;
      isDragging = true;
      dragNode.fixed = true;
      dragNode.setUnstoppable(true);
    }
    if (isDragging) {
      var pt = screenToSVG(e.clientX, e.clientY);
      dragNode.xPosition = pt.x;
      dragNode.yPosition = pt.y;
      dragNode.xVelocity = 0;
      dragNode.yVelocity = 0;
      dragNode.start();
      LayoutEngine.equilibrium = false;
      startAnimation();
      e.preventDefault();
    }
  }
});

window.addEventListener('mouseup', function(e) {
  if (dragNode) {
    dragNode.fixed = false;
    dragNode.setUnstoppable(false);
    dragNode = null;
    isDragging = false;
  }
});

// --- Animation loop ---
var running = false;

function engine() {
  if (!LayoutEngine.equilibrium) {
    LayoutEngine.layout(nodes);
    render();
  }
  if (LayoutEngine.equilibrium) {
    running = false;
  } else {
    window.requestAnimationFrame(engine);
  }
}

function startAnimation() {
  if (!running) {
    running = true;
    LayoutEngine.equilibrium = false;
    window.requestAnimationFrame(engine);
  }
}

render();
startAnimation();
</script>
</body>
</html>"""
    html = html.replace("__LAYOUT_JS__", load_layout_engine())
    html = html.replace("__GRAPH_JSON__", graph_json)
    return html


# ---------------------------------------------------------------
# Layout
# ---------------------------------------------------------------

col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("Workflows")

    workflows = list_workflows()
    names = [w["name"] for w in workflows] if workflows else []

    if st.button("+ New workflow", use_container_width=True):
        st.session_state.selected = "__new__"
        st.session_state.content = json.dumps({
            "WORKFLOW": "NewWorkflow",
            "WAREHOUSE": "COMPUTE_WH",
            "TASK_TIMEOUT": 3600000,
            "MAX_FAILURES": 3,
            "TASKS": []
        }, indent=2)
        st.session_state.pop("workflow_selector", None)
        st.experimental_rerun()

    if not names:
        st.caption("No workflows yet. Create one above.")
    else:
        selected = st.radio(
            "Select a workflow",
            options=names,
            key="workflow_selector",
            label_visibility="collapsed",
        )
        if selected:
            if "selected" not in st.session_state or st.session_state.selected != selected:
                content = load_workflow(selected)
                st.session_state.selected = selected
                st.session_state.content = content if content else ""
                st.session_state.modified = False

with col_right:
    if "selected" not in st.session_state or not st.session_state.selected:
        st.info("Select a workflow from the list or create a new one.")
        st.stop()

    is_new = st.session_state.selected == "__new__"
    title = "New workflow" if is_new else st.session_state.selected
    st.subheader(title)

    parsed, error = validate_json(st.session_state.content)

    # Graph visualization (top) + JSON editor (bottom) as tabs
    tab_graph, tab_json = st.tabs(["Graph", "JSON"])

    with tab_graph:
        if parsed and parsed.get("TASKS"):
            graph_data = extract_graph(parsed)
            components.html(render_graph_html(graph_data), height=400)
        elif error:
            st.error(f"Invalid JSON: {error}")
        else:
            st.info("No tasks defined yet.")

    with tab_json:
        edited = st.text_area(
            "JSON definition",
            value=st.session_state.content,
            height=500,
            key="json_editor",
        )

        if edited != st.session_state.content:
            st.session_state.content = edited
            st.session_state.modified = True

        # Re-validate after edit
        parsed, error = validate_json(st.session_state.content)
        if error:
            st.error(f"Invalid JSON: {error}")
        elif parsed:
            st.success("Valid JSON")
            tasks = parsed.get("TASKS", [])
            root = next((t for t in tasks if t.get("is_root") or t.get("schedule")), None)
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Tasks", len(tasks))
            with col_m2:
                st.metric("Root task", root.get("name", "?") if root else "—")
            with col_m3:
                st.metric("Schedule", root.get("schedule", "—") if root else "—")

    # Action buttons
    st.write("")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("Save", type="primary", disabled=not parsed, use_container_width=True):
            name = parsed.get("WORKFLOW", st.session_state.selected)
            result = save_workflow(name, st.session_state.content)
            st.cache_data.clear()
            st.session_state.selected = name
            st.session_state.modified = False
            st.success(f"Saved (CF_ID={result})")
    with col_btn2:
        if st.button("Delete", type="secondary", use_container_width=True):
            result = delete_workflow(st.session_state.selected)
            st.cache_data.clear()
            del st.session_state.selected
            del st.session_state.content
            st.success(result)
            st.experimental_rerun()
    with col_btn3:
        if st.session_state.get("modified"):
            st.caption("Unsaved changes")
