# Supply a trusted Hermes image with its dependencies already installed.
# Never build from a live container containing keys, profiles or VM state.
ARG HERMES_BASE_IMAGE
FROM ${HERMES_BASE_IMAGE}
USER root
# Gitea checkout requires node and git; the supplied image must provide both.
RUN command -v node && command -v git && command -v bash
ENTRYPOINT []
CMD ["sleep", "infinity"]
