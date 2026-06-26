import * as vscode from 'vscode';
import * as path from 'path';

export class BehaviorTreeEditor implements vscode.Disposable {
    private context: vscode.ExtensionContext;
    private editors: Map<string, vscode.WebviewPanel> = new Map();

    constructor(context: vscode.ExtensionContext) {
        this.context = context;

        // Register custom editor provider
        context.subscriptions.push(
            vscode.window.registerCustomEditorProvider(
                'qoocode.behaviorTree',
                new BehaviorTreeEditorProvider(context, this.editors),
                {
                    webviewOptions: {
                        retainContextWhenHidden: true
                    },
                    supportsMultipleEditorsPerDocument: false
                }
            )
        );
    }

    dispose(): void {
        this.editors.forEach(panel => panel.dispose());
        this.editors.clear();
    }
}

class BehaviorTreeEditorProvider implements vscode.CustomReadonlyEditorProvider {
    private context: vscode.ExtensionContext;
    private editors: Map<string, vscode.WebviewPanel>;

    constructor(context: vscode.ExtensionContext, editors: Map<string, vscode.WebviewPanel>) {
        this.context = context;
        this.editors = editors;
    }

    async openCustomDocument(
        uri: vscode.Uri,
        openContext: vscode.CustomDocumentOpenContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CustomDocument> {
        return new BTreeDocument(uri);
    }

    async resolveCustomEditor(
        document: vscode.CustomDocument,
        webviewPanel: vscode.WebviewPanel,
        token: vscode.CancellationToken
    ): Promise<void> {
        const doc = document as BTreeDocument;
        this.editors.set(doc.uri.toString(), webviewPanel);

        webviewPanel.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.file(path.join(this.context.extensionPath, 'webview', 'dist'))
            ]
        };

        // Read behavior tree JSON
        const rawContent = await vscode.workspace.fs.readFile(doc.uri);
        const treeJson = JSON.parse(Buffer.from(rawContent).toString('utf-8'));

        // Get webview content
        webviewPanel.webview.html = this.getWebviewContent(webviewPanel.webview, doc.uri);

        // Send the tree data to the webview once it's ready
        webviewPanel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.type) {
                    case 'ready':
                        // Send initial tree data
                        webviewPanel.webview.postMessage({
                            type: 'loadTree',
                            data: treeJson
                        });
                        break;

                    case 'saveTree':
                        // Save tree back to file
                        const updatedTree = JSON.stringify(message.data, null, 2);
                        await vscode.workspace.fs.writeFile(doc.uri, Buffer.from(updatedTree, 'utf-8'));
                        vscode.window.showInformationMessage('Behavior tree saved.');
                        break;

                    case 'addNode':
                        webviewPanel.webview.postMessage({
                            type: 'nodeAdded',
                            parentId: message.parentId,
                            nodeType: message.nodeType
                        });
                        break;

                    case 'deleteNode':
                        webviewPanel.webview.postMessage({
                            type: 'nodeDeleted',
                            nodeId: message.nodeId
                        });
                        break;

                    case 'error':
                        vscode.window.showErrorMessage(`Behavior Tree Editor: ${message.message}`);
                        break;
                }
            },
            undefined,
            this.context.subscriptions
        );

        // Watch for document changes from outside the editor
        const watcher = vscode.workspace.onDidChangeTextDocument(e => {
            if (e.document.uri.toString() === doc.uri.toString()) {
                try {
                    const content = e.document.getText();
                    const treeJson = JSON.parse(content);
                    webviewPanel.webview.postMessage({
                        type: 'loadTree',
                        data: treeJson
                    });
                } catch {
                    // JSON parse error — ignore, user may be mid-edit
                }
            }
        });
        this.context.subscriptions.push(watcher);
    }

    private getWebviewContent(webview: vscode.Webview, uri: vscode.Uri): string {
        // In production, load the built React app
        // For development, we inline a standalone HTML with React + React Flow via CDN
        const cspSource = webview.cspSource;
        const nonce = getNonce();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" 
          content="default-src 'none'; 
                   script-src 'nonce-${nonce}' https://unpkg.com; 
                   style-src 'unsafe-inline' https://unpkg.com;
                   font-src https://unpkg.com;
                   img-src ${cspSource} data:;">
    <title>Behavior Tree Editor</title>
    <style nonce="${nonce}">
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body, #root { width: 100%; height: 100%; overflow: hidden; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e2e;
            color: #cdd6f4;
        }
        #root {
            display: flex;
            flex-direction: column;
        }
        .toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #181825;
            border-bottom: 1px solid #313244;
            flex-shrink: 0;
        }
        .toolbar button {
            padding: 4px 12px;
            border: 1px solid #45475a;
            border-radius: 4px;
            background: #313244;
            color: #cdd6f4;
            cursor: pointer;
            font-size: 12px;
        }
        .toolbar button:hover { background: #45475a; }
        .toolbar button.primary { background: #89b4fa; color: #1e1e2e; border-color: #89b4fa; }
        .toolbar button.danger { background: #f38ba8; color: #1e1e2e; border-color: #f38ba8; }
        .toolbar .separator { width: 1px; height: 20px; background: #45475a; margin: 0 4px; }
        .toolbar .title { font-weight: 600; margin-right: 8px; }
        .canvas-container {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        .node-palette {
            position: absolute;
            top: 10px;
            left: 10px;
            background: #181825;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 8px;
            z-index: 10;
            min-width: 160px;
        }
        .node-palette h4 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #a6adc8;
            margin-bottom: 6px;
            padding: 0 4px;
        }
        .node-palette .palette-item {
            padding: 6px 8px;
            border-radius: 4px;
            cursor: grab;
            font-size: 12px;
            margin: 2px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .node-palette .palette-item:hover { background: #313244; }
        .node-palette .palette-item .dot {
            width: 8px; height: 8px; border-radius: 50%;
        }
        .dot.composite { background: #89b4fa; }
        .dot.decorator { background: #f9e2af; }
        .dot.action { background: #a6e3a1; }
        .dot.condition { background: #cba6f7; }
        
        /* ReactFlow overrides for dark theme */
        .react-flow__node {
            border-radius: 8px !important;
            font-size: 12px !important;
        }
        .react-flow__background { background: #1e1e2e !important; }
        .react-flow__controls button {
            background: #313244 !important;
            border-color: #45475a !important;
            color: #cdd6f4 !important;
        }
    </style>
</head>
<body>
    <div id="root">
        <div class="toolbar">
            <span class="title">🌳 Behavior Tree Editor</span>
            <span class="separator"></span>
            <button onclick="undo()" title="Undo (Ctrl+Z)">↩ Undo</button>
            <button onclick="redo()" title="Redo (Ctrl+Shift+Z)">↪ Redo</button>
            <span class="separator"></span>
            <button onclick="fitView()" title="Fit view">⊞ Fit</button>
            <button onclick="autoLayout()" title="Auto layout">⚡ Auto Layout</button>
            <span class="separator"></span>
            <button class="primary" onclick="saveTree()">💾 Save</button>
        </div>
        <div class="canvas-container" id="canvas">
            <div class="node-palette" id="palette">
                <h4>Composite</h4>
                <div class="palette-item" draggable="true" data-type="Sequence">
                    <span class="dot composite"></span> Sequence (→)
                </div>
                <div class="palette-item" draggable="true" data-type="Fallback">
                    <span class="dot composite"></span> Fallback (?)
                </div>
                <div class="palette-item" draggable="true" data-type="Parallel">
                    <span class="dot composite"></span> Parallel (⇉)
                </div>
                <h4>Decorator</h4>
                <div class="palette-item" draggable="true" data-type="Inverter">
                    <span class="dot decorator"></span> Inverter (¬)
                </div>
                <div class="palette-item" draggable="true" data-type="Retry">
                    <span class="dot decorator"></span> Retry (↻)
                </div>
                <div class="palette-item" draggable="true" data-type="Timeout">
                    <span class="dot decorator"></span> Timeout (⏱)
                </div>
                <h4>Action</h4>
                <div class="palette-item" draggable="true" data-type="Action">
                    <span class="dot action"></span> Action
                </div>
                <h4>Condition</h4>
                <div class="palette-item" draggable="true" data-type="Condition">
                    <span class="dot condition"></span> Condition
                </div>
            </div>
        </div>
    </div>

    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js" nonce="${nonce}"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" nonce="${nonce}"></script>
    <script nonce="${nonce}">
        // Behavior Tree Editor — standalone WebView script
        // This is a simplified inline version; the full React app is in the webview/ directory
        
        const vscode = acquireVsCodeApi();
        let treeData = null;
        let undoStack = [];
        let redoStack = [];
        
        // Notify VS Code that the webview is ready
        vscode.postMessage({ type: 'ready' });
        
        window.addEventListener('message', (event) => {
            const message = event.data;
            switch (message.type) {
                case 'loadTree':
                    pushUndo(treeData);
                    treeData = message.data;
                    renderTree();
                    break;
                case 'nodeAdded':
                    // Handle node added confirmation
                    break;
                case 'nodeDeleted':
                    // Handle node deleted confirmation
                    break;
            }
        });
        
        function pushUndo(data) {
            if (data) {
                undoStack.push(JSON.parse(JSON.stringify(data)));
                redoStack = [];
            }
        }
        
        function undo() {
            if (undoStack.length > 0) {
                redoStack.push(JSON.parse(JSON.stringify(treeData)));
                treeData = undoStack.pop();
                renderTree();
            }
        }
        
        function redo() {
            if (redoStack.length > 0) {
                undoStack.push(JSON.parse(JSON.stringify(treeData)));
                treeData = redoStack.pop();
                renderTree();
            }
        }
        
        function saveTree() {
            vscode.postMessage({ type: 'saveTree', data: treeData });
        }
        
        function fitView() {
            // Placeholder for React Flow fitView
        }
        
        function autoLayout() {
            if (!treeData || !treeData.root) return;
            pushUndo(treeData);
            layoutNodes(treeData.root, 0, 0, 1);
            renderTree();
        }
        
        function layoutNodes(node, x, y, siblingIndex) {
            node._x = x;
            node._y = y;
            if (node.children && node.children.length > 0) {
                const totalWidth = node.children.length * 200 - 200;
                let startX = x - totalWidth / 2;
                node.children.forEach((child, i) => {
                    layoutNodes(child, startX + i * 200, y + 120, i);
                });
            }
        }
        
        function renderTree() {
            const canvas = document.getElementById('canvas');
            // Remove old SVG
            const oldSvg = canvas.querySelector('svg.btree-svg');
            if (oldSvg) oldSvg.remove();
            
            if (!treeData || !treeData.root) {
                canvas.innerHTML += '<div style="padding:40px;text-align:center;color:#6c7086;">No behavior tree loaded</div>';
                return;
            }
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.classList.add('btree-svg');
            svg.style.width = '100%';
            svg.style.height = '100%';
            svg.style.position = 'absolute';
            svg.style.top = '0';
            svg.style.left = '0';
            
            // Auto-layout if not positioned
            if (treeData.root._x === undefined) {
                layoutNodes(treeData.root, 500, 60, 0);
            }
            
            renderNode(svg, treeData.root, null);
            canvas.appendChild(svg);
            
            // Make SVG pannable
            let isPanning = false;
            let startX, startY, viewX = 0, viewY = 0;
            
            svg.addEventListener('mousedown', (e) => {
                if (e.target === svg) {
                    isPanning = true;
                    startX = e.clientX - viewX;
                    startY = e.clientY - viewY;
                    svg.style.cursor = 'grabbing';
                }
            });
            
            svg.addEventListener('mousemove', (e) => {
                if (isPanning) {
                    viewX = e.clientX - startX;
                    viewY = e.clientY - startY;
                    const g = svg.querySelector('g.transform-group');
                    if (g) g.setAttribute('transform', \`translate(\${viewX}, \${viewY})\`);
                }
            });
            
            svg.addEventListener('mouseup', () => {
                isPanning = false;
                svg.style.cursor = 'default';
            });
            
            svg.addEventListener('wheel', (e) => {
                e.preventDefault();
                const scale = 1 - e.deltaY * 0.001;
                const g = svg.querySelector('g.transform-group');
                if (g) {
                    const current = g.getAttribute('transform') || '';
                    g.setAttribute('transform', current + \` scale(\${Math.max(0.3, Math.min(3, scale))})\`);
                }
            });
        }
        
        function renderNode(svg, node, parentNode) {
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            
            // Wrap in a transform group if root
            if (!parentNode) {
                const transformGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                transformGroup.classList.add('transform-group');
                svg.appendChild(transformGroup);
                transformGroup.appendChild(g);
            } else {
                svg.appendChild(g);
            }
            
            const x = node._x || 0;
            const y = node._y || 0;
            const width = 140;
            const height = 50;
            const rx = 8;
            
            // Colors by node type
            const colors = {
                'Sequence': { fill: '#89b4fa', text: '#1e1e2e' },
                'Fallback': { fill: '#f9e2af', text: '#1e1e2e' },
                'Parallel': { fill: '#94e2d5', text: '#1e1e2e' },
                'Inverter': { fill: '#f9e2af', text: '#1e1e2e' },
                'Retry': { fill: '#f9e2af', text: '#1e1e2e' },
                'Timeout': { fill: '#f9e2af', text: '#1e1e2e' },
                'Action': { fill: '#a6e3a1', text: '#1e1e2e' },
                'Condition': { fill: '#cba6f7', text: '#1e1e2e' }
            };
            
            const color = colors[node.type] || { fill: '#585b70', text: '#cdd6f4' };
            
            // Draw edge from parent
            if (parentNode) {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', (parentNode._x || 0));
                line.setAttribute('y1', (parentNode._y || 0) + height);
                line.setAttribute('x2', x);
                line.setAttribute('y2', y);
                line.setAttribute('stroke', '#585b70');
                line.setAttribute('stroke-width', '2');
                g.appendChild(line);
            }
            
            // Node rectangle
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x - width/2);
            rect.setAttribute('y', y);
            rect.setAttribute('width', width);
            rect.setAttribute('height', height);
            rect.setAttribute('rx', rx);
            rect.setAttribute('fill', color.fill);
            rect.setAttribute('stroke', '#45475a');
            rect.setAttribute('stroke-width', '1.5');
            rect.setAttribute('filter', 'drop-shadow(2px 2px 4px rgba(0,0,0,0.3))');
            rect.style.cursor = 'pointer';
            
            rect.addEventListener('click', (e) => {
                e.stopPropagation();
                selectNode(node);
            });
            
            rect.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                const newName = prompt('Node name:', node.name);
                if (newName) {
                    pushUndo(treeData);
                    node.name = newName;
                    renderTree();
                }
            });
            
            g.appendChild(rect);
            
            // Node label
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', y + height/2 + 5);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', color.text);
            text.setAttribute('font-size', '13');
            text.setAttribute('font-weight', '600');
            text.textContent = node.name || node.type;
            text.style.pointerEvents = 'none';
            text.style.fontFamily = '-apple-system, BlinkMacSystemFont, sans-serif';
            g.appendChild(text);
            
            // Type badge
            const badge = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            badge.setAttribute('x', x);
            badge.setAttribute('y', y + 14);
            badge.setAttribute('text-anchor', 'middle');
            badge.setAttribute('fill', color.text);
            badge.setAttribute('font-size', '10');
            badge.setAttribute('opacity', '0.7');
            badge.textContent = node.type;
            badge.style.pointerEvents = 'none';
            badge.style.fontFamily = '-apple-system, BlinkMacSystemFont, sans-serif';
            g.appendChild(badge);
            
            // Render children
            if (node.children) {
                node.children.forEach(child => renderNode(svg, child, node));
            }
            
            // Add button for composite nodes
            if (['Sequence', 'Fallback', 'Parallel'].includes(node.type)) {
                const addBtn = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                addBtn.setAttribute('cx', x + width/2 - 10);
                addBtn.setAttribute('cy', y + height - 10);
                addBtn.setAttribute('r', '8');
                addBtn.setAttribute('fill', '#313244');
                addBtn.setAttribute('stroke', '#45475a');
                addBtn.style.cursor = 'pointer';
                
                const addText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                addText.setAttribute('x', x + width/2 - 10);
                addText.setAttribute('y', y + height - 6);
                addText.setAttribute('text-anchor', 'middle');
                addText.setAttribute('fill', '#cdd6f4');
                addText.setAttribute('font-size', '12');
                addText.textContent = '+';
                addText.style.pointerEvents = 'none';
                
                addBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    addChildNode(node);
                });
                
                g.appendChild(addBtn);
                g.appendChild(addText);
            }
        }
        
        function selectNode(node) {
            // Highlight selected node and show properties
            document.querySelectorAll('rect').forEach(r => {
                r.setAttribute('stroke-width', '1.5');
                r.setAttribute('stroke', '#45475a');
            });
            // Re-render to reset, then highlight — simplified approach
            renderTree();
            const rects = document.querySelectorAll('rect');
            rects.forEach(r => {
                // Match by position — simplified
                if (Math.abs(parseFloat(r.getAttribute('x')) + 70 - (node._x || 0)) < 5) {
                    r.setAttribute('stroke', '#89b4fa');
                    r.setAttribute('stroke-width', '3');
                }
            });
        }
        
        function addChildNode(parentNode) {
            pushUndo(treeData);
            const newNode = {
                type: 'Action',
                name: 'NewAction',
                children: []
            };
            if (!parentNode.children) parentNode.children = [];
            parentNode.children.push(newNode);
            renderTree();
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                undo();
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
                e.preventDefault();
                redo();
            } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveTree();
            } else if (e.key === 'Delete' && treeData) {
                // Delete selected node — simplified
            }
        });
        
        // Drag and drop from palette
        const paletteItems = document.querySelectorAll('.palette-item');
        paletteItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.getAttribute('data-type'));
            });
        });
        
        const canvas = document.getElementById('canvas');
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const nodeType = e.dataTransfer.getData('text/plain');
            if (nodeType && treeData) {
                pushUndo(treeData);
                if (!treeData.root.children) treeData.root.children = [];
                treeData.root.children.push({
                    type: nodeType,
                    name: 'New' + nodeType,
                    children: []
                });
                renderTree();
            }
        });
        
        console.log('Behavior Tree Editor initialized');
    </script>
</body>
</html>`;
    }
}

class BTreeDocument implements vscode.CustomDocument {
    uri: vscode.Uri;

    constructor(uri: vscode.Uri) {
        this.uri = uri;
    }

    dispose(): void {}
}

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 64; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
