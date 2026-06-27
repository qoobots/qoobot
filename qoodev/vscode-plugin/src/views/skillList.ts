import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface QooSkillItem {
    name: string;
    filePath: string;
    className: string;
    description?: string;
}

export class QooSkillList implements vscode.TreeDataProvider<SkillTreeItem>, vscode.Disposable {
    private _onDidChangeTreeData = new vscode.EventEmitter<SkillTreeItem | undefined>();
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
            const skillsDir = path.join(workspaceRoot, 'skills');
            if (fs.existsSync(skillsDir)) {
                this.watcher = vscode.workspace.createFileSystemWatcher(
                    new vscode.RelativePattern(skillsDir, '**/*.py')
                );
                this.watcher.onDidChange(() => this.refresh());
                this.watcher.onDidCreate(() => this.refresh());
                this.watcher.onDidDelete(() => this.refresh());
            }
        }
    }

    private getWorkspaceRoot(): string | undefined {
        const folders = vscode.workspace.workspaceFolders;
        return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: SkillTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<SkillTreeItem[]> {
        const workspaceRoot = this.getWorkspaceRoot();
        if (!workspaceRoot) return [];

        const skillsDir = path.join(workspaceRoot, 'skills');
        if (!fs.existsSync(skillsDir)) {
            return [new SkillTreeItem(
                'No skills directory',
                '',
                '',
                new vscode.ThemeIcon('info')
            )];
        }

        const skills = this.scanSkills(skillsDir, workspaceRoot);
        if (skills.length === 0) {
            const createItem = new SkillTreeItem(
                'Create a skill...',
                '',
                '',
                new vscode.ThemeIcon('add')
            );
            createItem.command = { command: 'qoodev.createSkill', title: 'Create Skill' };
            return [createItem];
        }

        return skills.map(skill => {
            const item = new SkillTreeItem(
                skill.name,
                skill.className,
                skill.description || skill.filePath,
                new vscode.ThemeIcon('symbol-class')
            );
            item.command = {
                command: 'vscode.open',
                title: 'Open Skill',
                arguments: [vscode.Uri.file(skill.filePath)]
            };
            return item;
        });
    }

    private scanSkills(dir: string, workspaceRoot: string): QooSkillItem[] {
        const skills: QooSkillItem[] = [];

        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            if (entry.isDirectory()) {
                const subDir = path.join(dir, entry.name);
                skills.push(...this.scanSkills(subDir, workspaceRoot));
            } else if (entry.name.endsWith('.py') && !entry.name.startsWith('__')) {
                const filePath = path.join(dir, entry.name);
                const content = fs.readFileSync(filePath, 'utf-8');
                const classMatch = content.match(/class\s+(\w+)\s*\(.*QooSkill.*\):/);
                if (classMatch) {
                    skills.push({
                        name: entry.name.replace('.py', ''),
                        filePath,
                        className: classMatch[1],
                        description: path.relative(workspaceRoot, filePath)
                    });
                }
            }
        }

        return skills;
    }

    dispose(): void {
        this.watcher?.dispose();
    }
}

class SkillTreeItem extends vscode.TreeItem {
    constructor(
        label: string,
        public readonly className: string,
        description: string,
        icon: vscode.ThemeIcon
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.description = description;
        this.iconPath = icon;
        this.tooltip = `${className}\n${description}`;
    }
}
