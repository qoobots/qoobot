import * as vscode from 'vscode';
import { QooLspClient } from './lsp/client';
import { QooCLI } from './cli/runner';
import { QooProjectExplorer } from './views/projectExplorer';
import { QooSkillList } from './views/skillList';
import { QooBehaviorTreeProvider } from './views/behaviorTreeList';
import { BehaviorTreeEditor } from './editors/behaviorTreeEditor';
import { registerCommands } from './commands';
import { SnippetProvider } from './snippets/provider';

let lspClient: QooLspClient;
let cli: QooCLI;

export function activate(context: vscode.ExtensionContext) {
    console.log('qoodev-vscode: activating...');

    // ============================================================
    // 1. Initialize CLI runner
    // ============================================================
    cli = new QooCLI(context);
    context.subscriptions.push(cli);

    // ============================================================
    // 2. Set context for when clauses
    // ============================================================
    updateProjectContext();

    // ============================================================
    // 3. LSP Client — language services (completion, diagnostics, hover)
    // ============================================================
    lspClient = new QooLspClient(context);
    lspClient.start();
    context.subscriptions.push(lspClient);

    // ============================================================
    // 4. Tree Views
    // ============================================================
    const projectExplorer = new QooProjectExplorer(context);
    vscode.window.registerTreeDataProvider('qoodev.projectExplorer', projectExplorer);
    context.subscriptions.push(projectExplorer);

    const skillList = new QooSkillList(context);
    vscode.window.registerTreeDataProvider('qoodev.skillList', skillList);
    context.subscriptions.push(skillList);

    const behaviorTreeProvider = new QooBehaviorTreeProvider(context);
    vscode.window.registerTreeDataProvider('qoodev.behaviorTrees', behaviorTreeProvider);
    context.subscriptions.push(behaviorTreeProvider);

    // ============================================================
    // 5. Behavior Tree Editor (Custom Editor for .btree / .bt.json)
    // ============================================================
    const btEditor = new BehaviorTreeEditor(context);
    context.subscriptions.push(btEditor);

    // ============================================================
    // 6. Code Snippets
    // ============================================================
    const snippetProvider = new SnippetProvider(context);
    context.subscriptions.push(snippetProvider);

    // ============================================================
    // 7. Commands
    // ============================================================
    registerCommands(context, cli, lspClient, behaviorTreeProvider);

    // ============================================================
    // 8. Status Bar
    // ============================================================
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'qoodev.doctor';
    statusBar.text = '$(robot-view) qoodev';
    statusBar.tooltip = 'qoodev — Robot Skill Development';
    statusBar.show();
    context.subscriptions.push(statusBar);

    // ============================================================
    // 9. Watchers — refresh context on workspace changes
    // ============================================================
    context.subscriptions.push(
        vscode.workspace.onDidChangeWorkspaceFolders(() => updateProjectContext()),
        vscode.workspace.onDidOpenTextDocument(() => updateProjectContext())
    );

    console.log('qoodev-vscode: activated');
}

export function deactivate() {
    if (lspClient) {
        lspClient.stop();
    }
}

function updateProjectContext() {
    const isProject = isqoodevProject();
    vscode.commands.executeCommand('setContext', 'qoodev.isqoodevProject', isProject);
}

function isqoodevProject(): boolean {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        return false;
    }
    // Check for qoo.toml or pyproject.toml with [tool.qoo] section
    const fs = require('fs');
    const path = require('path');
    for (const folder of workspaceFolders) {
        const qooToml = path.join(folder.uri.fsPath, 'qoo.toml');
        const pyprojectToml = path.join(folder.uri.fsPath, 'pyproject.toml');
        if (fs.existsSync(qooToml)) return true;
        if (fs.existsSync(pyprojectToml)) {
            const content = fs.readFileSync(pyprojectToml, 'utf-8');
            if (content.includes('[tool.qoo]')) return true;
        }
    }
    return false;
}
