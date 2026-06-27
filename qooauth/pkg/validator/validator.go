// Package validator 输入验证工具
package validator

import (
	"fmt"
	"net/mail"
	"regexp"
	"unicode"
)

// ValidateEmail 验证邮箱格式
func ValidateEmail(email string) error {
	if email == "" {
		return fmt.Errorf("email is required")
	}
	_, err := mail.ParseAddress(email)
	if err != nil {
		return fmt.Errorf("invalid email format: %s", email)
	}
	return nil
}

// PasswordPolicy 密码策略
type PasswordPolicy struct {
	MinLength    int
	RequireUpper bool
	RequireLower bool
	RequireDigit bool
	RequireSpecial bool
}

// DefaultPasswordPolicy 默认密码策略
var DefaultPasswordPolicy = PasswordPolicy{
	MinLength:       8,
	RequireUpper:    true,
	RequireLower:    true,
	RequireDigit:    true,
	RequireSpecial:  true,
}

// ValidatePassword 验证密码强度
func ValidatePassword(password string, policy PasswordPolicy) error {
	if len(password) < policy.MinLength {
		return fmt.Errorf("password must be at least %d characters", policy.MinLength)
	}

	var (
		hasUpper   bool
		hasLower   bool
		hasDigit   bool
		hasSpecial bool
	)

	for _, c := range password {
		switch {
		case unicode.IsUpper(c):
			hasUpper = true
		case unicode.IsLower(c):
			hasLower = true
		case unicode.IsDigit(c):
			hasDigit = true
		case unicode.IsPunct(c) || unicode.IsSymbol(c):
			hasSpecial = true
		}
	}

	if policy.RequireUpper && !hasUpper {
		return fmt.Errorf("password must contain at least one uppercase letter")
	}
	if policy.RequireLower && !hasLower {
		return fmt.Errorf("password must contain at least one lowercase letter")
	}
	if policy.RequireDigit && !hasDigit {
		return fmt.Errorf("password must contain at least one digit")
	}
	if policy.RequireSpecial && !hasSpecial {
		return fmt.Errorf("password must contain at least one special character")
	}

	return nil
}

// phoneRegex 手机号正则（国际格式）
var phoneRegex = regexp.MustCompile(`^\+[1-9]\d{1,14}$`)

// ValidatePhone 验证手机号格式（E.164）
func ValidatePhone(phone string) error {
	if phone == "" {
		return fmt.Errorf("phone is required")
	}
	if !phoneRegex.MatchString(phone) {
		return fmt.Errorf("invalid phone format, must be E.164 (e.g. +8613800138000)")
	}
	return nil
}
