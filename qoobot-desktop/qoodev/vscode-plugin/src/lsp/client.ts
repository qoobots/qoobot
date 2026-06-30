import * as vscode from 'vscode';
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from 'vscode-languageclient/node';
import { execSync } from 'child_process';

export class QooLspClient implements vscode.Disposable {
    private client: LanguageClient | null = null;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    start(): void {
        const config = vscode.workspace.getConfiguration('qoodev');
        if (!config.get<boolean>('lsp.enabled', true)) {
            console.log('qoodev LSP: disabled by configuration');
            return;
        }

        const pythonPath = config.get<string>('lsp.pythonPath', 'python');
        const serverModule = this.context.asAbsolutePath('../qoodev-lsp/lsp_server/__init__.py');

        const serverOptions: ServerOptions = {
            command: pythonPath,
            args: ['-m', 'qoodev_lsp'],
            transport: TransportKind.stdio,
            options: {
                env: { ...process.env, PYTHONPATH: this.context.asAbsolutePath('../qoodev-lsp') }
            }
        };

        const clientOptions: LanguageClientOptions = {
            documentSelector: [
                { scheme: 'file', language: 'python' },
                { scheme: 'file', language: 'cpp' },
                { scheme: 'file', language: 'behavior-tree' }
            ],
            synchronize: {
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*.py')
            },
            outputChannel: vscode.window.createOutputChannel('qoodev LSP'),
            initializationOptions: {
                qooProject: true,
                sdkVersion: '0.1.0'
            }
        };

        this.client = new LanguageClient(
            'qoodev-lsp',
            'qoodev Language Server',
            serverOptions,
            clientOptions
        );

        this.client.start().then(() => {
            console.log('qoodev LSP: started');
        }).catch(err => {
            vscode.window.showWarningMessage(`qoodev LSP failed to start: ${err.message}`);
        });
    }

    stop(): void {
        if (this.client) {
            this.client.stop();
            this.client = null;
        }
    }

    async restart(): Promise<void> {
        this.stop();
        this.start();
    }

    getClient(): LanguageClient | null {
        return this.client;
    }

    dispose(): void {
        this.stop();
    }
}
