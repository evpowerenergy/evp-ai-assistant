FROM nousresearch/hermes-agent:v2026.7.7.2@sha256:9c841866021c54c4596849f6135717e8a4d52ba510b7f52c50aef1de1a283973

USER root
COPY patches/evp-trusted-context.patch /tmp/evp-trusted-context.patch
COPY evp_execution_context.py /opt/hermes/evp_execution_context.py
COPY bootstrap.py /opt/hermes/evp_bootstrap.py
RUN cd /opt/hermes && git apply --check /tmp/evp-trusted-context.patch && \
    git apply /tmp/evp-trusted-context.patch && \
    rm /tmp/evp-trusted-context.patch

ENV API_SERVER_ENABLED=true \
    API_SERVER_HOST=0.0.0.0 \
    API_SERVER_PORT=8080 \
    EVP_MCP_SERVER_NAME=evp

EXPOSE 8080
CMD ["python", "/opt/hermes/evp_bootstrap.py"]
