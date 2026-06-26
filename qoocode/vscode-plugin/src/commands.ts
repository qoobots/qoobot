import * as vscode from 'vscode';
import { QooCLI } from '../cli/runner';
import { QooLspClient } from '../lsp/client';
import { QooBehaviorTreeProvider } from '../views/behaviorTreeList';

export function registerCommands(
    context: vscode.ExtensionContext,
    cli: QooCLI,
    lspClient: QooLspClient,
    btProvider: QooBehaviorTreeProvider
): void {
    const disposables = [
        // ── Project Init ────────────────────────────────────
        vscode.commands.registerCommand('qoocode.init', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Project name',
                placeHolder: 'my-robot-skill'
            });
            if (!name) return;

            const type = await vscode.window.showQuickPick(['skill', 'service', 'model'], {
                placeHolder: 'Select project type'
            }) as 'skill' | 'service' | 'model' | undefined;
            if (!type) return;

            const result = await cli.init(name, type);
            if (result.success) {
                vscode.window.showInformationMessage(`Project "${name}" created successfully.`);
                vscode.commands.executeCommand('setContext', 'qoocode.isQoocodeProject', true);
            } else {
                vscode.window.showErrorMessage(`Failed to create project: ${result.stderr}`);
            }
        }),

        // ── Build ──────────────────────────────────────────
        vscode.commands.registerCommand('qoocode.build', async () => {
            const result = await cli.build();
            if (result.success) {
                vscode.window.showInformationMessage('Build succeeded.');
            } else {
                vscode.window.showErrorMessage(`Build failed. See output for details.`);
            }
        }),

        // ── Run ────────────────────────────────────────────
        vscode.commands.registerCommand('qoocode.run', async () => {
            vscode.window.showInformationMessage('Running project...');
            await cli.run();
        }),

        // ── Test ───────────────────────────────────────────
        vscode.commands.registerCommand('qoocode.test', async () => {
            const result = await cli.test();
            if (result.success) {
                vscode.window.showInformationMessage('All tests passed.');
            } else {
                vscode.window.showErrorMessage('Some tests failed.');
            }
        }),

        // ── Doctor ─────────────────────────────────────────
        vscode.commands.registerCommand('qoocode.doctor', async () => {
            const result = await cli.doctor();
            if (result.success) {
                vscode.window.showInformationMessage('Environment is healthy.');
            } else {
                vscode.window.showWarningMessage('Environment issues found. Check output for details.');
            }
        }),

        // ── Create Skill ───────────────────────────────────
        vscode.commands.registerCommand('qoocode.createSkill', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Skill name',
                placeHolder: 'my_skill'
            });
            if (!name) return;
            await cli.init(name, 'skill');
            vscode.window.showInformationMessage(`Skill "${name}" created.`);
        }),

        // ── Create Service ─────────────────────────────────
        vscode.commands.registerCommand('qoocode.createService', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Service name',
                placeHolder: 'my_service'
            });
            if (!name) return;
            await cli.init(name, 'service');
            vscode.window.showInformationMessage(`Service "${name}" created.`);
        }),

        // ── Create Model ───────────────────────────────────
        vscode.commands.registerCommand('qoocode.createModel', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Model name',
                placeHolder: 'my_model'
            });
            if (!name) return;
            await cli.init(name, 'model');
            vscode.window.showInformationMessage(`Model "${name}" created.`);
        }),

        // ── Open Behavior Tree Editor ──────────────────────
        vscode.commands.registerCommand('qoocode.openBehaviorTree', async () => {
            // If there's an active .btree file, open custom editor; otherwise prompt to create
            const editor = vscode.window.activeTextEditor;
            if (editor && (editor.document.fileName.endsWith('.btree') || editor.document.fileName.endsWith('.bt.json'))) {
                await vscode.commands.executeCommand(
                    'vscode.openWith',
                    editor.document.uri,
                    'qoocode.behaviorTree'
                );
            } else {
                // Create a new behavior tree file
                const uri = await vscode.window.showSaveDialog({
                    filters: { 'Behavior Tree': ['btree', 'bt.json'] },
                    defaultUri: vscode.Uri.file('behavior.btree')
                });
                if (uri) {
                    const defaultTree = JSON.stringify({
                        name: 'NewBehaviorTree',
                        version: '1.0',
                        root: {
                            type: 'Sequence',
                            name: 'Root',
                            children: []
                        }
                    }, null, 2);
                    await vscode.workspace.fs.writeFile(uri, Buffer.from(defaultTree, 'utf-8'));
                    const doc = await vscode.workspace.openTextDocument(uri);
                    await vscode.window.showTextDocument(doc);
                    await vscode.commands.executeCommand('vscode.openWith', uri, 'qoocode.behaviorTree');
                }
            }
        }),

        // ── LSP Restart ────────────────────────────────────
        vscode.commands.registerCommand('qoocode.restartLsp', async () => {
            await lspClient.restart();
            vscode.window.showInformationMessage('qoocode LSP restarted.');
        }),

        // ── Refresh Behavior Trees ─────────────────────────
        vscode.commands.registerCommand('qoocode.refreshBehaviorTrees', () => {
            btProvider.refresh();
        })
    ];

    context.subscriptions.push(...disposables);
}
