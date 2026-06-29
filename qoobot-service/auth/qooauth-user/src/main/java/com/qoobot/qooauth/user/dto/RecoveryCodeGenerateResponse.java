package com.qoobot.qooauth.user.dto;

import java.util.List;

public class RecoveryCodeGenerateResponse {
    private List<String> recoveryCodes;  // plaintext codes (shown once)
    private int count;

    public RecoveryCodeGenerateResponse(List<String> recoveryCodes) {
        this.recoveryCodes = recoveryCodes;
        this.count = recoveryCodes.size();
    }

    public List<String> getRecoveryCodes() { return recoveryCodes; }
    public void setRecoveryCodes(List<String> recoveryCodes) { this.recoveryCodes = recoveryCodes; }
    public int getCount() { return count; }
    public void setCount(int count) { this.count = count; }
}
