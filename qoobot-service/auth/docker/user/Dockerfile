FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

COPY qooauth-user/target/qooauth-user-*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
