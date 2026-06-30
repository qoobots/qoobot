import * as vscode from 'vscode';
import { exec, spawn, ExecException } from 'child_process';

export interface QooCommandResult {
    success: boolean;
    stdout: string;
    stderr: string;
    exitCode: number | null;
}

export class QooCLI implements vscode.Disposable {
    private context: vscode.ExtensionContext;
    private outputChannel: vscode.OutputChannel;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.outputChannel = vscode.window.createOutputChannel('qoodev CLI');
    }

    private getQooPath(): string {
        return vscode.workspace.getConfiguration('qoodev').get<string>('qoo.path', 'qoo');
    }

    private async runCommand(args: string[], cwd?: string): Promise<QooCommandResult> {
        return new Promise((resolve) => {
            const qooPath = this.getQooPath();
            const workDir = cwd || this.getWorkspaceRoot();
            const fullCmd = `${qooPath} ${args.join(' ')}`;

            this.outputChannel.appendLine(`\n> ${fullCmd}`);
            this.outputChannel.show(true);

            exec(fullCmd, { cwd: workDir }, (error: ExecException | null, stdout: string, stderr: string) => {
                this.outputChannel.appendLine(stdout);
                if (stderr) this.outputChannel.appendLine(`[stderr] ${stderr}`);

                resolve({
                    success: !error,
                    stdout,
                    stderr,
                    exitCode: error ? error.code ?? null : 0
                });
            });
        });
    }

    private getWorkspaceRoot(): string | undefined {
        const folders = vscode.workspace.workspaceFolders;
        return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined;
    }

    async init(projectName: string, projectType: 'skill' | 'service' | 'model' = 'skill'): Promise<QooCommandResult> {
        return this.runCommand(['init', projectName, '--type', projectType]);
    }

    async build(): Promise<QooCommandResult> {
        return this.runCommand(['build']);
    }

    async run(): Promise<QooCommandResult> {
        return this.runCommand(['run']);
    }

    async test(): Promise<QooCommandResult> {
        return this.runCommand(['test']);
    }

    async doctor(): Promise<QooCommandResult> {
        return this.runCommand(['doctor']);
    }

    dispose(): void {
        this.outputChannel.dispose();
    }
}
