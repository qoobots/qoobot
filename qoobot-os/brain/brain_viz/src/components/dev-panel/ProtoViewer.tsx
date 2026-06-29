/**
 * src/components/dev-panel/ProtoViewer.tsx — Protobuf message viewer
 */
'use client';

import React, { useState } from 'react';
import { CodeEditor } from './CodeEditor';

const SAMPLE_PROTO = `// brain_proto/proto/cognition/service.proto
service CognitionService {
  rpc ParseIntent(ParseIntentRequest) returns (ParseIntentResponse);
  rpc DecomposeTask(DecomposeTaskRequest) returns (DecomposeTaskResponse);
  rpc GenerateBT(GenerateBTRequest) returns (GenerateBTResponse);
  rpc Clarify(ClarifyRequest) returns (ClarifyResponse);
}

message ParseIntentRequest {
  string instruction = 1;
  string context = 2;
}

message ParseIntentResponse {
  Intent intent = 1;
  repeated Intent alternatives = 2;
}

message Intent {
  string action = 1;
  string target = 2;
  string source = 3;
  repeated string constraints = 4;
  float confidence = 5;
  string raw_text = 6;
}`;

export function ProtoViewer() {
  const [protoText, setProtoText] = useState(SAMPLE_PROTO);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs text-brain-muted uppercase tracking-wide">Proto 定义</h3>
        <select className="bg-brain-surface border border-brain-border rounded px-2 py-0.5 text-[10px] text-brain-text">
          <option>cognition/service.proto</option>
          <option>decision/service.proto</option>
          <option>perception/service.proto</option>
          <option>control/service.proto</option>
          <option>safety/service.proto</option>
          <option>knowledge/service.proto</option>
        </select>
      </div>
      <CodeEditor
        value={protoText}
        onChange={setProtoText}
        language="text"
        readOnly
        height="300px"
      />
    </div>
  );
}
