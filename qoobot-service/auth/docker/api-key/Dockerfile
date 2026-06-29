FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml .
COPY qooauth-common/pom.xml qooauth-common/
COPY qooauth-api-key/pom.xml qooauth-api-key/
RUN mvn dependency:go-offline -pl qooauth-api-key -am -B
COPY qooauth-common/src qooauth-common/src
COPY qooauth-api-key/src qooauth-api-key/src
RUN mvn package -DskipTests -pl qooauth-api-key -am

FROM eclipse-temurin:17-jre-alpine
RUN addgroup -S qooauth && adduser -S qooauth -G qooauth
USER qooauth
COPY --from=builder /build/qooauth-api-key/target/*.jar app.jar
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-XX:+UseZGC", "-Xmx512m", "-jar", "app.jar"]
