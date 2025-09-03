FROM alpine:latest

# Install build dependencies
RUN apk add --no-cache \
    abuild \
    alpine-sdk \
    autoconf \
    automake \
    libtool \
    linux-headers \
    pkgconfig \
    sudo \
    curl-dev \
    libevent-dev \
    libxml2-dev \
    net-snmp-dev \
    openssl-dev \
    pcre2-dev \
    sqlite-dev \
    unixodbc-dev \
    zlib-dev \
    openldap-dev \
    libssh2-dev \
    && adduser -D -G abuild builder \
    && echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Setup build environment
USER builder
WORKDIR /home/builder

# Generate signing keys
RUN abuild-keygen -a -i -n

# Copy package files
COPY --chown=builder:builder . /home/builder/zabbix/

WORKDIR /home/builder/zabbix

# Set build command
CMD ["abuild", "-r"]
