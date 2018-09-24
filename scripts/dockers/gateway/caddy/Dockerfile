FROM golang:alpine as builder
RUN apk -U add git ca-certificates
RUN go get github.com/mholt/caddy
RUN cd $GOPATH/src/github.com/mholt/caddy/caddy && CGO_ENABLED=0 GOOS=linux go build -a -ldflags '-extldflags "-static" -s -w' -o /go/bin/caddy
FROM scratch
COPY --from=builder /go/bin/caddy /bin/caddy
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY config.json /etc/config.json
