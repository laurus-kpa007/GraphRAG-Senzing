#!/usr/bin/env python3
"""
GraphRAG Knowledge Graph Visualizer
그래프 엔티티와 관계를 인터랙티브 HTML로 시각화합니다.
"""

import json
import pathlib
import tomllib
from typing import Any

import networkx as nx


def load_config(config_path: str = "config.toml") -> dict:
    """Load configuration from TOML file."""
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def load_entities(ent_path: pathlib.Path) -> dict[str, dict]:
    """Load entities from JSONL file."""
    entities = {}
    if not ent_path.exists():
        print(f"⚠️  Entity file not found: {ent_path}")
        return entities

    with open(ent_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ent = json.loads(line)
            key = ent.get("lemma_key", ent.get("text", ""))
            entities[key] = ent

    print(f"✓ Loaded {len(entities)} entities from {ent_path.name}")
    return entities


def load_erkg_graph(erkg_path: pathlib.Path) -> nx.DiGraph:
    """Load Entity-Relation Knowledge Graph."""
    G = nx.DiGraph()

    if not erkg_path.exists():
        print(f"⚠️  ERKG file not found: {erkg_path}")
        return G

    with open(erkg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Add nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id", node.get("uid"))
            G.add_node(
                node_id,
                label=node.get("label", node.get("text", str(node_id))),
                **{k: v for k, v in node.items() if k not in ("id", "uid", "label")}
            )

    # Add edges
    if "edges" in data:
        for edge in data["edges"]:
            src = edge.get("source", edge.get("from"))
            tgt = edge.get("target", edge.get("to"))
            rel = edge.get("relation", edge.get("label", "related"))
            G.add_edge(src, tgt, relation=rel)

    print(f"✓ Loaded ERKG: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def load_lex_graph(lex_path: pathlib.Path) -> nx.Graph:
    """Load Lexical Graph (TextRank)."""
    G = nx.Graph()

    if not lex_path.exists():
        print(f"⚠️  Lexical graph file not found: {lex_path}")
        return G

    with open(lex_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Add nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id", node.get("uid"))
            G.add_node(
                node_id,
                label=node.get("label", node.get("text", str(node_id))),
                score=node.get("score", node.get("rank", 0.0)),
                **{k: v for k, v in node.items() if k not in ("id", "uid", "label", "score")}
            )

    # Add edges
    if "edges" in data:
        for edge in data["edges"]:
            src = edge.get("source", edge.get("from"))
            tgt = edge.get("target", edge.get("to"))
            weight = edge.get("weight", 1.0)
            G.add_edge(src, tgt, weight=weight)

    print(f"✓ Loaded Lexical Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def visualize_with_pyvis(
    G: nx.Graph,
    output_path: str,
    title: str = "Knowledge Graph",
    height: str = "900px",
    width: str = "100%",
) -> None:
    """Create interactive HTML visualization using pyvis."""
    try:
        from pyvis.network import Network
    except ImportError:
        print("⚠️  pyvis not installed. Install with: pip install pyvis")
        return

    # Create pyvis network
    net = Network(
        height=height,
        width=width,
        bgcolor="#ffffff",
        font_color="#000000",
        directed=isinstance(G, nx.DiGraph),
    )

    # Configure physics
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.001,
        damping=0.09,
    )

    # Add nodes
    for node_id, attrs in G.nodes(data=True):
        label = attrs.get("label", str(node_id))
        score = attrs.get("score", attrs.get("count", 0))
        node_type = attrs.get("label_type", attrs.get("type", "default"))

        # Node size based on score/count
        size = min(10 + score * 2, 50)

        # Color by entity type
        color_map = {
            "PERSON": "#ff6b6b",
            "ORG": "#4ecdc4",
            "GPE": "#45b7d1",
            "LOC": "#96ceb4",
            "PRODUCT": "#ffeaa7",
            "EVENT": "#dfe6e9",
            "NOUN": "#a29bfe",
            "default": "#95a5a6",
        }
        color = color_map.get(node_type, color_map["default"])

        # Hover info
        title_text = f"{label}\nType: {node_type}\nScore: {score:.3f}"

        net.add_node(
            node_id,
            label=label,
            title=title_text,
            size=size,
            color=color,
        )

    # Add edges
    for src, tgt, attrs in G.edges(data=True):
        relation = attrs.get("relation", "")
        weight = attrs.get("weight", 1.0)
        edge_label = relation if relation else ""

        net.add_edge(
            src,
            tgt,
            label=edge_label,
            title=f"Weight: {weight:.3f}",
            width=max(1, min(weight * 2, 10)),
        )

    # Add title and controls
    net.heading = title

    # Save
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))
    print(f"✓ Saved interactive visualization: {output_path}")
    print(f"  Open in browser: file://{output_path.absolute()}")


def visualize_with_networkx(
    G: nx.Graph,
    output_path: str,
    title: str = "Knowledge Graph",
) -> None:
    """Create static visualization using matplotlib (fallback)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️  matplotlib not installed. Install with: pip install matplotlib")
        return

    plt.figure(figsize=(16, 12))
    plt.title(title, fontsize=16, pad=20)

    # Layout
    if G.number_of_nodes() > 100:
        pos = nx.spring_layout(G, k=0.5, iterations=20)
    else:
        pos = nx.spring_layout(G, k=1, iterations=50)

    # Node colors by type
    node_colors = []
    for node_id, attrs in G.nodes(data=True):
        node_type = attrs.get("label_type", attrs.get("type", "default"))
        color_map = {
            "PERSON": "#ff6b6b",
            "ORG": "#4ecdc4",
            "GPE": "#45b7d1",
            "LOC": "#96ceb4",
            "PRODUCT": "#ffeaa7",
            "NOUN": "#a29bfe",
            "default": "#95a5a6",
        }
        node_colors.append(color_map.get(node_type, color_map["default"]))

    # Node sizes
    node_sizes = []
    for node_id, attrs in G.nodes(data=True):
        score = attrs.get("score", attrs.get("count", 0))
        node_sizes.append(min(100 + score * 50, 1000))

    # Draw
    nx.draw_networkx_nodes(
        G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8
    )
    nx.draw_networkx_edges(G, pos, alpha=0.3, arrows=isinstance(G, nx.DiGraph))

    # Labels (only for top nodes)
    labels = {}
    node_scores = [(n, d.get("score", d.get("count", 0))) for n, d in G.nodes(data=True)]
    top_nodes = sorted(node_scores, key=lambda x: x[1], reverse=True)[:30]
    for node_id, _ in top_nodes:
        attrs = G.nodes[node_id]
        labels[node_id] = attrs.get("label", str(node_id))[:20]

    nx.draw_networkx_labels(G, pos, labels, font_size=8)

    plt.axis("off")
    plt.tight_layout()

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"✓ Saved static visualization: {output_path}")


def build_entity_cooccurrence_graph(entities: dict[str, dict]) -> nx.Graph:
    """Build entity co-occurrence graph from entity store.

    When ERKG/Lex graphs are not available, create a simple graph
    where entities are nodes and edges represent co-occurrence.
    """
    G = nx.Graph()

    # Add all entities as nodes
    for key, ent in entities.items():
        node_id = ent.get("uid", key)
        G.add_node(
            node_id,
            label=ent.get("text", key),
            label_type=ent.get("label", "ENTITY"),
            count=ent.get("count", 1),
            lemma_key=ent.get("lemma_key", key),
        )

    # Create edges between entities with similar types or high frequency
    # (This is a simple heuristic - better with actual co-occurrence data)
    sorted_ents = sorted(entities.values(), key=lambda x: x.get("count", 0), reverse=True)
    top_entities = sorted_ents[:min(100, len(sorted_ents))]  # Limit to top 100

    for i, ent1 in enumerate(top_entities):
        node1 = ent1.get("uid", ent1.get("lemma_key"))
        label1 = ent1.get("label", "")

        # Connect entities of the same type
        for ent2 in top_entities[i+1:i+6]:  # Connect to next 5 of same type
            node2 = ent2.get("uid", ent2.get("lemma_key"))
            label2 = ent2.get("label", "")

            if label1 == label2 and label1:  # Same entity type
                weight = min(ent1.get("count", 1), ent2.get("count", 1)) / max(ent1.get("count", 1), ent2.get("count", 1))
                G.add_edge(node1, node2, weight=weight)

    print(f"✓ Built entity co-occurrence graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def main():
    """Main visualization workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Visualize GraphRAG Knowledge Graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize ERKG (Entity-Relation Knowledge Graph)
  python visualize_graph.py --graph erkg

  # Visualize Lexical Graph
  python visualize_graph.py --graph lex

  # Visualize entities (fallback when ERKG/Lex not available)
  python visualize_graph.py --graph entities

  # Custom output path
  python visualize_graph.py --graph erkg --output my_graph.html

  # Static PNG instead of interactive HTML
  python visualize_graph.py --graph erkg --format png
        """,
    )

    parser.add_argument(
        "--graph",
        choices=["erkg", "lex", "entities"],
        default="entities",
        help="Which graph to visualize (default: entities)",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Config file path (default: config.toml)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: from config or data/output/<graph>.html)",
    )
    parser.add_argument(
        "--format",
        choices=["html", "png"],
        default="html",
        help="Output format (default: html)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine paths
    if args.graph == "erkg":
        graph_path = pathlib.Path(config["erkg"]["erkg_path"])
        default_output = config["vis"]["html_path"]
        title = "Entity-Relation Knowledge Graph (ERKG)"
    elif args.graph == "lex":
        graph_path = pathlib.Path(config["nlp"]["lex_path"])
        default_output = "data/output/lex.html"
        title = "Lexical Graph (TextRank)"
    else:  # entities
        graph_path = None
        default_output = "data/output/entities.html"
        title = "Entity Co-occurrence Graph"

    output_path = args.output or default_output
    if args.format == "png":
        output_path = output_path.replace(".html", ".png")

    print(f"\n{'=' * 60}")
    print(f"  GraphRAG Visualization Tool")
    print(f"  Graph: {args.graph}")
    print(f"  Format: {args.format}")
    print(f"{'=' * 60}\n")

    # Load entities first
    ent_path = pathlib.Path(config["ent"]["store_path"])
    entities = load_entities(ent_path)

    if not entities:
        print(f"\n⚠️  No entity data found. Run the pipeline first:")
        print(f"     python run_pipeline.py data/documents/\n")
        return

    # Load or build graph
    if args.graph == "erkg":
        G = load_erkg_graph(graph_path)
        if G.number_of_nodes() == 0:
            print(f"\n⚠️  ERKG not available. Falling back to entity graph.")
            print(f"     (ERKG requires strwythura pipeline)\n")
            G = build_entity_cooccurrence_graph(entities)
            title = "Entity Graph (standalone mode)"
    elif args.graph == "lex":
        G = load_lex_graph(graph_path)
        if G.number_of_nodes() == 0:
            print(f"\n⚠️  Lexical graph not available. Falling back to entity graph.")
            print(f"     (Lex graph requires strwythura pipeline)\n")
            G = build_entity_cooccurrence_graph(entities)
            title = "Entity Graph (standalone mode)"
    else:  # entities
        G = build_entity_cooccurrence_graph(entities)

    if G.number_of_nodes() == 0:
        print(f"\n⚠️  No graph data available.\n")
        return

    # Enrich nodes with entity info
    for node_id in G.nodes():
        if node_id in entities:
            ent = entities[node_id]
            G.nodes[node_id].update({
                "label_type": ent.get("label", ""),
                "count": ent.get("count", 0),
            })

    # Visualize
    print()
    if args.format == "html":
        visualize_with_pyvis(
            G,
            output_path,
            title=title,
            height=config["vis"]["html_height"],
            width=config["vis"]["html_width"],
        )
    else:
        visualize_with_networkx(G, output_path, title=title)

    print(f"\n{'=' * 60}")
    print(f"  Visualization complete!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
