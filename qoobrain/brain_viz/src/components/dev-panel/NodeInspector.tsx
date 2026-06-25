/**
 * src/components/dev-panel/NodeInspector.tsx — Behavior tree node inspector
 */
'use client';

import React, { useState } from 'react';
import { CodeEditor } from './CodeEditor';
import { Button } from '@/components/common/Button';

const SAMPLE_BT_XML = `<BehaviorTree>
  <Sequence name="pick_red_cup">
    <NavigateTo goal="above_cup" speed="0.5"/>
    <Detect target="red_cup" timeout_sec="3"/>
    <Pick target="red_cup" approach="top_down" force="0.3"/>
    <Place location="table_left" height="0.1"/>
    <Speak text="任务完成"/>
  </Sequence>
</BehaviorTree>`;

interface BTNode {
  type: string;
  name: string;
  children: BTNode[];
}

function parseBTSimple(xml: string): BTNode[] {
  const nodes: BTNode[] = [];
  const tagRegex = /<(\w+)\s+([^>]*?)\/?>/g;
  const closeRegex = /<\/(\w+)>/g;
  const stack: BTNode[] = [];
  let match;

  // Simple parser
  const lines = xml.split('\n');
  let currentParent: BTNode | null = null;

  for (const line of lines) {
    const trimmed = line.trim();
    const openMatch = /<(\w+)\s+([^>]*?)\/?>/.exec(trimmed);
    const selfCloseMatch = /<(\w+)\s+([^>]*?)\/>/.exec(trimmed);
    const closeMatch = /<\/(\w+)>/.exec(trimmed);

    if (selfCloseMatch) {
      const nameMatch = /name="([^"]*)"/.exec(selfCloseMatch[2]);
      const node: BTNode = {
        type: selfCloseMatch[1],
        name: nameMatch ? nameMatch[1] : selfCloseMatch[1],
        children: [],
      };
      if (currentParent) {
        currentParent.children.push(node);
      } else {
        nodes.push(node);
      }
    } else if (openMatch) {
      const nameMatch = /name="([^"]*)"/.exec(openMatch[2]);
      const node: BTNode = {
        type: openMatch[1],
        name: nameMatch ? nameMatch[1] : openMatch[1],
        children: [],
      };
      if (currentParent) {
        currentParent.children.push(node);
      } else {
        nodes.push(node);
      }
      if (openMatch[1] !== 'BehaviorTree') {
        // Not a leaf — push as new parent
        currentParent = node;
      }
    } else if (closeMatch) {
      // Pop up or stay
    }
  }

  return nodes;
}

function TreeNode({ node, depth = 0 }: { node: BTNode; depth?: number }) {
  const isControl = ['Sequence', 'Fallback', 'Parallel', 'ReactiveSequence'].includes(node.type);
  const isDecorator = ['Inverter', 'Retry', 'Timeout', 'ForceSuccess', 'ForceFailure'].includes(node.type);
  const isLeaf = !isControl && !isDecorator;

  const bgClass = isControl ? 'bg-blue-500/10 border-blue-500/20'
    : isDecorator ? 'bg-yellow-500/10 border-yellow-500/20'
    : 'bg-green-500/10 border-green-500/20';

  return (
    <div style={{ marginLeft: depth * 16 }}>
      <div className={`px-2 py-1 rounded text-xs border mb-0.5 ${bgClass}`}>
        <span className="text-brain-muted text-[10px]">{node.type}</span>
        <span className="text-brain-text ml-2 font-medium">{node.name}</span>
        {isLeaf && <span className="ml-2 text-[10px] text-green-400">动作</span>}
      </div>
      {node.children.map((child, i) => (
        <TreeNode key={i} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function NodeInspector() {
  const [xml, setXml] = useState(SAMPLE_BT_XML);
  const [parsed, setParsed] = useState<BTNode[]>([]);

  const handleParse = () => {
    try {
      const nodes = parseBTSimple(xml);
      setParsed(nodes);
    } catch {
      setParsed([]);
    }
  };

  return (
    <div className="space-y-3">
      <CodeEditor
        value={xml}
        onChange={setXml}
        language="xml"
        label="行为树 XML"
        height="160px"
      />
      <Button size="sm" onClick={handleParse}>
        解析行为树
      </Button>

      {parsed.length > 0 && (
        <div className="mt-3">
          <h3 className="text-xs text-brain-muted mb-2 uppercase tracking-wide">
            节点树
          </h3>
          <div className="space-y-0.5">
            {parsed.map((node, i) => (
              <TreeNode key={i} node={node} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
