package com.qoobot.qoostore.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI qoostoreOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("QooStore API")
                        .description("QooBot 技能市场 API — 技能发现/分发/商业化")
                        .version("v0.1.0")
                        .license(new License()
                                .name("Apache 2.0")
                                .url("https://www.apache.org/licenses/LICENSE-2.0")));
    }
}
