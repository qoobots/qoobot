// Package router 导入所需的业务模型
package router

import (
	"github.com/qoobot/qooauth/internal/model"
	"github.com/qoobot/qooauth/internal/service/apikey"
	"github.com/qoobot/qooauth/internal/service/auth"
	"github.com/qoobot/qooauth/internal/service/device"
	"github.com/qoobot/qooauth/internal/service/oauth"
)

// 确保导入了 handlers.go 中使用的所有类型
var _ = (*model.Device)(nil)
var _ = (*model.APIKey)(nil)
var _ = (auth.LoginRequest{})
var _ = (device.ActivateDeviceRequest{})
var _ = (apikey.CreateAPIKeyRequest{})
var _ = (oauth.ExchangeTokenRequest{})
