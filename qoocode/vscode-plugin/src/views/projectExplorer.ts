import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface QooProjectItem {
    name: string;
    type: 'folder' | 'skill' | 'service' | 'model' | 'config' | 'test' | 'btree';
    filePath?: string;
}

export class QooProjectExplorer implements vscode.TreeDataProvider<QooTreeItem>, vscode.Disposable {
    private _onDidChangeTreeData = new vscode.EventEmitter<QooTreeItem | undefined>();
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
            this.watcher = vscode.workspace.createFileSystemWatcher(
                new vscode.RelativePattern(workspaceRoot, '**/*')
            );
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

    getTreeItem(element: QooTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: QooTreeItem): Promise<QooTreeItem[]> {
        const workspaceRoot = this.getWorkspaceRoot();
        if (!workspaceRoot) return [];

        if (!element) {
            return this.getRootItems(workspaceRoot);
        }

        return this.getFolderItems(element.filePath || '');
    }

    private async getRootItems(root: string): Promise<QooTreeItem[]> {
        const items: QooTreeItem[] = [];

        // Scan for project structure
        const entries = fs.readdirSync(root, { withFileTypes: true });
        const dirs = entries.filter(e => e.isDirectory()).map(e => e.name);

        // Check if this is a qoocode project
        const isProject = fs.existsSync(path.join(root, 'qoo.toml')) ||
            (fs.existsSync(path.join(root, 'pyproject.toml')) &&
                fs.readFileSync(path.join(root, 'pyproject.toml'), 'utf-8').includes('[tool.qoo]'));

        if (isProject) {
            // Standard qoocode project layout
            if (dirs.includes('skills')) {
                items.push(new QooTreeItem('Skills', 'skills', vscode.TreeItemCollapsibleState.Collapsed, 'folder', root));
            }
            if (dirs.includes('services')) {
                items.push(new QooTreeItem('Services', 'services', vscode.TreeItemCollapsibleState.Collapsed, 'folder', root));
            }
            if (dirs.includes('models')) {
                items.push(new QooTreeItem('Models', 'models', vscode.TreeItemCollapsibleState.Collapsed, 'folder', root));
            }
            if (dirs.includes('behavior_trees') || dirs.includes('trees')) {
                items.push(new QooTreeItem('Behavior Trees', 'behavior_trees', vscode.TreeItemCollapsibleState.Collapsed, 'folder', root));
            }
            if (dirs.includes('tests')) {
                items.push(new QooTreeItem('Tests', 'tests', vscode.TreeItemCollapsibleState.Collapsed, 'folder', root));
            }

            // Config files
            if (fs.existsSync(path.join(root, 'qoo.toml'))) {
                items.push(new QooTreeItem('qoo.toml', 'qoo.toml', vscode.TreeItemCollapsibleState.None, 'config', root));
            }
            if (fs.existsSync(path.join(root, 'pyproject.toml'))) {
                items.push(new QooTreeItem('pyproject.toml', 'pyproject.toml', vscode.TreeItemCollapsibleState.None, 'config', root));
            }
        } else {
            // Not a qoocode project — show prompt to init
            items.push(new QooTreeItem(
                'Not a qoocode project',
                '',
                vscode.TreeItemCollapsibleState.None,
                'config',
                '',
                new vscode.ThemeIcon('warning')
            ));
            const initItem = new QooTreeItem(
                'Initialize qoocode project...',
                '',
                vscode.TreeItemCollapsibleState.None,
                'config',
                '',
                new vscode.ThemeIcon('add')
            );
            initItem.command = { command: 'qoocode.init', title: 'Init Project' };
            items.push(initItem);
        }

        return items;
    }

    private async getFolderItems(folderPath: string): Promise<QooTreeItem[]> {
        const items: QooTreeItem[] = [];

        if (!fs.existsSync(folderPath)) return items;

        // Resolve the full path
        const workspaceRoot = this.getWorkspaceRoot();
        const fullPath = path.isAbsolute(folderPath) ? folderPath : path.join(workspaceRoot || '', folderPath);

        const entries = fs.readdirSync(fullPath, { withFileTypes: true });

        for (const entry of entries) {
            const entryPath = path.join(fullPath, entry.name);
            const relativePath = path.relative(workspaceRoot || '', entryPath);

            if (entry.isDirectory()) {
                items.push(new QooTreeItem(
                    entry.name,
                    relativePath,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'folder',
                    entryPath
                ));
            } else {
                let type: QooProjectItem['type'] = 'config';
                if (entry.name.endsWith('.py')) type = 'skill';
                else if (entry.name.endsWith('.btree') || entry.name.endsWith('.bt.json')) type = 'btree';
                else if (entry.name.startsWith('test_')) type = 'test';

                const item = new QooTreeItem(
                    entry.name,
                    relativePath,
                    vscode.TreeItemCollapsibleState.None,
                    type,
                    entryPath
                );

                if (type === 'btree') {
                    item.command = {
                        command: 'vscode.openWith',
                        title: 'Open Behavior Tree',
                        arguments: [vscode.Uri.file(entryPath), 'qoocode.behaviorTree']
                    };
                } else {
                    item.command = {
                        command: 'vscode.open',
                        title: 'Open File',
                        arguments: [vscode.Uri.file(entryPath)]
                    };
                }

                items.push(item);
            }
        }

        return items;
    }

    dispose(): void {
        this.watcher?.dispose();
    }
}

class QooTreeItem extends vscode.TreeItem {
    filePath: string;

    constructor(
        public readonly label: string,
        public readonly id: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly itemType: QooProjectItem['type'],
        filePath: string,
        icon?: vscode.ThemeIcon
    ) {
        super(label, collapsibleState);
        this.filePath = filePath;

        this.iconPath = icon || this.getIconForType();
        this.contextValue = itemType;
        this.tooltip = filePath || label;
    }

    private getIconForType(): vscode.ThemeIcon {
        switch (this.itemType) {
            case 'folder': return new vscode.ThemeIcon('folder');
            case 'skill': return new vscode.ThemeIcon('symbol-class');
            case 'service': return new vscode.ThemeIcon('server');
            case 'model': return new vscode.ThemeIcon('symbol-structure');
            case 'config': return new vscode.ThemeIcon('settings');
            case 'test': return new vscode.ThemeIcon('beaker');
            case 'btree': return new vscode.ThemeIcon('type-hierarchy');
            default: return new vscode.ThemeIcon('file');
        }
    }
}
