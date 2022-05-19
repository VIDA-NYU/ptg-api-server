# Base image that has nginx-rtmp
FROM tiangolo/nginx-rtmp:latest

# Additional config to enable HLS
COPY nginx.conf /etc/nginx/nginx.conf

# Port for RTMP
EXPOSE 1935/tcp
# Port for HLS
EXPOSE 80/tcp



# FROM tiangolo/nginx-rtmp:latest

# # RUN curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg && \
# #     echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" > /etc/apt/sources.list.d/redis.list && \
# #     apt-get update && \
# #     apt-get install redis && \
# #     rm -rf /var/lib/apt/lists/*

# # RUN cd /tmp &&\
# #     curl http://download.redis.io/redis-stable.tar.gz | tar xz &&\
# #     make -C redis-stable &&\
# #     cp redis-stable/src/redis-cli /usr/local/bin &&\
# #     rm -rf /tmp/redis-stable

# RUN mkdir -p /usr/src/stat.xsl && curl -o /usr/src/stat.xsl/stat.xsl https://raw.githubusercontent.com/arut/nginx-rtmp-module/master/stat.xsl

# RUN mkdir -p /home/hls/live && chmod 777 /home/hls
# RUN mkdir -p /home/recordings

# COPY nginx.conf /etc/nginx/nginx.conf
# COPY index.html /usr/local/nginx/html/index.html
