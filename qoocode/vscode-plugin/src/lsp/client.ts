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
        const config = vscode.workspace.getConfiguration('qoocode');
        if (!config.get<boolean>('lsp.enabled', true)) {
            console.log('qoocode LSP: disabled by configuration');
            return;
        }

        const pythonPath = config.get<string>('lsp.pythonPath', 'python');
        const serverModule = this.context.asAbsolutePath('../qoocode-lsp/lsp_server/__init__.py');

        const serverOptions: ServerOptions = {
            command: pythonPath,
            args: ['-m', 'qoocode_lsp'],
            transport: TransportKind.stdio,
            options: {
                env: { ...process.env, PYTHONPATH: this.context.asAbsolutePath('../qoocode-lsp') }
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
            outputChannel: vscode.window.createOutputChannel('qoocode LSP'),
            initializationOptions: {
                qooProject: true,
                sdkVersion: '0.1.0'
            }
        };

        this.client = new LanguageClient(
            'qoocode-lsp',
            'qoocode Language Server',
            serverOptions,
            clientOptions
        );

        this.client.start().then(() => {
            console.log('qoocode LSP: started');
        }).catch(err => {
            vscode.window.showWarningMessage(`qoocode LSP failed to start: ${err.message}`);
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
