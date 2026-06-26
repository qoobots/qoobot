import * as vscode from 'vscode';

export class SnippetProvider implements vscode.Disposable {
    private context: vscode.ExtensionContext;
    private disposables: vscode.Disposable[] = [];

    constructor(context: vscode.ExtensionContext) {
        this.context = context;

        // Register completion provider for Python files in qoocode projects
        this.disposables.push(
            vscode.languages.registerCompletionItemProvider(
                { scheme: 'file', language: 'python' },
                new QooCompletionProvider(),
                '.', '('
            )
        );
    }

    dispose(): void {
        this.disposables.forEach(d => d.dispose());
    }
}

class QooCompletionProvider implements vscode.CompletionItemProvider {
    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.CompletionItem[] {
        const linePrefix = document.lineAt(position).text.substring(0, position.character);
        const items: vscode.CompletionItem[] = [];

        // Check if we're in a qoocode project
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) return items;

        // QooSkill class completion
        if (linePrefix.match(/class\s+\w*$/)) {
            const skillItem = new vscode.CompletionItem('QooSkill', vscode.CompletionItemKind.Class);
            skillItem.detail = 'qoobot-sdk';
            skillItem.documentation = new vscode.MarkdownString(
                'Base class for all robot skills.\n\n```python\nclass MySkill(QooSkill):\n    async def setup(self): ...\n    async def loop(self): ...\n    async def teardown(self): ...\n```'
            );
            skillItem.insertText = new vscode.SnippetString('MySkill(QooSkill):\n    """${1:Skill description}"""\n\n    async def setup(self):\n        ${2:pass}\n\n    async def loop(self):\n        ${3:pass}\n\n    async def teardown(self):\n        ${4:pass}');
            items.push(skillItem);
        }

        // SDK API completions
        if (linePrefix.includes('from qoobot_sdk') || linePrefix.includes('import qoobot_sdk')) {
            items.push(
                this.createCompletion('QooSkill', vscode.CompletionItemKind.Class, 'Base skill class'),
                this.createCompletion('SkillConfig', vscode.CompletionItemKind.Class, 'Skill configuration'),
                this.createCompletion('Image', vscode.CompletionItemKind.Class, 'Camera image data'),
                this.createCompletion('PointCloud', vscode.CompletionItemKind.Class, 'LiDAR point cloud data'),
                this.createCompletion('JointStates', vscode.CompletionItemKind.Class, 'Robot joint states'),
                this.createCompletion('JointCommand', vscode.CompletionItemKind.Class, 'Joint control command'),
                this.createCompletion('EndEffectorTarget', vscode.CompletionItemKind.Class, 'End-effector pose target'),
                this.createCompletion('BrainOSClient', vscode.CompletionItemKind.Class, 'BrainOS communication client')
            );
        }

        // Method completions for QooSkill subclasses
        const text = document.getText();
        if (text.includes('class') && text.includes('QooSkill')) {
            if (linePrefix.trim().startsWith('async def')) {
                items.push(
                    this.createSnippetCompletion('setup', 'async def setup(self):\n    """Initialize skill resources."""\n    ${1:pass}'),
                    this.createSnippetCompletion('loop', 'async def loop(self):\n    """Main skill loop."""\n    ${1:pass}'),
                    this.createSnippetCompletion('teardown', 'async def teardown(self):\n    """Clean up resources."""\n    ${1:pass}'),
                    this.createSnippetCompletion('on_perception', 'async def on_perception(self, data):\n    """Handle perception data."""\n    ${1:pass}')
                );
            }
        }

        return items;
    }

    private createCompletion(label: string, kind: vscode.CompletionItemKind, detail: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, kind);
        item.detail = detail;
        return item;
    }

    private createSnippetCompletion(label: string, snippet: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Method);
        item.insertText = new vscode.SnippetString(snippet);
        item.detail = 'QooSkill lifecycle method';
        return item;
    }
}
