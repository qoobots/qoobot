FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

COPY qooauth-auth/target/qooauth-auth-*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
