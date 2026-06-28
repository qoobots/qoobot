package com.qoobot.qooauth.auth.config;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.Curve;
import com.nimbusds.jose.jwk.ECKey;
import com.nimbusds.jose.jwk.OctetKeyPair;
import com.nimbusds.jose.jwk.gen.ECKeyGenerator;
import com.nimbusds.jose.jwk.gen.OctetKeyPairGenerator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.security.interfaces.ECPublicKey;

/**
 * JWT signing key configuration.
 * Supports Ed25519 (primary) and RS256 (fallback for legacy clients).
 */
@Configuration
public class JwtConfig {

    @Bean
    public OctetKeyPair ed25519Key() throws JOSEException {
        return new OctetKeyPairGenerator(Curve.Ed25519)
                .keyID("qooauth-ed25519-2026")
                .generate();
    }

    @Bean
    public ECKey rs256Key() throws JOSEException {
        return new ECKeyGenerator(Curve.P_256)
                .keyID("qooauth-rs256-2026")
                .algorithm(JWSAlgorithm.RS256)
                .generate();
    }

    @Bean
    public ECKey ecdsaP256Key() throws JOSEException {
        return new ECKeyGenerator(Curve.P_256)
                .keyID("qooauth-ecdsa-p256-device-ca")
                .generate();
    }
}
