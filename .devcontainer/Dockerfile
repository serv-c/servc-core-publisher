FROM bitnami/spark:3.5 AS spark-image

FROM mcr.microsoft.com/vscode/devcontainers/python

COPY --from=spark-image /opt/bitnami /opt/bitnami
RUN sudo rm -rf /opt/bitnami/python

ENV BITNAMI_ROOT_DIR=/opt/bitnami
ENV SPARK_HOME=$BITNAMI_ROOT_DIR/spark
ENV PATH="$PATH:$BITNAMI_ROOT_DIR/java/bin:$BITNAMI_ROOT_DIR/spark/bin:$BITNAMI_ROOT_DIR/spark/sbin"
