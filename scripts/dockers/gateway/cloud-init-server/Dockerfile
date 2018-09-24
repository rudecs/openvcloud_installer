from golang as builder
RUN go get github.com/zero-os/cloud-init-server
RUN cd $GOPATH/src/github.com/zero-os/cloud-init-server && CGO_ENABLED=0 GOOS=linux go build -a -ldflags '-extldflags "-static" -s -w' -o /go/bin/cloud-init-server
FROM scratch
COPY --from=builder /go/bin/cloud-init-server /bin/cloud-init-server
COPY config.json /etc/config.json
