import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class QooBehaviorTreeProvider implements vscode.TreeDataProvider<BTreeItem>, vscode.Disposable {
    private _onDidChangeTreeData = new vscode.EventEmitter<BTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private context: vscode.ExtensionContext;
    private watcher: vscode.FileSystemWatcher | undefined;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.setupWatcher();
    }

    private setupWatcher(): void {
        const workspaceRoot = this.getWorkspaceRoot();
        if (workspaceRoot) {
            const pattern = new vscode.RelativePattern(workspaceRoot, '**/*.{btree,bt.json}');
            this.watcher = vscode.workspace.createFileSystemWatcher(pattern);
            this.watcher.onDidChange(() => this.refresh());
            this.watcher.onDidCreate(() => this.refresh());
            this.watcher.onDidDelete(() => this.refresh());
        }
    }

    private getWorkspaceRoot(): string | undefined {
        const folders = vscode.workspace.workspaceFolders;
        return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: BTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<BTreeItem[]> {
        const workspaceRoot = this.getWorkspaceRoot();
        if (!workspaceRoot) return [];

        const trees = this.findBehaviorTrees(workspaceRoot);

        if (trees.length === 0) {
            const createItem = new BTreeItem(
                'Create behavior tree...',
                '',
                new vscode.ThemeIcon('add')
            );
            createItem.command = { command: 'qoodev.openBehaviorTree', title: 'Create Behavior Tree' };
            return [createItem];
        }

        return trees.map(treePath => {
            const relativePath = path.relative(workspaceRoot, treePath);
            const name = path.basename(treePath, path.extname(treePath));

            let treeName = name;
            try {
                const content = JSON.parse(fs.readFileSync(treePath, 'utf-8'));
                treeName = content.name || name;
            } catch {
                // Use filename as fallback
            }

            const item = new BTreeItem(
                treeName,
                relativePath,
                new vscode.ThemeIcon('type-hierarchy')
            );
            item.command = {
                command: 'vscode.openWith',
                title: 'Open Behavior Tree',
                arguments: [vscode.Uri.file(treePath), 'qoodev.behaviorTree']
            };
            item.contextValue = 'behaviorTree';
            return item;
        });
    }

    private findBehaviorTrees(root: string): string[] {
        const results: string[] = [];

        function walk(dir: string) {
            if (!fs.existsSync(dir)) return;
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
                    walk(path.join(dir, entry.name));
                } else if (entry.name.endsWith('.btree') || entry.name.endsWith('.bt.json')) {
                    results.push(path.join(dir, entry.name));
                }
            }
        }

        walk(root);
        return results;
    }

    dispose(): void {
        this.watcher?.dispose();
    }
}

class BTreeItem extends vscode.TreeItem {
    constructor(
        label: string,
        description: string,
        icon: vscode.ThemeIcon
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.description = description;
        this.iconPath = icon;
        this.tooltip = description;
    }
}
