"""
Thesis Engine
=============
The long-term memory of Atlas.

A stock is not a report. It is a monitored hypothesis tree.
Each node tracks confidence, evidence, and overturn conditions.

This allows the Agent to know: "Today's news should impact WHICH judgment?"
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from atlas.models import ThesisTree, ThesisNode


class ThesisEngine:
    """Manages investment hypothesis trees for tracked stocks."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, ThesisTree] = {}

    def load(self, ticker: str) -> ThesisTree:
        """Load thesis tree from disk or create default."""
        if ticker in self._cache:
            return self._cache[ticker]

        path = self.data_dir / f"thesis_{ticker.lower()}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tree = ThesisTree.model_validate(data)
        else:
            tree = self._create_default_tree(ticker)

        self._cache[ticker] = tree
        return tree

    def save(self, ticker: str) -> None:
        """Persist thesis tree to disk."""
        tree = self._cache.get(ticker)
        if not tree:
            return
        path = self.data_dir / f"thesis_{ticker.lower()}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tree.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def update_node_confidence(
        self,
        ticker: str,
        node_id: str,
        new_confidence: float,
        reason: str,
        evidence_id: Optional[str] = None
    ) -> ThesisNode:
        """
        Update confidence with full audit trail.
        This is the ONLY way to modify formal thesis — enforceable by orchestrator.
        """
        tree = self.load(ticker)
        node = tree.update_confidence(node_id, new_confidence, reason)

        # Record what changed and why
        if evidence_id:
            node.contradicting_evidence.append(evidence_id)

        self.save(ticker)
        return node

    def assess_impact(self, ticker: str, event_description: str) -> Dict:
        """
        Assess which nodes are most exposed to a given event.
        Returns ranked list of vulnerable hypotheses.
        """
        tree = self.load(ticker)
        at_risk = tree.at_risk_nodes()

        return {
            "ticker": ticker,
            "overall_direction": tree.overall_direction,
            "at_risk_count": len(at_risk),
            "at_risk_nodes": [
                {"id": n.node_id, "hypothesis": n.hypothesis, "confidence": n.confidence}
                for n in at_risk
            ],
            "event": event_description,
        }

    def _create_default_tree(self, ticker: str) -> ThesisTree:
        """Create a sample thesis tree for CATL."""
        if ticker.upper() in ["CATL", "300750.SZ", "宁德时代"]:
            return self._catl_tree()
        return ThesisTree(ticker=ticker, overall_direction="neutral")

    def _catl_tree(self) -> ThesisTree:
        """CATL investment thesis — the demo case."""
        root = ThesisNode(
            node_id="root",
            ticker="CATL",
            hypothesis="宁德时代长期投资价值",
            confidence=75.0,
            key_variables=["全球动力电池市占率", "欧洲出海进度", "储能业务增速"],
            overturn_conditions=["市占率连续两季度下滑", "欧洲政策重大不利变化"],
        )

        h1 = ThesisNode(
            node_id="H1",
            ticker="CATL",
            hypothesis="欧洲销量保持两位数增长 (>10% YoY)",
            confidence=78.0,
            key_variables=["欧洲新能源车渗透率", "CATL欧洲装机量", "关税政策"],
            supporting_evidence=["ev_2024q3_eu_sales"],
            overturn_conditions=["连续两季度欧洲销量增速<5%", "欧盟征收>20%关税"],
            parent_id="root",
        )

        h2 = ThesisNode(
            node_id="H2",
            ticker="CATL",
            hypothesis="海外毛利率保持 >20%",
            confidence=81.0,
            key_variables=["海外售价", "原材料成本", "运费/关税"],
            supporting_evidence=["ev_2024q2_gm"],
            overturn_conditions=["海外毛利率连续两季度<18%"],
            parent_id="root",
        )

        h3 = ThesisNode(
            node_id="H3",
            ticker="CATL",
            hypothesis="储能成为第二增长曲线",
            confidence=72.0,
            key_variables=["储能订单增速", "储能毛利率", "美国大储政策"],
            supporting_evidence=["ev_2024q1_storage"],
            overturn_conditions=["储能收入占比连续下滑", "美国IRA政策取消"],
            parent_id="root",
        )

        h4 = ThesisNode(
            node_id="H4",
            ticker="CATL",
            hypothesis="全球市占率保持稳定 (>35%)",
            confidence=84.0,
            key_variables=["全球装机量", "竞争对手份额", "技术迭代速度"],
            supporting_evidence=["ev_2024q3_share"],
            overturn_conditions=["市占率连续两季度<33%", "固态电池技术被颠覆"],
            parent_id="root",
        )

        root.children_ids = ["H1", "H2", "H3", "H4"]

        return ThesisTree(
            ticker="CATL",
            overall_direction="bullish",
            nodes={
                "root": root,
                "H1": h1,
                "H2": h2,
                "H3": h3,
                "H4": h4,
            },
            root_id="root",
        )
