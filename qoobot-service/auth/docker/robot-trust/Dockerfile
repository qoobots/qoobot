FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml .
COPY qooauth-common/pom.xml qooauth-common/
COPY qooauth-robot-trust/pom.xml qooauth-robot-trust/
RUN mvn dependency:go-offline -pl qooauth-robot-trust -am -B
COPY qooauth-common/src qooauth-common/src
COPY qooauth-robot-trust/src qooauth-robot-trust/src
RUN mvn package -DskipTests -pl qooauth-robot-trust -am

FROM eclipse-temurin:17-jre-alpine
RUN addgroup -S qooauth && adduser -S qooauth -G qooauth
USER qooauth
COPY --from=builder /build/qooauth-robot-trust/target/*.jar app.jar
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-XX:+UseZGC", "-Xmx512m", "-jar", "app.jar"]
