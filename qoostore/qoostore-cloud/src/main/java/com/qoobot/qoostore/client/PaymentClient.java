package com.qoobot.qoostore.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.Map;
import java.util.TreeMap;

/**
 * 支付网关客户端
 * 集成 Stripe / 支付宝 / 微信支付
 */
@Slf4j
@Component
public class PaymentClient {

    private final RestTemplate restTemplate;

    @Value("${payment.stripe.api-key:}")
    private String stripeApiKey;

    @Value("${payment.stripe.webhook-secret:}")
    private String stripeWebhookSecret;

    @Value("${payment.alipay.app-id:}")
    private String alipayAppId;

    @Value("${payment.alipay.private-key:}")
    private String alipayPrivateKey;

    @Value("${payment.wechat.app-id:}")
    private String wechatAppId;

    @Value("${payment.wechat.mch-id:}")
    private String wechatMchId;

    @Value("${payment.wechat.api-key:}")
    private String wechatApiKey;

    public PaymentClient() {
        this.restTemplate = new RestTemplate();
    }

    /**
     * 创建支付单（根据支付方式路由到不同的支付网关）
     */
    public Map<String, Object> createPayment(String orderNo, double amount, String currency,
                                               String paymentMethod, String description) {
        return switch (paymentMethod) {
            case "stripe" -> createStripePayment(orderNo, amount, currency, description);
            case "alipay" -> createAlipayPayment(orderNo, amount, currency, description);
            case "wechat" -> createWechatPayment(orderNo, amount, currency, description);
            default -> throw new RuntimeException("Unsupported payment method: " + paymentMethod);
        };
    }

    /**
     * Stripe 支付
     */
    private Map<String, Object> createStripePayment(String orderNo, double amount, String currency, String description) {
        log.info("Creating Stripe payment: orderNo={}, amount={}, currency={}", orderNo, amount, currency);

        long amountCents = Math.round(amount * 100);
        Map<String, Object> payload = Map.of(
                "amount", amountCents,
                "currency", currency.toLowerCase(),
                "description", description,
                "metadata", Map.of("order_no", orderNo)
        );

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setBasicAuth(stripeApiKey, "");
            headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

            // In production: POST https://api.stripe.com/v1/payment_intents
            log.info("Stripe payment intent created for order: {}", orderNo);
            return Map.of(
                    "paymentId", "pi_" + System.currentTimeMillis(),
                    "status", "created",
                    "clientSecret", "pi_secret_" + System.currentTimeMillis()
            );
        } catch (Exception e) {
            log.error("Stripe payment failed: orderNo={}, error={}", orderNo, e.getMessage());
            throw new RuntimeException("Stripe payment creation failed", e);
        }
    }

    /**
     * 支付宝支付
     */
    private Map<String, Object> createAlipayPayment(String orderNo, double amount, String currency, String description) {
        log.info("Creating Alipay payment: orderNo={}, amount={}, currency={}", orderNo, currency);

        TreeMap<String, String> params = new TreeMap<>();
        params.put("app_id", alipayAppId);
        params.put("method", "alipay.trade.app.pay");
        params.put("charset", "utf-8");
        params.put("timestamp", java.time.Instant.now().toString());
        params.put("out_trade_no", orderNo);
        params.put("total_amount", String.format("%.2f", amount));
        params.put("subject", description);

        try {
            String sign = signAlipay(buildSignString(params));
            params.put("sign", sign);

            log.info("Alipay order created: orderNo={}", orderNo);
            return Map.of(
                    "paymentId", "alipay_" + System.currentTimeMillis(),
                    "status", "created",
                    "orderString", String.join("&", params.entrySet().stream()
                            .map(e -> e.getKey() + "=" + e.getValue()).toList())
            );
        } catch (Exception e) {
            log.error("Alipay payment failed: orderNo={}, error={}", orderNo, e.getMessage());
            throw new RuntimeException("Alipay payment creation failed", e);
        }
    }

    /**
     * 微信支付
     */
    private Map<String, Object> createWechatPayment(String orderNo, double amount, String currency, String description) {
        log.info("Creating Wechat payment: orderNo={}, amount={}, currency={}", orderNo, currency);

        int amountFen = (int) Math.round(amount * 100);
        Map<String, Object> payload = Map.of(
                "appid", wechatAppId,
                "mchid", wechatMchId,
                "out_trade_no", orderNo,
                "amount", Map.of("total", amountFen, "currency", currency),
                "description", description
        );

        log.info("Wechat payment order created: orderNo={}", orderNo);
        return Map.of(
                "paymentId", "wx_" + System.currentTimeMillis(),
                "status", "created",
                "prepayId", "prepay_" + System.currentTimeMillis()
        );
    }

    /**
     * 验证支付回调签名
     */
    public boolean verifyCallbackSignature(String payload, String signature, String paymentMethod) {
        return switch (paymentMethod) {
            case "stripe" -> verifyStripeSignature(payload, signature);
            case "alipay" -> verifyAlipaySignature(payload, signature);
            case "wechat" -> verifyWechatSignature(payload, signature);
            default -> false;
        };
    }

    private boolean verifyStripeSignature(String payload, String signature) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec keySpec = new SecretKeySpec(stripeWebhookSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(keySpec);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String expected = Base64.getEncoder().encodeToString(hash);
            return expected.equals(signature);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            log.error("Stripe signature verification failed", e);
            return false;
        }
    }

    private boolean verifyAlipaySignature(String payload, String signature) {
        // In production: use Alipay SDK to verify RSA signature
        log.info("Alipay signature verification: payload length={}", payload.length());
        return true; // Simplified for dev
    }

    private boolean verifyWechatSignature(String payload, String signature) {
        // In production: use Wechat Pay SDK to verify signature
        log.info("Wechat signature verification: payload length={}", payload.length());
        return true; // Simplified for dev
    }

    private String signAlipay(String content) throws NoSuchAlgorithmException, InvalidKeyException {
        Mac mac = Mac.getInstance("HmacSHA256");
        SecretKeySpec keySpec = new SecretKeySpec(alipayPrivateKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        mac.init(keySpec);
        return Base64.getEncoder().encodeToString(mac.doFinal(content.getBytes(StandardCharsets.UTF_8)));
    }

    private String buildSignString(TreeMap<String, String> params) {
        StringBuilder sb = new StringBuilder();
        params.forEach((k, v) -> {
            if (v != null && !v.isEmpty()) {
                if (!sb.isEmpty()) sb.append("&");
                sb.append(k).append("=").append(v);
            }
        });
        return sb.toString();
    }
}
