# Multi-stage build for qooauth
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /auth-server ./cmd/auth-server

FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata
ENV TZ=UTC

COPY --from=builder /auth-server /usr/local/bin/auth-server

RUN addgroup -S qooauth && adduser -S qooauth -G qooauth
USER qooauth

EXPOSE 8080 9090

ENTRYPOINT ["auth-server"]
